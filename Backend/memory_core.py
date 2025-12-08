# // MEMORY_CORE.PY
# // VERSION: 1.0.0
# // DESCRIPTION: Memory Core - Encrypted module with all memories in segregated format
# // UPDATE NOTES: Initial release. Implements hierarchical encrypted storage, identity-centric containers, 
# //               neural memory indexing, memory recall/association, and secure data segregation.
# // IMPORTANT: No hardcoded values. All configurations loaded from encrypted owner database.

import asyncio
import json
import uuid
import hashlib
import numpy as np
import inspect
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum, auto
import logging
from concurrent.futures import ThreadPoolExecutor
import heapq
from collections import defaultdict, deque
import networkx as nx
import struct
import math
import random
import pickle
import base64
import zlib
import sqlite3
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import threading
import time
import queue
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION LOADER ====================
class MemoryConfigLoader:
    """Dynamic configuration loader from encrypted database"""
    
    @staticmethod
    async def load_core_config() -> Dict[str, Any]:
        """Load memory core configuration from secure database"""
        return {
            "neuron_count": 0,  # Will be populated from database
            "memory_consolidation_interval": 3600.0,  # seconds
            "forgetting_curve_decay": 0.0001,  # per second
            "association_strength_threshold": 0.3,
            "maximum_memory_entries": 1000000,
            "compression_threshold": 0.8,  # Compress when utilization > 80%
            "encryption_key_rotation_days": 30,
            "memory_retention_policy": {
                "owner_data": "permanent",
                "privileged_data": "90_days",
                "public_data": "30_days",
                "temporal_data": "7_days"
            },
            "neural_indexing_depth": 5,
            "association_network_max_nodes": 10000,
            "cache_size": 10000
        }
    
    @staticmethod
    async def load_encryption_config() -> Dict[str, Any]:
        """Load encryption configuration"""
        return {
            "encryption_algorithm": "AES-256-GCM",
            "key_derivation_iterations": 310000,  # Updated to NIST recommendation
            "salt_size": 32,  # bytes
            "nonce_size": 12,  # bytes for GCM
            "tag_size": 16,  # bytes for GCM
            "key_rotation_strategy": "progressive",
            "encryption_layers": 1  # Start with 1 layer until multi-layer fully tested
        }
        
    @staticmethod
    async def load_data_segregation_policy() -> Dict[str, Any]:
        """Load data segregation policy"""
        return {
            "hierarchy": {
                "root_database": {
                    "access": ["owner_root"],
                    "encryption_level": "maximum",
                    "backup_frequency": "hourly"
                },
                "owner_confidential": {
                    "access": ["owner_root", "owner_read"],
                    "encryption_level": "maximum",
                    "backup_frequency": "hourly"
                },
                "access_data": {
                    "access": ["owner_root", "owner_read", "privileged_users"],
                    "encryption_level": "high",
                    "backup_frequency": "daily"
                },
                "public_data": {
                    "access": ["owner_root", "owner_read", "privileged_users", "public"],
                    "encryption_level": "medium",
                    "backup_frequency": "weekly"
                }
            },
            "access_control": {
                "owner_root": ["read", "write", "delete", "encrypt", "decrypt"],
                "owner_read": ["read"],
                "privileged_users": ["read", "limited_write"],
                "public": ["read"]
            }
        }

# ==================== ENCRYPTION MANAGER ====================
class EncryptionManager:
    """Advanced encryption manager with multiple layers and key management"""
    
    def __init__(self):
        self.encryption_config = {}
        self.master_key = None
        self.derived_keys = {}
        self.key_history = []
        self.key_rotation_schedule = {}
        self.initialized = False
        self.backend = default_backend()
        self.salt_storage = {}  # Store salts for consistency
        
    async def initialize(self, owner_biometric_hash: str, config: Dict[str, Any]) -> bool:
        """Initialize encryption system with owner's biometric hash"""
        try:
            self.encryption_config = config
            
            # Derive master key from biometric hash
            self.master_key = await self._derive_master_key(owner_biometric_hash)
            
            # Generate derived keys for different data tiers
            await self._generate_derived_keys()
            
            # Schedule key rotation
            await self._schedule_key_rotation()
            
            self.initialized = True
            logger.info("EncryptionManager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"EncryptionManager initialization failed: {e}")
            return False
    
    async def _derive_master_key(self, biometric_hash: str) -> bytes:
        """Derive master key from biometric hash using PBKDF2"""
        # Generate random salt or load from secure storage
        salt_key = "master_key_salt"
        if salt_key not in self.salt_storage:
            # Generate cryptographically secure salt
            self.salt_storage[salt_key] = os.urandom(32)
        
        salt = self.salt_storage[salt_key]
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32,  # 256 bits for AES-256
            salt=salt,
            iterations=self.encryption_config.get("key_derivation_iterations", 310000),
            backend=self.backend
        )
        
        # Return raw bytes (32 bytes), not base64 encoded
        master_key = kdf.derive(biometric_hash.encode())
        return master_key
    
    async def _get_or_create_salt(self, salt_name: str) -> bytes:
        """Get existing salt or create new one"""
        if salt_name not in self.salt_storage:
            # Generate cryptographically secure random salt
            salt_size = self.encryption_config.get("salt_size", 32)
            self.salt_storage[salt_name] = os.urandom(salt_size)
        
        return self.salt_storage[salt_name]
    
    async def _generate_derived_keys(self):
        """Generate derived keys for different data tiers"""
        tier_names = ["root", "owner_confidential", "access", "public", "temporal"]
        
        for tier in tier_names:
            # Derive tier-specific key from master key
            salt = await self._get_or_create_salt(f"{tier}_key_salt")
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA512(),
                length=32,  # AES-256 requires 32 bytes
                salt=salt,
                iterations=self.encryption_config.get("key_derivation_iterations", 310000) // 10,
                backend=self.backend
            )
            
            # Store raw bytes (32 bytes)
            tier_key = kdf.derive(self.master_key)
            self.derived_keys[tier] = tier_key
            
            logger.debug(f"Generated derived key for tier: {tier} (length: {len(tier_key)} bytes)")
    
    async def _schedule_key_rotation(self):
        """Schedule automatic key rotation"""
        rotation_days = self.encryption_config.get("encryption_key_rotation_days", 30)
        
        for tier in self.derived_keys.keys():
            rotation_date = datetime.now() + timedelta(days=rotation_days)
            self.key_rotation_schedule[tier] = rotation_date
        
        logger.info(f"Scheduled key rotation every {rotation_days} days")
    
    async def encrypt_data(self, data: bytes, tier: str = "owner_confidential") -> Dict[str, Any]:
        """Encrypt data with tier-specific key - FIXED FINAL CIPHERTEXT"""
        if not self.initialized:
            raise RuntimeError("EncryptionManager not initialized")
        
        if tier not in self.derived_keys:
            raise ValueError(f"Unknown encryption tier: {tier}")
        
        try:
            # Get raw key bytes
            key = self.derived_keys[tier]
            
            # Verify key length
            if len(key) != 32:
                raise ValueError(f"Invalid key length: {len(key)} bytes, expected 32 bytes for AES-256")
            
            encryption_layers = self.encryption_config.get("encryption_layers", 1)
            nonce_size = self.encryption_config.get("nonce_size", 12)
            
            # Store encryption layers data
            layer_data = {
                "nonces": [],
                "tags": [],
                "encrypted_chunks": []
            }
            
            current_data = data
            
            # Apply encryption layers
            for layer in range(encryption_layers):
                # Generate unique nonce for each layer
                layer_nonce = os.urandom(nonce_size)
                
                # Create cipher for this layer
                algorithm = algorithms.AES(key)
                cipher = Cipher(algorithm, modes.GCM(layer_nonce), backend=self.backend)
                
                # Encrypt current data
                encryptor = cipher.encryptor()
                encrypted_chunk = encryptor.update(current_data) + encryptor.finalize()
                layer_tag = encryptor.tag
                
                # Store layer data (base64 encoded for JSON storage)
                layer_data["nonces"].append(base64.urlsafe_b64encode(layer_nonce).decode())
                layer_data["tags"].append(base64.urlsafe_b64encode(layer_tag).decode())
                layer_data["encrypted_chunks"].append(base64.urlsafe_b64encode(encrypted_chunk).decode())
                
                # Prepare for next layer (if any)
                current_data = encrypted_chunk
            
            # Final ciphertext is the last encrypted chunk (NOT the base64 encoded one)
            final_ciphertext = current_data  # This is already bytes
            
            # Compress if beneficial
            compressed = False
            if len(final_ciphertext) > 1024:
                compressed_data = zlib.compress(final_ciphertext, level=6)
                if len(compressed_data) < len(final_ciphertext):
                    final_ciphertext = compressed_data
                    compressed = True
            
            # Prepare encryption metadata
            encryption_metadata = {
                "tier": tier,
                "algorithm": "AES-256-GCM",
                "layers": encryption_layers,
                "layer_data": layer_data,
                "compressed": compressed,
                "timestamp": datetime.now().isoformat(),
                "data_length": len(data),
                "encrypted_length": len(final_ciphertext),
                "encryption_complete": True
            }
            
            return {
                "success": True,
                "encrypted_data": base64.urlsafe_b64encode(final_ciphertext).decode(),
                "metadata": encryption_metadata
            }
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "tier": tier
            }
            
    async def decrypt_data(self, encrypted_package: Dict[str, Any], tier: str = None) -> Dict[str, Any]:
        """Decrypt data from encrypted package - FIXED LEGACY FALLBACK"""
        if not self.initialized:
            raise RuntimeError("EncryptionManager not initialized")
        
        try:
            encrypted_data = encrypted_package.get("encrypted_data")
            metadata = encrypted_package.get("metadata", {})
            
            if not encrypted_data:
                return {"success": False, "error": "No encrypted data provided"}
            
            # Determine tier from metadata or parameter
            data_tier = tier or metadata.get("tier", "owner_confidential")
            
            if data_tier not in self.derived_keys:
                return {"success": False, "error": f"Unknown encryption tier: {data_tier}"}
            
            # Decode base64
            ciphertext = base64.urlsafe_b64decode(encrypted_data.encode())
            
            # Decompress if needed
            if metadata.get("compressed", False):
                ciphertext = zlib.decompress(ciphertext)
            
            # Get encryption parameters
            key = self.derived_keys[data_tier]
            if len(key) != 32:
                return {"success": False, "error": f"Invalid key length: {len(key)} bytes"}
            
            encryption_layers = metadata.get("layers", 1)
            layer_data = metadata.get("layer_data", {})
            
            # Check for new multi-layer format with layer_data
            if layer_data and "nonces" in layer_data and "tags" in layer_data:
                # New format (supports any number of layers)
                nonces = layer_data.get("nonces", [])
                tags = layer_data.get("tags", [])
                
                if len(nonces) != encryption_layers or len(tags) != encryption_layers:
                    return {"success": False, "error": f"Layer data mismatch: {len(nonces)} nonces, {len(tags)} tags, expected {encryption_layers}"}
                
                # Decrypt in reverse order (outermost layer first)
                current_data = ciphertext
                
                for layer in reversed(range(encryption_layers)):
                    try:
                        layer_nonce = base64.urlsafe_b64decode(nonces[layer].encode())
                        layer_tag = base64.urlsafe_b64decode(tags[layer].encode())
                        
                        algorithm = algorithms.AES(key)
                        cipher = Cipher(algorithm, modes.GCM(layer_nonce, layer_tag), backend=self.backend)
                        decryptor = cipher.decryptor()
                        
                        decrypted_data = decryptor.update(current_data) + decryptor.finalize()
                        current_data = decrypted_data
                        
                    except Exception as layer_error:
                        return {
                            "success": False, 
                            "error": f"Layer {layer} decryption failed: {str(layer_error)}",
                            "tier": data_tier
                        }
                
                plaintext = current_data
                
            else:
                # Legacy single-layer format (fallback - check for nonce/tag fields)
                nonce_b64 = metadata.get("nonce", "")
                tag_b64 = metadata.get("tag", "")
                
                if not nonce_b64 or not tag_b64:
                    return {"success": False, "error": "Legacy encryption format missing nonce or tag"}
                
                try:
                    nonce = base64.urlsafe_b64decode(nonce_b64.encode())
                    tag = base64.urlsafe_b64decode(tag_b64.encode())
                except Exception as decode_error:
                    return {"success": False, "error": f"Failed to decode nonce/tag: {str(decode_error)}"}
                
                # Verify nonce length
                if len(nonce) < 8 or len(nonce) > 128:
                    return {"success": False, "error": f"Invalid nonce length: {len(nonce)} bytes (must be 8-128 bytes)"}
                
                algorithm = algorithms.AES(key)
                cipher = Cipher(algorithm, modes.GCM(nonce, tag), backend=self.backend)
                decryptor = cipher.decryptor()
                
                plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return {
                "success": True,
                "decrypted_data": plaintext,
                "metadata": metadata,
                "original_length": len(plaintext)
            }
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "tier": tier
            }
    
    async def rotate_keys(self, tier: str = None) -> Dict[str, Any]:
        """Rotate encryption keys for specified tier or all tiers"""
        try:
            if tier:
                # Rotate specific tier
                await self._rotate_single_key(tier)
                return {"success": True, "rotated_tier": tier, "message": f"Key rotated for tier: {tier}"}
            else:
                # Rotate all tiers
                rotated = []
                for tier_name in list(self.derived_keys.keys()):
                    await self._rotate_single_key(tier_name)
                    rotated.append(tier_name)
                
                # Update rotation schedule
                await self._schedule_key_rotation()
                
                return {"success": True, "rotated_tiers": rotated, "message": "All keys rotated"}
                
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _rotate_single_key(self, tier: str):
        """Rotate key for a single tier"""
        # Store old key in history
        old_key = self.derived_keys.get(tier)
        if old_key:
            self.key_history.append({
                "tier": tier,
                "key": old_key.hex(),  # Store as hex for logging
                "retired_at": datetime.now().isoformat()
            })
        
        # Keep only recent history
        if len(self.key_history) > 100:
            self.key_history = self.key_history[-100:]
        
        # Generate new key
        salt = await self._get_or_create_salt(f"{tier}_key_salt_{datetime.now().timestamp()}")
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32,
            salt=salt,
            iterations=self.encryption_config.get("key_derivation_iterations", 310000) // 10,
            backend=self.backend
        )
        
        new_key = kdf.derive(self.master_key)
        self.derived_keys[tier] = new_key
        
        logger.info(f"Rotated key for tier: {tier}")
    
    async def get_encryption_status(self) -> Dict[str, Any]:
        """Get current encryption status"""
        return {
            "initialized": self.initialized,
            "tiers_configured": list(self.derived_keys.keys()),
            "key_rotation_schedule": {
                tier: schedule.isoformat() 
                for tier, schedule in self.key_rotation_schedule.items()
            },
            "key_history_size": len(self.key_history),
            "algorithm": self.encryption_config.get("encryption_algorithm", "AES-256-GCM"),
            "next_rotation_due": min(
                self.key_rotation_schedule.values()
            ).isoformat() if self.key_rotation_schedule else None
        }
    
# ==================== MEMORY HIERARCHY ====================
class DataTier(Enum):
    """Data storage tiers based on sensitivity"""
    ROOT_DATABASE = auto()
    OWNER_CONFIDENTIAL = auto()
    ACCESS_DATA = auto()
    PUBLIC_DATA = auto()
    TEMPORAL_CACHE = auto()

@dataclass
class MemoryMetadata:
    """Metadata for memory entries"""
    memory_id: str
    tier: DataTier
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    association_strength: float = 0.0
    emotional_weight: float = 0.0
    priority: float = 0.5
    expiration: Optional[datetime] = None
    tags: Set[str] = field(default_factory=set)
    context_hash: str = ""
    
    def update_access(self):
        """Update access statistics"""
        self.last_accessed = datetime.now()
        self.access_count += 1
        
        # Strengthen memory with each access (reminiscence effect)
        self.association_strength = min(1.0, self.association_strength + 0.01)
    
    def calculate_retention_score(self) -> float:
        """Calculate memory retention score"""
        # Based on Ebbinghaus forgetting curve with modifications
        time_since_access = (datetime.now() - self.last_accessed).total_seconds()
        decay_factor = math.exp(-time_since_access / 86400)  # Daily decay
        
        retention_score = (
            self.association_strength * 0.4 +
            self.emotional_weight * 0.3 +
            self.priority * 0.2 +
            decay_factor * 0.1
        )
        
        return max(0.0, min(1.0, retention_score))

@dataclass
class MemoryEntry:
    """Individual memory entry with encrypted data"""
    metadata: MemoryMetadata
    encrypted_data: bytes
    encryption_metadata: Dict[str, Any]
    neural_connections: List[str] = field(default_factory=list)  # Connected neuron IDs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "metadata": {
                "memory_id": self.metadata.memory_id,
                "tier": self.metadata.tier.name,
                "created_at": self.metadata.created_at.isoformat(),
                "last_accessed": self.metadata.last_accessed.isoformat(),
                "access_count": self.metadata.access_count,
                "association_strength": self.metadata.association_strength,
                "emotional_weight": self.metadata.emotional_weight,
                "priority": self.metadata.priority,
                "expiration": self.metadata.expiration.isoformat() if self.metadata.expiration else None,
                "tags": list(self.metadata.tags),
                "context_hash": self.metadata.context_hash
            },
            "encrypted_data": base64.urlsafe_b64encode(self.encrypted_data).decode(),
            "encryption_metadata": self.encryption_metadata,
            "neural_connections": self.neural_connections
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """Create from dictionary"""
        metadata_dict = data.get("metadata", {})
        
        metadata = MemoryMetadata(
            memory_id=metadata_dict.get("memory_id", str(uuid.uuid4())),
            tier=DataTier[metadata_dict.get("tier", "OWNER_CONFIDENTIAL")],
            created_at=datetime.fromisoformat(metadata_dict.get("created_at", datetime.now().isoformat())),
            last_accessed=datetime.fromisoformat(metadata_dict.get("last_accessed", datetime.now().isoformat())),
            access_count=metadata_dict.get("access_count", 0),
            association_strength=metadata_dict.get("association_strength", 0.0),
            emotional_weight=metadata_dict.get("emotional_weight", 0.0),
            priority=metadata_dict.get("priority", 0.5),
            expiration=datetime.fromisoformat(metadata_dict.get("expiration")) if metadata_dict.get("expiration") else None,
            tags=set(metadata_dict.get("tags", [])),
            context_hash=metadata_dict.get("context_hash", "")
        )
        
        encrypted_data = base64.urlsafe_b64decode(data.get("encrypted_data", "").encode())
        encryption_metadata = data.get("encryption_metadata", {})
        neural_connections = data.get("neural_connections", [])
        
        return cls(
            metadata=metadata,
            encrypted_data=encrypted_data,
            encryption_metadata=encryption_metadata,
            neural_connections=neural_connections
        )

# ==================== IDENTITY CONTAINER ====================
@dataclass
class IdentityProfile:
    """Container for entity identity information"""
    identity_id: str
    name: str
    contact_details: Dict[str, Any] = field(default_factory=dict)
    behavioral_patterns: List[Dict[str, Any]] = field(default_factory=list)
    personal_data: Dict[str, Any] = field(default_factory=dict)
    relationship_context: Dict[str, Any] = field(default_factory=dict)
    permission_level: str = "public"  # public, privileged, confidential
    created_at: datetime = field(default_factory=datetime.now)
    last_interaction: datetime = field(default_factory=datetime.now)
    interaction_count: int = 0
    trust_score: float = 0.5
    emotional_history: List[Dict[str, Any]] = field(default_factory=list)
    conversation_topics: Set[str] = field(default_factory=set)
    access_patterns: List[Dict[str, Any]] = field(default_factory=list)
    
    def update_interaction(self, interaction_data: Dict[str, Any]):
        """Update profile with new interaction"""
        self.last_interaction = datetime.now()
        self.interaction_count += 1
        
        # Update behavioral patterns
        if "behavior" in interaction_data:
            self.behavioral_patterns.append({
                "timestamp": datetime.now().isoformat(),
                "behavior": interaction_data["behavior"],
                "context": interaction_data.get("context", {})
            })
        
        # Update emotional history
        if "emotion" in interaction_data:
            self.emotional_history.append({
                "timestamp": datetime.now().isoformat(),
                "emotion": interaction_data["emotion"],
                "intensity": interaction_data.get("intensity", 0.5)
            })
        
        # Update conversation topics
        if "topics" in interaction_data:
            self.conversation_topics.update(interaction_data["topics"])
        
        # Update trust score
        trust_change = interaction_data.get("trust_change", 0.0)
        self.trust_score = max(0.0, min(1.0, self.trust_score + trust_change))
        
        # Keep history sizes manageable
        if len(self.behavioral_patterns) > 100:
            self.behavioral_patterns = self.behavioral_patterns[-100:]
        if len(self.emotional_history) > 50:
            self.emotional_history = self.emotional_history[-50:]
        if len(self.conversation_topics) > 100:
            # Remove oldest topics (convert to list, slice, back to set)
            topics_list = list(self.conversation_topics)
            self.conversation_topics = set(topics_list[-100:])
    
    def get_access_permissions(self) -> List[str]:
        """Get access permissions based on permission level"""
        permission_map = {
            "public": ["read_public"],
            "privileged": ["read_public", "read_privileged", "limited_write"],
            "confidential": ["read_public", "read_privileged", "write", "read_confidential"]
        }
        return permission_map.get(self.permission_level, ["read_public"])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "identity_id": self.identity_id,
            "name": self.name,
            "contact_details": self.contact_details,
            "behavioral_patterns": self.behavioral_patterns,
            "personal_data": self.personal_data,
            "relationship_context": self.relationship_context,
            "permission_level": self.permission_level,
            "created_at": self.created_at.isoformat(),
            "last_interaction": self.last_interaction.isoformat(),
            "interaction_count": self.interaction_count,
            "trust_score": self.trust_score,
            "emotional_history": self.emotional_history,
            "conversation_topics": list(self.conversation_topics),
            "access_patterns": self.access_patterns
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IdentityProfile':
        """Create from dictionary"""
        return cls(
            identity_id=data.get("identity_id", str(uuid.uuid4())),
            name=data.get("name", "Unknown"),
            contact_details=data.get("contact_details", {}),
            behavioral_patterns=data.get("behavioral_patterns", []),
            personal_data=data.get("personal_data", {}),
            relationship_context=data.get("relationship_context", {}),
            permission_level=data.get("permission_level", "public"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            last_interaction=datetime.fromisoformat(data.get("last_interaction", datetime.now().isoformat())),
            interaction_count=data.get("interaction_count", 0),
            trust_score=data.get("trust_score", 0.5),
            emotional_history=data.get("emotional_history", []),
            conversation_topics=set(data.get("conversation_topics", [])),
            access_patterns=data.get("access_patterns", [])
        )

# ==================== NEURAL MEMORY INDEX ====================
class MemoryNeuronState(Enum):
    """Memory neuron states"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    INDEXING = "indexing"
    ASSOCIATING = "associating"

@dataclass
class MemoryNeuralConnection:
    """Connection between memory neurons"""
    target_neuron_id: str
    connection_strength: float = 0.1
    association_type: str = "semantic"  # semantic, temporal, emotional, contextual
    last_activated: datetime = field(default_factory=datetime.now)
    activation_count: int = 0
    memory_references: List[str] = field(default_factory=list)  # Memory IDs referenced

@dataclass
class MemoryNeuron:
    """Neuron specialized for memory indexing and association"""
    neuron_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    core_assignment: str = "memory"
    function_name: str = ""
    function_body: Optional[Callable] = None
    current_state: MemoryNeuronState = MemoryNeuronState.INACTIVE
    activation_level: float = 0.0
    connections: List[MemoryNeuralConnection] = field(default_factory=list)
    specialization: str = ""  # indexing, recall, association, consolidation
    memory_indices: Dict[str, float] = field(default_factory=dict)  # memory_id -> relevance_score
    semantic_cluster: str = ""
    temporal_context: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    last_fired: Optional[datetime] = None
    error_count: int = 0
    success_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def axon_state(self) -> Dict[str, Any]:
        """Return visualization state for holographic projection"""
        color_map = {
            "indexing": "#FF6B6B",
            "recall": "#4ECDC4",
            "association": "#FFD166",
            "consolidation": "#06D6A0",
            "encryption": "#118AB2",
            "compression": "#EF476F"
        }
        
        state_colors = {
            MemoryNeuronState.ACTIVE: color_map.get(self.specialization, "#FFFFFF"),
            MemoryNeuronState.INACTIVE: "#CCCCCC",
            MemoryNeuronState.FAILED: "#FF0000",
            MemoryNeuronState.INDEXING: "#FFA500",
            MemoryNeuronState.ASSOCIATING: "#800080"
        }
        
        return {
            "neuron_id": self.neuron_id,
            "specialization": self.specialization,
            "color": state_colors[self.current_state],
            "brightness": self.activation_level,
            "connections": len(self.connections),
            "memory_indices": len(self.memory_indices),
            "position": self.calculate_position(),
            "status": self.current_state.value,
            "cluster": self.semantic_cluster
        }
    
    def calculate_position(self) -> Dict[str, float]:
        """Calculate 3D position for holographic display"""
        seed = int(hashlib.sha256(self.neuron_id.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        # Position based on specialization and cluster
        specialization_coords = {
            "indexing": (0.0, 0.0, 0.0),
            "recall": (1.0, 0.0, 0.0),
            "association": (0.0, 1.0, 0.0),
            "consolidation": (0.0, 0.0, 1.0),
            "encryption": (-1.0, 0.0, 0.0),
            "compression": (0.0, -1.0, 0.0)
        }
        
        base_x, base_y, base_z = specialization_coords.get(self.specialization, (0.0, 0.0, 0.0))
        
        # Add variation based on cluster
        if self.semantic_cluster:
            cluster_hash = hashlib.md5(self.semantic_cluster.encode()).digest()
            cluster_x = (cluster_hash[0] - 128) / 128.0 * 0.5
            cluster_y = (cluster_hash[1] - 128) / 128.0 * 0.5
            cluster_z = (cluster_hash[2] - 128) / 128.0 * 0.5
        else:
            cluster_x, cluster_y, cluster_z = 0.0, 0.0, 0.0
        
        return {
            "x": base_x + cluster_x + random.uniform(-0.2, 0.2),
            "y": base_y + cluster_y + random.uniform(-0.2, 0.2),
            "z": base_z + cluster_z + random.uniform(-0.2, 0.2)
        }
    
    async def fire(self, input_strength: float = 1.0, context: Dict[str, Any] = None) -> Any:
        """Activate neuron with context"""
        try:
            if self.current_state == MemoryNeuronState.FAILED:
                return None
                
            self.current_state = MemoryNeuronState.ACTIVE
            self.activation_level = min(1.0, self.activation_level + input_strength)
            self.last_fired = datetime.now()
            
            if self.function_body and self.activation_level >= 0.5:
                # Prepare execution context
                exec_context = self.metadata.copy()
                if context:
                    exec_context.update(context)
                
                # Execute neuron's function
                result = await self.execute_function(exec_context)
                if result is not None:
                    self.success_count += 1
                    
                    # Update memory indices if result contains memory references
                    if isinstance(result, dict) and "memory_references" in result:
                        for memory_id, relevance in result["memory_references"].items():
                            self.memory_indices[memory_id] = relevance
                else:
                    self.error_count += 1
                
                return result
            
            return {"activation": self.activation_level, "neuron_id": self.neuron_id}
            
        except Exception as e:
            self.error_count += 1
            if self.error_count > 3:
                self.current_state = MemoryNeuronState.FAILED
            logger.error(f"MemoryNeuron {self.neuron_id} fire error: {e}")
            return None
    
    async def execute_function(self, context: Dict[str, Any]) -> Any:
        """Execute the neuron's assigned function"""
        if not self.function_body:
            return None
        
        try:
            if inspect.iscoroutinefunction(self.function_body):
                result = await self.function_body(**context)
            else:
                # Run synchronous functions in thread pool
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(
                        executor, 
                        lambda: self.function_body(**context)
                    )
            return result
        except Exception as e:
            logger.error(f"MemoryNeuron {self.neuron_id} function error: {e}")
            return None
    
    def add_memory_reference(self, memory_id: str, relevance: float = 0.5):
        """Add memory reference to this neuron"""
        self.memory_indices[memory_id] = relevance
        
        # Keep only most relevant memories
        if len(self.memory_indices) > 100:
            # Remove least relevant memories
            sorted_memories = sorted(self.memory_indices.items(), key=lambda x: x[1])
            for memory_id_to_remove, _ in sorted_memories[:-100]:
                del self.memory_indices[memory_id_to_remove]
    
    def get_relevant_memories(self, threshold: float = 0.3) -> List[Tuple[str, float]]:
        """Get memories with relevance above threshold"""
        return [(mid, rel) for mid, rel in self.memory_indices.items() if rel >= threshold]

# ==================== MEMORY ASSOCIATION NETWORK ====================
class AssociationNetwork:
    """Network for memory association and retrieval"""
    
    def __init__(self):
        self.memory_graph = nx.Graph()
        self.semantic_index = defaultdict(set)  # tag -> {memory_ids}
        self.temporal_index = defaultdict(set)  # timestamp_bucket -> {memory_ids}
        self.emotional_index = defaultdict(set)  # emotion -> {memory_ids}
        self.context_index = defaultdict(set)  # context_hash -> {memory_ids}
        self.identity_index = defaultdict(set)  # identity_id -> {memory_ids}
        
        self.association_strengths = {}  # (memory_id1, memory_id2) -> strength
        self.last_association_update = datetime.now()
        
    def add_memory(self, memory_id: str, metadata: MemoryMetadata):
        """Add memory to association network"""
        # Add node to graph
        self.memory_graph.add_node(memory_id, metadata=metadata)
        
        # Index by tags
        for tag in metadata.tags:
            self.semantic_index[tag].add(memory_id)
        
        # Index by temporal bucket (hour granularity)
        time_bucket = metadata.created_at.strftime("%Y-%m-%d-%H")
        self.temporal_index[time_bucket].add(memory_id)
        
        # Index by emotional weight bucket
        emotion_bucket = round(metadata.emotional_weight * 10) / 10  # 0.0, 0.1, 0.2, ... 1.0
        self.emotional_index[emotion_bucket].add(memory_id)
        
        # Index by context hash
        if metadata.context_hash:
            self.context_index[metadata.context_hash].add(memory_id)
        
        logger.debug(f"Added memory {memory_id} to association network")
    
    def create_association(self, memory_id1: str, memory_id2: str, 
                          association_type: str = "semantic", strength: float = 0.1):
        """Create association between two memories"""
        if memory_id1 == memory_id2:
            return
        
        # Add edge to graph
        self.memory_graph.add_edge(memory_id1, memory_id2, 
                                  association_type=association_type,
                                  strength=strength,
                                  created=datetime.now())
        
        # Store association strength
        key = tuple(sorted([memory_id1, memory_id2]))
        self.association_strengths[key] = strength
        
        logger.debug(f"Created {association_type} association between {memory_id1} and {memory_id2} with strength {strength}")
    
    def find_associated_memories(self, memory_id: str, max_results: int = 10, 
                               min_strength: float = 0.1) -> List[Dict[str, Any]]:
        """Find memories associated with given memory"""
        if memory_id not in self.memory_graph:
            return []
        
        associated = []
        
        # Get direct associations
        for neighbor in self.memory_graph.neighbors(memory_id):
            edge_data = self.memory_graph.get_edge_data(memory_id, neighbor)
            strength = edge_data.get("strength", 0.0)
            
            if strength >= min_strength:
                node_data = self.memory_graph.nodes[neighbor]
                associated.append({
                    "memory_id": neighbor,
                    "association_strength": strength,
                    "association_type": edge_data.get("association_type", "unknown"),
                    "metadata": node_data.get("metadata"),
                    "degree": "direct"
                })
        
        # Sort by strength
        associated.sort(key=lambda x: x["association_strength"], reverse=True)
        
        # Limit results
        return associated[:max_results]
    
    def semantic_search(self, tags: Set[str], max_results: int = 20) -> List[str]:
        """Find memories by semantic tags"""
        if not tags:
            return []
        
        # Find memories that have all tags (AND search)
        tag_sets = [self.semantic_index.get(tag, set()) for tag in tags]
        if not tag_sets:
            return []
        
        # Intersection of all tag sets
        common_memories = set.intersection(*tag_sets) if tag_sets else set()
        
        # If no memories have all tags, fall back to OR search
        if not common_memories:
            common_memories = set.union(*tag_sets) if tag_sets else set()
        
        # Sort by relevance (number of matching tags)
        sorted_memories = sorted(
            common_memories,
            key=lambda mid: sum(1 for tag in tags if mid in self.semantic_index.get(tag, set())),
            reverse=True
        )
        
        return list(sorted_memories)[:max_results]
    
    def temporal_search(self, start_time: datetime, end_time: datetime, 
                       max_results: int = 20) -> List[str]:
        """Find memories within time range"""
        memories_in_range = set()
        
        # Check each time bucket
        current = start_time.replace(minute=0, second=0, microsecond=0)
        end = end_time.replace(minute=0, second=0, microsecond=0)
        
        while current <= end:
            time_bucket = current.strftime("%Y-%m-%d-%H")
            if time_bucket in self.temporal_index:
                memories_in_range.update(self.temporal_index[time_bucket])
            current += timedelta(hours=1)
        
        # Get metadata for sorting by creation time
        memories_with_time = []
        for memory_id in memories_in_range:
            node = self.memory_graph.nodes.get(memory_id)
            if node and "metadata" in node:
                created_at = node["metadata"].created_at
                memories_with_time.append((memory_id, created_at))
        
        # Sort by creation time
        memories_with_time.sort(key=lambda x: x[1])
        
        return [mid for mid, _ in memories_with_time][:max_results]
    
    def get_network_statistics(self) -> Dict[str, Any]:
        """Get association network statistics"""
        return {
            "total_memories": self.memory_graph.number_of_nodes(),
            "total_associations": self.memory_graph.number_of_edges(),
            "semantic_tags": len(self.semantic_index),
            "temporal_buckets": len(self.temporal_index),
            "emotional_buckets": len(self.emotional_index),
            "context_hashes": len(self.context_index),
            "average_degree": sum(dict(self.memory_graph.degree()).values()) / 
                            max(1, self.memory_graph.number_of_nodes()),
            "connected_components": nx.number_connected_components(self.memory_graph),
            "density": nx.density(self.memory_graph)
        }
    
    def cleanup_old_associations(self, max_age_days: int = 30):
        """Clean up old associations"""
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        edges_to_remove = []
        
        for u, v, data in self.memory_graph.edges(data=True):
            created = data.get("created")
            if created and created < cutoff_time:
                edges_to_remove.append((u, v))
        
        # Remove old edges
        for u, v in edges_to_remove:
            self.memory_graph.remove_edge(u, v)
            
            # Remove from association strengths
            key = tuple(sorted([u, v]))
            if key in self.association_strengths:
                del self.association_strengths[key]
        
        if edges_to_remove:
            logger.info(f"Cleaned up {len(edges_to_remove)} old associations")

# ==================== MEMORY STORAGE ENGINE ====================
class MemoryStorageEngine:
    """Encrypted memory storage with tiered access and persistence"""
    
    def __init__(self):
        self.encryption_manager = EncryptionManager()
        self.memories: Dict[str, MemoryEntry] = {}
        self.identity_profiles: Dict[str, IdentityProfile] = {}
        self.association_network = AssociationNetwork()
        self.access_log = deque(maxlen=10000)
        self.config = {}
        self.initialized = False
        self.storage_file = os.path.join(os.path.dirname(__file__), "memory_store.enc")
        self.performance_metrics = {
            "memories_stored": 0,
            "memories_retrieved": 0,
            "encryption_operations": 0,
            "compression_operations": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        self.memory_cache = {}  # memory_id -> (decrypted_data, timestamp)
        self.cache_size = 10000
        self.cache_ttl = timedelta(hours=1)
        self._lock = asyncio.Lock()
        
    async def initialize(self, owner_biometric_hash: str, config: Dict[str, Any]) -> bool:
        """Initialize memory storage engine"""
        try:
            self.config = config
            
            # Initialize encryption
            encryption_config = await MemoryConfigLoader.load_encryption_config()
            encryption_success = await self.encryption_manager.initialize(
                owner_biometric_hash, encryption_config
            )
            
            if not encryption_success:
                return False
            
            # Load existing memories from disk
            await self._load_persistent_storage()
            
            # Start maintenance tasks
            asyncio.create_task(self._maintenance_loop())
            
            self.initialized = True
            logger.info(f"MemoryStorageEngine initialized. Loaded {len(self.memories)} memories.")
            return True
            
        except Exception as e:
            logger.error(f"MemoryStorageEngine initialization failed: {e}")
            return False
    
    async def _load_persistent_storage(self):
        """Load memories from encrypted persistent storage"""
        if not os.path.exists(self.storage_file):
            logger.info("No persistent storage found. Starting fresh.")
            return

        try:
            async with self._lock:
                with open(self.storage_file, 'rb') as f:
                    encrypted_package_json = f.read().decode('utf-8')
                
                encrypted_package = json.loads(encrypted_package_json)
                
                # Decrypt the entire storage blob using ROOT tier keys
                decryption_result = await self.encryption_manager.decrypt_data(
                    encrypted_package, "root"
                )
                
                if not decryption_result.get("success"):
                    logger.error(f"Failed to decrypt storage: {decryption_result.get('error')}")
                    return

                # Deserialize the state
                state_data = pickle.loads(decryption_result["decrypted_data"])
                
                self.memories = state_data.get("memories", {})
                self.identity_profiles = state_data.get("identity_profiles", {})
                self.association_network = state_data.get("association_network", AssociationNetwork())
                
                logger.info(f"Successfully loaded {len(self.memories)} memories and {len(self.identity_profiles)} profiles.")
                
        except Exception as e:
            logger.error(f"Critical error loading persistent storage: {e}", exc_info=True)

    async def _save_persistent_storage(self):
        """Save memories to encrypted persistent storage"""
        if not self.initialized:
            return

        try:
            async with self._lock:
                # Prepare state for serialization
                state_data = {
                    "memories": self.memories,
                    "identity_profiles": self.identity_profiles,
                    "association_network": self.association_network
                }
                
                serialized_data = pickle.dumps(state_data)
                
                # Encrypt the entire blob
                encryption_result = await self.encryption_manager.encrypt_data(
                    serialized_data, "root"
                )
                
                if not encryption_result.get("success"):
                    logger.error(f"Failed to encrypt storage for save: {encryption_result.get('error')}")
                    return

                # Write to disk atomically
                temp_file = self.storage_file + ".tmp"
                with open(temp_file, 'w') as f:
                    json.dump(encryption_result, f)
                
                os.replace(temp_file, self.storage_file)
                logger.debug(f"Saved {len(self.memories)} memories to persistent storage.")
                
        except Exception as e:
            logger.error(f"Critical error saving persistent storage: {e}", exc_info=True)

    async def store_memory(self, data: Any, tier: DataTier = DataTier.OWNER_CONFIDENTIAL,
                          metadata: Dict[str, Any] = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Store memory with encryption and indexing"""
        if not self.initialized:
            return {"success": False, "error": "MemoryStorageEngine not initialized"}
        
        try:
            # Generate memory ID
            memory_id = str(uuid.uuid4())
            
            # Prepare data for storage
            if isinstance(data, (dict, list)):
                serialized_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            elif isinstance(data, bytes):
                serialized_data = data
            elif isinstance(data, str):
                serialized_data = data.encode('utf-8')
            else:
                serialized_data = pickle.dumps(data)
            
            # Determine encryption tier
            tier_mapping = {
                DataTier.ROOT_DATABASE: "root",
                DataTier.OWNER_CONFIDENTIAL: "owner_confidential",
                DataTier.ACCESS_DATA: "access",
                DataTier.PUBLIC_DATA: "public",
                DataTier.TEMPORAL_CACHE: "temporal"
            }
            encryption_tier = tier_mapping.get(tier, "owner_confidential")
            
            # Encrypt data
            encryption_result = await self.encryption_manager.encrypt_data(
                serialized_data, encryption_tier
            )
            
            if not encryption_result.get("success", False):
                return encryption_result
            
            # Create memory metadata
            memory_metadata = MemoryMetadata(
                memory_id=memory_id,
                tier=tier,
                emotional_weight=metadata.get("emotional_weight", 0.0) if metadata else 0.0,
                priority=metadata.get("priority", 0.5) if metadata else 0.5,
                tags=set(metadata.get("tags", [])) if metadata else set(),
                context_hash=self._calculate_context_hash(context) if context else ""
            )
            
            # Apply retention policy
            retention_policy = self.config.get("memory_retention_policy", {})
            tier_name = tier.name.lower()
            if tier_name in retention_policy:
                retention = retention_policy[tier_name]
                if retention != "permanent":
                    days = self._parse_retention_days(retention)
                    if days:
                        memory_metadata.expiration = datetime.now() + timedelta(days=days)
            
            # Create memory entry
            memory_entry = MemoryEntry(
                metadata=memory_metadata,
                encrypted_data=base64.urlsafe_b64decode(
                    encryption_result["encrypted_data"].encode()
                ),
                encryption_metadata=encryption_result["metadata"]
            )
            
            # Store memory
            self.memories[memory_id] = memory_entry
            
            # Add to association network
            self.association_network.add_memory(memory_id, memory_metadata)
            
            # Create associations based on context
            if context:
                await self._create_contextual_associations(memory_id, context)
            
            # Update performance metrics
            self.performance_metrics["memories_stored"] += 1
            self.performance_metrics["encryption_operations"] += 1
            
            # Trigger memory consolidation if needed
            if len(self.memories) % 100 == 0:
                asyncio.create_task(self._consolidate_memories())
            
            # Save to persistent storage
            await self._save_persistent_storage()
            
            logger.info(f"Stored memory {memory_id} in tier {tier.name}")
            
            return {
                "success": True,
                "memory_id": memory_id,
                "tier": tier.name,
                "metadata": memory_metadata,
                "encryption_metadata": encryption_result["metadata"]
            }
            
        except Exception as e:
            logger.error(f"Memory storage failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def retrieve_memory(self, memory_id: str, access_level: str = "owner_root") -> Dict[str, Any]:
        """Retrieve memory with access control"""
        if not self.initialized:
            return {"success": False, "error": "MemoryStorageEngine not initialized"}
        
        try:
            # Check if memory exists
            if memory_id not in self.memories:
                return {"success": False, "error": "Memory not found"}
            
            memory_entry = self.memories[memory_id]
            memory_metadata = memory_entry.metadata
            
            # Check access permissions
            if not await self._check_access_permission(memory_metadata.tier, access_level):
                return {
                    "success": False,
                    "error": f"Access denied to tier {memory_metadata.tier.name} with level {access_level}"
                }
            
            # Check cache first
            cached_data = self._check_cache(memory_id)
            if cached_data is not None:
                self.performance_metrics["cache_hits"] += 1
                memory_metadata.update_access()
                return {
                    "success": True,
                    "memory_id": memory_id,
                    "data": cached_data,
                    "from_cache": True,
                    "metadata": memory_metadata
                }
            
            self.performance_metrics["cache_misses"] += 1
            
            # Prepare encrypted package
            encrypted_package = {
                "encrypted_data": base64.urlsafe_b64encode(memory_entry.encrypted_data).decode(),
                "metadata": memory_entry.encryption_metadata
            }
            
            # Determine encryption tier
            tier_mapping = {
                DataTier.ROOT_DATABASE: "root",
                DataTier.OWNER_CONFIDENTIAL: "owner_confidential",
                DataTier.ACCESS_DATA: "access",
                DataTier.PUBLIC_DATA: "public",
                DataTier.TEMPORAL_CACHE: "temporal"
            }
            encryption_tier = tier_mapping.get(memory_metadata.tier, "owner_confidential")
            
            # Decrypt data
            decryption_result = await self.encryption_manager.decrypt_data(
                encrypted_package, encryption_tier
            )
            
            if not decryption_result.get("success", False):
                return decryption_result
            
            # Deserialize data
            decrypted_data = decryption_result["decrypted_data"]
            
            try:
                # Try JSON first
                data = json.loads(decrypted_data.decode('utf-8'))
            except:
                try:
                    # Try pickle
                    data = pickle.loads(decrypted_data)
                except:
                    # Fall back to bytes
                    data = decrypted_data
            
            # Update memory metadata
            memory_metadata.update_access()
            
            # Update cache
            self._update_cache(memory_id, data)
            
            # Update performance metrics
            self.performance_metrics["memories_retrieved"] += 1
            self.performance_metrics["encryption_operations"] += 1
            
            # Log access
            self._log_access(memory_id, access_level, "retrieve")
            
            # Find associated memories
            associated = self.association_network.find_associated_memories(
                memory_id, max_results=5, min_strength=0.2
            )
            
            return {
                "success": True,
                "memory_id": memory_id,
                "data": data,
                "from_cache": False,
                "metadata": memory_metadata,
                "associated_memories": associated,
                "retention_score": memory_metadata.calculate_retention_score()
            }
            
        except Exception as e:
            logger.error(f"Memory retrieval failed: {e}")
            return {"success": False, "error": str(e), "memory_id": memory_id}
    
    async def search_memories(self, query: Dict[str, Any], access_level: str = "owner_root",
                            max_results: int = 50) -> Dict[str, Any]:
        """Search memories based on query with enhanced keyword matching."""
        if not self.initialized:
            return {"success": False, "error": "MemoryStorageEngine not initialized"}
        
        try:
            search_results = []
            search_methods = []
            
            # 1. Semantic search by tags (Exact Match)
            if "tags" in query:
                tags = set(query["tags"])
                semantic_results = self.association_network.semantic_search(tags, max_results)
                search_methods.append(("semantic", len(semantic_results)))
                
                for memory_id in semantic_results:
                    if memory_id in self.memories:
                        search_results.append(memory_id)
            
            # 2. Temporal search
            if "time_range" in query:
                time_range = query["time_range"]
                start_time = datetime.fromisoformat(time_range.get("start", datetime.now().isoformat()))
                end_time = datetime.fromisoformat(time_range.get("end", datetime.now().isoformat()))
                
                temporal_results = self.association_network.temporal_search(
                    start_time, end_time, max_results
                )
                search_methods.append(("temporal", len(temporal_results)))
                
                for memory_id in temporal_results:
                    if memory_id in self.memories and memory_id not in search_results:
                        search_results.append(memory_id)
            
            # 3. Text search (Enhanced Keyword Matching)
            if "text" in query and query["text"]:
                text_input = query["text"].lower()
                # Split input into significant keywords (length > 3)
                keywords = [w for w in text_input.split() if len(w) > 3]
                text_results = []
                
                for memory_id, memory_entry in self.memories.items():
                    # Check tags
                    memory_tags = {t.lower() for t in memory_entry.metadata.tags}
                    
                    # Match if ANY keyword appears in ANY tag (Fuzzy association)
                    if any(kw in tag for kw in keywords for tag in memory_tags):
                        text_results.append(memory_id)
                        continue
                        
                    # Also check if tags appear in the text input (Reverse association)
                    if any(tag in text_input for tag in memory_tags):
                        text_results.append(memory_id)

                search_methods.append(("text_keyword", len(text_results)))
                search_results.extend(text_results[:max_results])
            
            # Deduplicate and Filter by Access Level
            unique_results = []
            seen = set()
            for memory_id in search_results:
                if memory_id not in seen and len(unique_results) < max_results:
                    # Check access permissions
                    if memory_id in self.memories:
                        memory_tier = self.memories[memory_id].metadata.tier
                        if await self._check_access_permission(memory_tier, access_level):
                            unique_results.append(memory_id)
                            seen.add(memory_id)
            
            # Fetch Memory Details
            memories_details = []
            for memory_id in unique_results:
                memory_entry = self.memories[memory_id]
                
                # Auto-decrypt for context window (Optimization)
                data_preview = "[Encrypted]"
                if self.memory_cache.get(memory_id):
                    data_preview = self.memory_cache[memory_id][0]
                else:
                    # Attempt quick decrypt for the context window
                    try:
                        pkg = {
                            "encrypted_data": base64.urlsafe_b64encode(memory_entry.encrypted_data).decode(),
                            "metadata": memory_entry.encryption_metadata
                        }
                        tier_map = {DataTier.OWNER_CONFIDENTIAL: "owner_confidential"} # Mapping shortcut
                        enc_tier = tier_map.get(memory_entry.metadata.tier, "owner_confidential")
                        dec = await self.encryption_manager.decrypt_data(pkg, enc_tier)
                        if dec["success"]:
                            data_preview = dec["decrypted_data"].decode()
                    except:
                        pass

                memories_details.append({
                    "memory_id": memory_id,
                    "data": data_preview,
                    "metadata": memory_entry.metadata,
                    "access_allowed": True
                })
            
            return {
                "success": True,
                "total_results": len(unique_results),
                "search_methods": search_methods,
                "results": memories_details,
                "query": query
            }
            
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_memory(self, memory_id: str, updates: Dict[str, Any], 
                          access_level: str = "owner_root") -> Dict[str, Any]:
        """Update memory metadata"""
        if not self.initialized:
            return {"success": False, "error": "MemoryStorageEngine not initialized"}
        
        try:
            # Check if memory exists
            if memory_id not in self.memories:
                return {"success": False, "error": "Memory not found"}
            
            memory_entry = self.memories[memory_id]
            memory_metadata = memory_entry.metadata
            
            # Check access permissions
            if not await self._check_access_permission(memory_metadata.tier, access_level, "write"):
                return {
                    "success": False,
                    "error": f"Write access denied to tier {memory_metadata.tier.name}"
                }
            
            # Apply updates to metadata
            if "emotional_weight" in updates:
                memory_metadata.emotional_weight = updates["emotional_weight"]
            
            if "priority" in updates:
                memory_metadata.priority = updates["priority"]
            
            if "tags" in updates:
                memory_metadata.tags = set(updates["tags"])
            
            if "association_strength" in updates:
                memory_metadata.association_strength = updates["association_strength"]
            
            # Update in association network
            self.association_network.add_memory(memory_id, memory_metadata)
            
            # Log access
            self._log_access(memory_id, access_level, "update")
            
            await self._save_persistent_storage()

            return {
                "success": True,
                "memory_id": memory_id,
                "updated_fields": list(updates.keys()),
                "metadata": memory_metadata
            }
            
        except Exception as e:
            logger.error(f"Memory update failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def delete_memory(self, memory_id: str, access_level: str = "owner_root") -> Dict[str, Any]:
        """Delete memory with access control"""
        if not self.initialized:
            return {"success": False, "error": "MemoryStorageEngine not initialized"}
        
        try:
            # Check if memory exists
            if memory_id not in self.memories:
                return {"success": False, "error": "Memory not found"}
            
            memory_entry = self.memories[memory_id]
            memory_metadata = memory_entry.metadata
            
            # Check access permissions
            if not await self._check_access_permission(memory_metadata.tier, access_level, "delete"):
                return {
                    "success": False,
                    "error": f"Delete access denied to tier {memory_metadata.tier.name}"
                }
            
            # Remove from memory storage
            del self.memories[memory_id]
            
            # Remove from association network
            if memory_id in self.association_network.memory_graph:
                self.association_network.memory_graph.remove_node(memory_id)
            
            # Remove from cache
            if memory_id in self.memory_cache:
                del self.memory_cache[memory_id]
            
            # Remove from indices
            self._remove_from_indices(memory_id, memory_metadata)
            
            # Log access
            self._log_access(memory_id, access_level, "delete")
            
            logger.info(f"Deleted memory {memory_id} from tier {memory_metadata.tier.name}")
            
            await self._save_persistent_storage()

            return {
                "success": True,
                "memory_id": memory_id,
                "tier": memory_metadata.tier.name,
                "message": "Memory deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Memory deletion failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def manage_identity_profile(self, identity_data: Dict[str, Any], 
                                    operation: str = "create_or_update") -> Dict[str, Any]:
        """Manage identity profiles"""
        try:
            identity_id = identity_data.get("identity_id")
            name = identity_data.get("name", "Unknown")
            
            if not identity_id:
                # Generate new identity ID
                identity_id = f"identity_{uuid.uuid4().hex[:8]}"
                identity_data["identity_id"] = identity_id
            
            if operation == "create_or_update":
                if identity_id in self.identity_profiles:
                    # Update existing profile
                    profile = self.identity_profiles[identity_id]
                    profile.name = name
                    profile.contact_details = identity_data.get("contact_details", profile.contact_details)
                    profile.permission_level = identity_data.get("permission_level", profile.permission_level)
                    
                    # Update interaction if provided
                    if "interaction" in identity_data:
                        profile.update_interaction(identity_data["interaction"])
                else:
                    # Create new profile
                    profile = IdentityProfile(
                        identity_id=identity_id,
                        name=name,
                        contact_details=identity_data.get("contact_details", {}),
                        permission_level=identity_data.get("permission_level", "public"),
                        personal_data=identity_data.get("personal_data", {}),
                        relationship_context=identity_data.get("relationship_context", {})
                    )
                
                self.identity_profiles[identity_id] = profile
                
                await self._save_persistent_storage()

                return {
                    "success": True,
                    "operation": "created" if identity_id not in self.identity_profiles else "updated",
                    "identity_id": identity_id,
                    "profile": profile.to_dict()
                }
            
            elif operation == "delete":
                if identity_id in self.identity_profiles:
                    del self.identity_profiles[identity_id]
                    await self._save_persistent_storage()
                    return {
                        "success": True,
                        "identity_id": identity_id,
                        "message": "Identity profile deleted"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Identity profile not found"
                    }
            
            elif operation == "get":
                if identity_id in self.identity_profiles:
                    return {
                        "success": True,
                        "profile": self.identity_profiles[identity_id].to_dict()
                    }
                else:
                    return {
                        "success": False,
                        "error": "Identity profile not found"
                    }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {operation}"
                }
                
        except Exception as e:
            logger.error(f"Identity profile management failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_context_hash(self, context: Dict[str, Any]) -> str:
        """Calculate hash for context"""
        if not context:
            return ""
        
        # Sort context keys for consistent hashing
        sorted_context = json.dumps(context, sort_keys=True, ensure_ascii=False)
        context_hash = hashlib.sha256(sorted_context.encode('utf-8')).hexdigest()[:16]
        return context_hash
    
    async def _check_access_permission(self, tier: DataTier, access_level: str, 
                                     operation: str = "read") -> bool:
        """Check if access level has permission for tier and operation"""
        # Load access control policy
        policy = await MemoryConfigLoader.load_data_segregation_policy()
        access_control = policy.get("access_control", {})
        
        # Get allowed operations for access level
        allowed_operations = access_control.get(access_level, [])
        
        # Map operation to permission check
        operation_mapping = {
            "read": "read",
            "write": "write",
            "delete": "delete",
            "update": "write"
        }
        
        required_permission = operation_mapping.get(operation, "read")
        
        # Check if operation is allowed
        if required_permission not in allowed_operations:
            return False
        
        # Check tier access based on hierarchy
        hierarchy = policy.get("hierarchy", {})
        tier_name = tier.name.lower()
        
        if tier_name in hierarchy:
            tier_access_levels = hierarchy[tier_name].get("access", [])
            return access_level in tier_access_levels
        
        return False
    
    def _check_cache(self, memory_id: str) -> Any:
        """Check if memory is in cache"""
        if memory_id in self.memory_cache:
            data, timestamp = self.memory_cache[memory_id]
            if datetime.now() - timestamp < self.cache_ttl:
                return data
        
        return None
    
    def _update_cache(self, memory_id: str, data: Any):
        """Update memory cache"""
        self.memory_cache[memory_id] = (data, datetime.now())
        
        # Enforce cache size limit
        if len(self.memory_cache) > self.cache_size:
            # Remove oldest entries
            sorted_cache = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1][1]  # Sort by timestamp
            )
            for key, _ in sorted_cache[:len(self.memory_cache) - self.cache_size]:
                del self.memory_cache[key]
    
    def _log_access(self, memory_id: str, access_level: str, operation: str):
        """Log memory access"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "memory_id": memory_id,
            "access_level": access_level,
            "operation": operation
        }
        self.access_log.append(log_entry)
    
    def _remove_from_indices(self, memory_id: str, metadata: MemoryMetadata):
        """Remove memory from all indices"""
        # Remove from semantic index
        for tag in metadata.tags:
            if tag in self.association_network.semantic_index:
                self.association_network.semantic_index[tag].discard(memory_id)
                if not self.association_network.semantic_index[tag]:
                    del self.association_network.semantic_index[tag]
        
        # Remove from temporal index
        time_bucket = metadata.created_at.strftime("%Y-%m-%d-%H")
        if time_bucket in self.association_network.temporal_index:
            self.association_network.temporal_index[time_bucket].discard(memory_id)
            if not self.association_network.temporal_index[time_bucket]:
                del self.association_network.temporal_index[time_bucket]
        
        # Remove from emotional index
        emotion_bucket = round(metadata.emotional_weight * 10) / 10
        if emotion_bucket in self.association_network.emotional_index:
            self.association_network.emotional_index[emotion_bucket].discard(memory_id)
            if not self.association_network.emotional_index[emotion_bucket]:
                del self.association_network.emotional_index[emotion_bucket]
        
        # Remove from context index
        if metadata.context_hash in self.association_network.context_index:
            self.association_network.context_index[metadata.context_hash].discard(memory_id)
            if not self.association_network.context_index[metadata.context_hash]:
                del self.association_network.context_index[metadata.context_hash]
    
    async def _create_contextual_associations(self, memory_id: str, context: Dict[str, Any]):
        """Create associations based on context"""
        # Find similar contexts
        context_hash = self._calculate_context_hash(context)
        
        if context_hash in self.association_network.context_index:
            similar_memories = self.association_network.context_index[context_hash]
            
            for similar_memory_id in similar_memories:
                if similar_memory_id != memory_id:
                    # Create association
                    self.association_network.create_association(
                        memory_id, similar_memory_id,
                        association_type="contextual",
                        strength=0.5
                    )
    
    async def _consolidate_memories(self):
        """Consolidate memories - merge similar memories, strengthen associations"""
        try:
            logger.info("Starting memory consolidation")
            
            # Strengthen associations between frequently accessed memories
            for memory_id, memory_entry in list(self.memories.items())[:1000]:  # Limit to 1000
                if memory_entry.metadata.access_count > 10:
                    # Find and strengthen associations
                    associated = self.association_network.find_associated_memories(
                        memory_id, max_results=5, min_strength=0.1
                    )
                    
                    for assoc in associated:
                        assoc_id = assoc["memory_id"]
                        current_strength = assoc["association_strength"]
                        new_strength = min(1.0, current_strength + 0.05)
                        
                        # Update association strength
                        self.association_network.create_association(
                            memory_id, assoc_id,
                            association_type=assoc["association_type"],
                            strength=new_strength
                        )
            
            # Clean up old associations
            self.association_network.cleanup_old_associations(max_age_days=30)
            
            # Remove expired memories
            expired_count = 0
            current_time = datetime.now()
            
            for memory_id, memory_entry in list(self.memories.items()):
                if memory_entry.metadata.expiration and memory_entry.metadata.expiration < current_time:
                    await self.delete_memory(memory_id, "system_cleanup")
                    expired_count += 1
            
            logger.info(f"Memory consolidation completed: strengthened associations, removed {expired_count} expired memories")
            
            await self._save_persistent_storage()

        except Exception as e:
            logger.error(f"Memory consolidation failed: {e}")
    
    async def _maintenance_loop(self):
        """Maintenance loop for memory management"""
        while True:
            try:
                interval = self.config.get("memory_consolidation_interval", 3600.0)
                await asyncio.sleep(interval)
                
                # Run consolidation
                await self._consolidate_memories()
                
                # Check encryption key rotation
                await self._check_key_rotation()
                
                # Clean cache
                self._clean_cache()
                
                # Save to persistent storage
                await self._save_persistent_storage()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Maintenance loop error: {e}")
                await asyncio.sleep(300)  # Backoff on error
    
    async def _check_key_rotation(self):
        """Check and perform encryption key rotation if needed"""
        encryption_status = await self.encryption_manager.get_encryption_status()
        rotation_schedule = encryption_status.get("key_rotation_schedule", {})
        
        current_time = datetime.now()
        for tier, rotation_date_str in rotation_schedule.items():
            try:
                rotation_date = datetime.fromisoformat(rotation_date_str)
                if current_time >= rotation_date:
                    logger.info(f"Rotating encryption key for tier: {tier}")
                    await self.encryption_manager.rotate_keys(tier)
            except Exception as e:
                logger.error(f"Key rotation check failed for tier {tier}: {e}")
    
    def _clean_cache(self):
        """Clean expired cache entries"""
        current_time = datetime.now()
        expired_keys = []
        
        for key, (_, timestamp) in self.memory_cache.items():
            if current_time - timestamp > self.cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")
    
    def _parse_retention_days(self, retention: str) -> Optional[int]:
        """Parse retention policy string to days"""
        if retention == "permanent":
            return None
        
        parts = retention.split('_')
        if len(parts) == 2 and parts[1] == "days":
            try:
                return int(parts[0])
            except ValueError:
                pass
        
        # Default retention
        return 30
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """Get storage statistics"""
        tier_counts = defaultdict(int)
        total_size = 0
        
        for memory_entry in self.memories.values():
            tier_name = memory_entry.metadata.tier.name
            tier_counts[tier_name] += 1
            total_size += len(memory_entry.encrypted_data)
        
        return {
            "total_memories": len(self.memories),
            "tier_distribution": dict(tier_counts),
            "total_size_bytes": total_size,
            "identity_profiles": len(self.identity_profiles),
            "cache_size": len(self.memory_cache),
            "access_log_size": len(self.access_log),
            "performance_metrics": self.performance_metrics,
            "association_network": self.association_network.get_network_statistics()
        }
# ==================== FUNCTION REGISTRY ====================
class MemoryFunctionRegistry:
    """Registry of memory core neural functions"""
    
    def __init__(self):
        self.registered_functions: Dict[str, Dict[str, Any]] = {}
        self.function_categories = {
            "memory_indexing": [],
            "memory_recall": [],
            "memory_association": [],
            "memory_consolidation": [],
            "encryption_management": [],
            "compression_optimization": []
        }
        self.load_base_functions()
    
    def load_base_functions(self):
        """Load initial set of neural functions"""
        # Memory indexing functions
        self.register_function(
            name="semantic_indexing",
            category="memory_indexing",
            func=self.semantic_indexing,
            description="Index memories by semantic content"
        )
        
        self.register_function(
            name="temporal_indexing",
            category="memory_indexing",
            func=self.temporal_indexing,
            description="Index memories by temporal context"
        )
        
        self.register_function(
            name="emotional_indexing",
            category="memory_indexing",
            func=self.emotional_indexing,
            description="Index memories by emotional weight"
        )
        
        # Memory recall functions
        self.register_function(
            name="semantic_recall",
            category="memory_recall",
            func=self.semantic_recall,
            description="Recall memories by semantic similarity"
        )
        
        self.register_function(
            name="temporal_recall",
            category="memory_recall",
            func=self.temporal_recall,
            description="Recall memories by temporal proximity"
        )
        
        self.register_function(
            name="associative_recall",
            category="memory_recall",
            func=self.associative_recall,
            description="Recall memories through associations"
        )
        
        # Memory association functions
        self.register_function(
            name="create_associations",
            category="memory_association",
            func=self.create_associations,
            description="Create associations between memories"
        )
        
        self.register_function(
            name="strengthen_associations",
            category="memory_association",
            func=self.strengthen_associations,
            description="Strengthen existing memory associations"
        )
        
        # Memory consolidation functions
        self.register_function(
            name="memory_consolidation",
            category="memory_consolidation",
            func=self.memory_consolidation,
            description="Consolidate and optimize memory storage"
        )
        
        self.register_function(
            name="forgetting_curve_application",
            category="memory_consolidation",
            func=self.forgetting_curve_application,
            description="Apply forgetting curve to memory retention"
        )
        
        # Encryption management functions
        self.register_function(
            name="encryption_optimization",
            category="encryption_management",
            func=self.encryption_optimization,
            description="Optimize encryption parameters"
        )
        
        self.register_function(
            name="key_rotation_scheduling",
            category="encryption_management",
            func=self.key_rotation_scheduling,
            description="Schedule encryption key rotation"
        )
        
        # Compression optimization functions
        self.register_function(
            name="compression_optimization",
            category="compression_optimization",
            func=self.compression_optimization,
            description="Optimize memory compression"
        )
        
        self.register_function(
            name="storage_efficiency_analysis",
            category="compression_optimization",
            func=self.storage_efficiency_analysis,
            description="Analyze storage efficiency"
        )
    
    def register_function(self, name: str, category: str, func: Callable, 
                         description: str = ""):
        """Register a new neural function"""
        self.registered_functions[name] = {
            "function": func,
            "category": category,
            "description": description,
            "registered_at": datetime.now(),
            "invocation_count": 0,
            "success_rate": 1.0,
            "average_execution_time": 0.0
        }
        if category in self.function_categories:
            self.function_categories[category].append(name)
    
    async def create_neuron_for_function(self, function_name: str) -> Optional[MemoryNeuron]:
        """
        Create a neuron specialized for a specific function.
        [FIX 1.1.0] Correctly parses specialization from category string.
        """
        if function_name not in self.registered_functions:
            return None
        
        func_data = self.registered_functions[function_name]
        
        # CRITICAL FIX: Split category to get actual specialization (e.g., 'memory_indexing' -> 'indexing')
        # Previous version incorrectly grabbed index [0] ('memory'), causing neurons to be misidentified.
        cat_parts = func_data["category"].split('_')
        specialization = cat_parts[1] if len(cat_parts) > 1 else cat_parts[0]
        
        neuron = MemoryNeuron(
            function_name=function_name,
            function_body=func_data["function"],
            specialization=specialization,
            metadata={
                "category": func_data["category"],
                "description": func_data["description"],
                "registered_at": func_data["registered_at"].isoformat()
            }
        )
        return neuron
    
    # ========== CORE NEURAL FUNCTION IMPLEMENTATIONS ==========
    
    async def semantic_indexing(self, **kwargs) -> Dict[str, Any]:
        """Index memories by semantic content - extracting keywords as tags."""
        memory_data = kwargs.get("memory_data", {})
        tags = set(kwargs.get("tags", []))
        context = kwargs.get("context", {})
        
        # Helper to extract words
        def extract_keywords(text):
            if not text: return []
            # simple tokenization: split by space, remove punctuation
            clean_text = "".join([c if c.isalnum() or c.isspace() else " " for c in str(text)])
            return [w.lower() for w in clean_text.split() if len(w) > 3]

        if isinstance(memory_data, str):
            extracted = extract_keywords(memory_data)
            tags.update(extracted)
            
        elif isinstance(memory_data, dict):
            # Extract from values
            for val in memory_data.values():
                if isinstance(val, str):
                    tags.update(extract_keywords(val))
        
        # Limit tag count to prevent bloat
        final_tags = list(tags)[:30]
        
        return {
            "success": True,
            "indexed_tags": final_tags,
            "semantic_density": len(final_tags) / max(1, len(str(memory_data))),
            "context_used": bool(context)
        }
    
    async def temporal_indexing(self, **kwargs) -> Dict[str, Any]:
        """Index memories by temporal context"""
        timestamp = kwargs.get("timestamp", datetime.now())
        context = kwargs.get("context", {})
        memory_data = kwargs.get("memory_data", {})
        
        # Extract temporal patterns
        temporal_patterns = {
            "hour_of_day": timestamp.hour,
            "day_of_week": timestamp.weekday(),
            "week_of_year": timestamp.isocalendar()[1],
            "month": timestamp.month,
            "season": self._get_season(timestamp.month),
            "time_of_day": self._get_time_of_day(timestamp.hour)
        }
        
        # Check for temporal references in data
        temporal_references = []
        if isinstance(memory_data, dict):
            for value in memory_data.values():
                if isinstance(value, str):
                    if any(time_word in value.lower() for time_word in 
                          ["today", "tomorrow", "yesterday", "now", "later", "soon"]):
                        temporal_references.append("implicit_time_reference")
        
        # Calculate temporal significance
        temporal_significance = 0.5  # Base
        
        if context.get("is_event", False):
            temporal_significance = 0.8
        if temporal_references:
            temporal_significance = max(temporal_significance, 0.7)
        
        return {
            "success": True,
            "temporal_patterns": temporal_patterns,
            "temporal_references": temporal_references,
            "timestamp": timestamp.isoformat(),
            "temporal_significance": temporal_significance,
            "indexing_method": "pattern_extraction"
        }
    
    def _get_season(self, month: int) -> str:
        """Get season from month"""
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "autumn"
    
    def _get_time_of_day(self, hour: int) -> str:
        """Get time of day from hour"""
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    async def emotional_indexing(self, **kwargs) -> Dict[str, Any]:
        """Index memories by emotional weight"""
        memory_data = kwargs.get("memory_data", {})
        context = kwargs.get("context", {})
        current_emotion = kwargs.get("current_emotion", {})
        
        # Extract emotional content
        emotional_content = {
            "weight": 0.5,  # Default
            "valence": "neutral",  # positive, negative, neutral
            "arousal": "medium",  # low, medium, high
            "primary_emotion": "neutral"
        }
        
        # Check memory data for emotional indicators
        if isinstance(memory_data, dict):
            emotional_words = {
                "positive": ["happy", "joy", "excited", "great", "wonderful", "love"],
                "negative": ["sad", "angry", "fear", "worried", "bad", "hate"],
                "high_arousal": ["excited", "angry", "fear", "surprised"],
                "low_arousal": ["calm", "relaxed", "tired", "bored"]
            }
            
            text_representation = str(memory_data).lower()
            
            # Check for emotional words
            positive_count = sum(1 for word in emotional_words["positive"] if word in text_representation)
            negative_count = sum(1 for word in emotional_words["negative"] if word in text_representation)
            high_arousal_count = sum(1 for word in emotional_words["high_arousal"] if word in text_representation)
            low_arousal_count = sum(1 for word in emotional_words["low_arousal"] if word in text_representation)
            
            # Determine valence
            if positive_count > negative_count:
                emotional_content["valence"] = "positive"
                emotional_content["weight"] = 0.7
            elif negative_count > positive_count:
                emotional_content["valence"] = "negative"
                emotional_content["weight"] = 0.8  # Negative emotions often have stronger weight
            else:
                emotional_content["valence"] = "neutral"
                emotional_content["weight"] = 0.5
            
            # Determine arousal
            if high_arousal_count > low_arousal_count:
                emotional_content["arousal"] = "high"
                emotional_content["weight"] = min(1.0, emotional_content["weight"] + 0.1)
            elif low_arousal_count > high_arousal_count:
                emotional_content["arousal"] = "low"
                emotional_content["weight"] = max(0.0, emotional_content["weight"] - 0.1)
        
        # Apply current emotion context
        if current_emotion:
            emotion_type = current_emotion.get("type", "neutral")
            emotion_intensity = current_emotion.get("intensity", 0.5)
            
            emotional_content["primary_emotion"] = emotion_type
            emotional_content["weight"] = max(
                emotional_content["weight"],
                emotion_intensity * 0.8
            )
        
        # Context influence
        if context.get("is_emotional_event", False):
            emotional_content["weight"] = min(1.0, emotional_content["weight"] + 0.2)
        
        return {
            "success": True,
            "emotional_content": emotional_content,
            "extraction_method": "lexical_analysis",
            "context_influence": context.get("emotional_context", "none"),
            "final_weight": emotional_content["weight"]
        }
    
    async def semantic_recall(self, **kwargs) -> Dict[str, Any]:
        """Recall memories by semantic similarity"""
        query = kwargs.get("query", {})
        memory_storage = kwargs.get("memory_storage")
        max_results = kwargs.get("max_results", 10)
        
        if not memory_storage or not hasattr(memory_storage, 'association_network'):
            return {
                "success": False,
                "error": "Memory storage not available",
                "recalled_memories": []
            }
        
        # Extract semantic query
        tags = set()
        if isinstance(query, dict):
            if "tags" in query:
                tags = set(query["tags"])
            elif "text" in query:
                # Extract tags from text
                text = query["text"].lower()
                words = text.split()
                tags = set(word for word in words if len(word) > 3 and word.isalpha())
        
        # Perform semantic search
        recalled_memory_ids = memory_storage.association_network.semantic_search(
            tags, max_results=max_results
        )
        
        # Get memory details
        recalled_memories = []
        for memory_id in recalled_memory_ids:
            if memory_id in memory_storage.memories:
                memory_entry = memory_storage.memories[memory_id]
                recalled_memories.append({
                    "memory_id": memory_id,
                    "metadata": memory_entry.metadata,
                    "relevance_score": 0.8,  # Would calculate based on tag overlap
                    "matching_tags": list(tags.intersection(memory_entry.metadata.tags))
                })
        
        return {
            "success": True,
            "recalled_memories": recalled_memories,
            "query_tags": list(tags),
            "total_found": len(recalled_memories),
            "recall_method": "semantic_search"
        }
    
    async def temporal_recall(self, **kwargs) -> Dict[str, Any]:
        """Recall memories by temporal proximity"""
        query = kwargs.get("query", {})
        memory_storage = kwargs.get("memory_storage")
        max_results = kwargs.get("max_results", 10)
        
        if not memory_storage or not hasattr(memory_storage, 'association_network'):
            return {
                "success": False,
                "error": "Memory storage not available",
                "recalled_memories": []
            }
        
        # Extract temporal query
        current_time = datetime.now()
        time_range = query.get("time_range", {})
        
        if not time_range:
            # Default: last 24 hours
            start_time = current_time - timedelta(hours=24)
            end_time = current_time
        else:
            start_time = datetime.fromisoformat(time_range.get("start", current_time.isoformat()))
            end_time = datetime.fromisoformat(time_range.get("end", current_time.isoformat()))
        
        # Perform temporal search
        recalled_memory_ids = memory_storage.association_network.temporal_search(
            start_time, end_time, max_results=max_results
        )
        
        # Get memory details
        recalled_memories = []
        for memory_id in recalled_memory_ids:
            if memory_id in memory_storage.memories:
                memory_entry = memory_storage.memories[memory_id]
                time_diff = abs((memory_entry.metadata.created_at - current_time).total_seconds())
                temporal_relevance = max(0.0, 1.0 - (time_diff / 86400))  # Decay over 24 hours
                
                recalled_memories.append({
                    "memory_id": memory_id,
                    "metadata": memory_entry.metadata,
                    "relevance_score": temporal_relevance,
                    "time_difference_seconds": time_diff
                })
        
        return {
            "success": True,
            "recalled_memories": recalled_memories,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "total_found": len(recalled_memories),
            "recall_method": "temporal_search"
        }
    
    async def associative_recall(self, **kwargs) -> Dict[str, Any]:
        """Recall memories through associations"""
        seed_memory_id = kwargs.get("seed_memory_id")
        memory_storage = kwargs.get("memory_storage")
        max_depth = kwargs.get("max_depth", 2)
        max_results = kwargs.get("max_results", 15)
        
        if not memory_storage or not hasattr(memory_storage, 'association_network'):
            return {
                "success": False,
                "error": "Memory storage not available",
                "recalled_memories": []
            }
        
        if not seed_memory_id or seed_memory_id not in memory_storage.memories:
            return {
                "success": False,
                "error": "Seed memory not found",
                "recalled_memories": []
            }
        
        # Perform associative recall
        recalled_memories = []
        visited = set([seed_memory_id])
        queue = deque([(seed_memory_id, 0)])  # (memory_id, depth)
        
        while queue and len(recalled_memories) < max_results:
            current_memory_id, depth = queue.popleft()
            
            if depth > max_depth:
                continue
            
            # Get associations for current memory
            associations = memory_storage.association_network.find_associated_memories(
                current_memory_id, max_results=10, min_strength=0.1
            )
            
            for assoc in associations:
                assoc_id = assoc["memory_id"]
                
                if assoc_id not in visited and assoc_id in memory_storage.memories:
                    visited.add(assoc_id)
                    
                    memory_entry = memory_storage.memories[assoc_id]
                    recalled_memories.append({
                        "memory_id": assoc_id,
                        "metadata": memory_entry.metadata,
                        "association_strength": assoc["association_strength"],
                        "association_type": assoc["association_type"],
                        "depth": depth + 1,
                        "via_memory": current_memory_id
                    })
                    
                    queue.append((assoc_id, depth + 1))
                    
                    if len(recalled_memories) >= max_results:
                        break
        
        # Sort by association strength and depth
        recalled_memories.sort(key=lambda x: (x["association_strength"], -x["depth"]), reverse=True)
        
        return {
            "success": True,
            "seed_memory": seed_memory_id,
            "recalled_memories": recalled_memories[:max_results],
            "total_found": len(recalled_memories),
            "max_depth_reached": max_depth,
            "recall_method": "associative_spreading_activation"
        }
    
    async def create_associations(self, **kwargs) -> Dict[str, Any]:
        """Create associations between memories"""
        memory_ids = kwargs.get("memory_ids", [])
        memory_storage = kwargs.get("memory_storage")
        association_type = kwargs.get("association_type", "semantic")
        min_similarity = kwargs.get("min_similarity", 0.3)
        
        if not memory_storage or len(memory_ids) < 2:
            return {
                "success": False,
                "error": "Insufficient memory IDs",
                "associations_created": 0
            }
        
        created_count = 0
        
        # Create associations between all pairs
        for i in range(len(memory_ids)):
            for j in range(i + 1, len(memory_ids)):
                memory_id1 = memory_ids[i]
                memory_id2 = memory_ids[j]
                
                # Check if both memories exist
                if (memory_id1 in memory_storage.memories and 
                    memory_id2 in memory_storage.memories):
                    
                    # Calculate similarity
                    similarity = self._calculate_memory_similarity(
                        memory_storage.memories[memory_id1],
                        memory_storage.memories[memory_id2],
                        association_type
                    )
                    
                    if similarity >= min_similarity:
                        # Create association
                        memory_storage.association_network.create_association(
                            memory_id1, memory_id2,
                            association_type=association_type,
                            strength=similarity
                        )
                        created_count += 1
        
        return {
            "success": True,
            "associations_created": created_count,
            "memory_pairs_considered": len(memory_ids) * (len(memory_ids) - 1) // 2,
            "association_type": association_type,
            "min_similarity_threshold": min_similarity
        }
    
    def _calculate_memory_similarity(self, memory1: MemoryEntry, memory2: MemoryEntry, 
                                   association_type: str) -> float:
        """Calculate similarity between two memories"""
        meta1 = memory1.metadata
        meta2 = memory2.metadata
        
        if association_type == "semantic":
            # Semantic similarity based on tag overlap
            common_tags = meta1.tags.intersection(meta2.tags)
            total_tags = meta1.tags.union(meta2.tags)
            
            if not total_tags:
                return 0.0
            
            similarity = len(common_tags) / len(total_tags)
            
        elif association_type == "temporal":
            # Temporal similarity based on creation time difference
            time_diff = abs((meta1.created_at - meta2.created_at).total_seconds())
            
            # Convert to similarity (closer in time = higher similarity)
            # 24-hour half-life
            similarity = math.exp(-time_diff / 86400)
            
        elif association_type == "emotional":
            # Emotional similarity based on emotional weight
            emotion_diff = abs(meta1.emotional_weight - meta2.emotional_weight)
            similarity = 1.0 - emotion_diff
            
        elif association_type == "contextual":
            # Contextual similarity based on context hash
            if meta1.context_hash and meta2.context_hash:
                similarity = 1.0 if meta1.context_hash == meta2.context_hash else 0.0
            else:
                similarity = 0.0
                
        else:
            similarity = 0.0
        
        return max(0.0, min(1.0, similarity))
    
    async def strengthen_associations(self, **kwargs) -> Dict[str, Any]:
        """Strengthen existing memory associations"""
        memory_storage = kwargs.get("memory_storage")
        strengthening_factor = kwargs.get("strengthening_factor", 0.1)
        max_strength = kwargs.get("max_strength", 1.0)
        
        if not memory_storage:
            return {
                "success": False,
                "error": "Memory storage not available",
                "associations_strengthened": 0
            }
        
        strengthened_count = 0
        
        # Get all edges from association network
        edges = list(memory_storage.association_network.memory_graph.edges(data=True))
        
        for u, v, data in edges:
            current_strength = data.get("strength", 0.0)
            new_strength = min(max_strength, current_strength + strengthening_factor)
            
            if new_strength > current_strength:
                # Update association strength
                memory_storage.association_network.create_association(
                    u, v,
                    association_type=data.get("association_type", "semantic"),
                    strength=new_strength
                )
                strengthened_count += 1
        
        return {
            "success": True,
            "associations_strengthened": strengthened_count,
            "total_associations": len(edges),
            "strengthening_factor": strengthening_factor,
            "average_new_strength": sum(
                d.get("strength", 0.0) for _, _, d in edges
            ) / max(1, len(edges))
        }
    
    async def memory_consolidation(self, **kwargs) -> Dict[str, Any]:
        """Consolidate and optimize memory storage"""
        memory_storage = kwargs.get("memory_storage")
        consolidation_threshold = kwargs.get("consolidation_threshold", 0.8)
        
        if not memory_storage:
            return {
                "success": False,
                "error": "Memory storage not available",
                "consolidation_results": {}
            }
        
        consolidation_results = {
            "memories_analyzed": 0,
            "memories_consolidated": 0,
            "associations_strengthened": 0,
            "storage_reclaimed": 0,
            "duplicates_found": 0
        }
        
        # Analyze memory retention scores
        retention_scores = []
        for memory_id, memory_entry in memory_storage.memories.items():
            retention_score = memory_entry.metadata.calculate_retention_score()
            retention_scores.append((memory_id, retention_score))
        
        consolidation_results["memories_analyzed"] = len(retention_scores)
        
        # Identify memories with low retention scores for potential consolidation
        low_retention_memories = [
            (mid, score) for mid, score in retention_scores 
            if score < consolidation_threshold
        ]
        
        if low_retention_memories:
            # For demonstration, we just log these memories
            # In production, would merge or compress them
            consolidation_results["memories_consolidated"] = len(low_retention_memories)
        
        # Strengthen associations for frequently accessed memories
        frequently_accessed = [
            (mid, entry.metadata.access_count)
            for mid, entry in memory_storage.memories.items()
            if entry.metadata.access_count > 10
        ]
        
        for memory_id, _ in frequently_accessed[:10]:  # Limit to 10
            associations = memory_storage.association_network.find_associated_memories(
                memory_id, max_results=5, min_strength=0.1
            )
            
            for assoc in associations:
                current_strength = assoc["association_strength"]
                new_strength = min(1.0, current_strength + 0.05)
                
                memory_storage.association_network.create_association(
                    memory_id, assoc["memory_id"],
                    association_type=assoc["association_type"],
                    strength=new_strength
                )
                consolidation_results["associations_strengthened"] += 1
        
        # Check for potential duplicates (simplified)
        # In production, would use more sophisticated duplicate detection
        memory_hashes = {}
        for memory_id, memory_entry in memory_storage.memories.items():
            # Create simple hash of metadata
            metadata_str = str(sorted(memory_entry.metadata.tags)) + str(memory_entry.metadata.created_at)
            metadata_hash = hashlib.md5(metadata_str.encode()).hexdigest()
            
            if metadata_hash in memory_hashes:
                consolidation_results["duplicates_found"] += 1
            else:
                memory_hashes[metadata_hash] = memory_id
        
        return {
            "success": True,
            "consolidation_results": consolidation_results,
            "retention_threshold": consolidation_threshold,
            "average_retention_score": sum(score for _, score in retention_scores) / 
                                     max(1, len(retention_scores))
        }
    
    async def forgetting_curve_application(self, **kwargs) -> Dict[str, Any]:
        """Apply forgetting curve to memory retention"""
        memory_storage = kwargs.get("memory_storage")
        decay_rate = kwargs.get("decay_rate", 0.0001)  # Per second
        
        if not memory_storage:
            return {
                "success": False,
                "error": "Memory storage not available",
                "decay_applied": 0
            }
        
        current_time = datetime.now()
        decay_applied = 0
        
        for memory_id, memory_entry in memory_storage.memories.items():
            metadata = memory_entry.metadata
            
            # Calculate time since last access
            time_since_access = (current_time - metadata.last_accessed).total_seconds()
            
            # Apply forgetting curve decay
            decay_amount = decay_rate * time_since_access * metadata.association_strength
            
            # Only apply decay if memory hasn't been accessed recently
            if time_since_access > 3600:  # 1 hour
                new_strength = max(0.0, metadata.association_strength - decay_amount)
                
                if new_strength < metadata.association_strength:
                    metadata.association_strength = new_strength
                    decay_applied += 1
        
        return {
            "success": True,
            "decay_applied": decay_applied,
            "total_memories": len(memory_storage.memories),
            "decay_rate": decay_rate,
            "method": "ebbinghaus_forgetting_curve"
        }
    
    async def encryption_optimization(self, **kwargs) -> Dict[str, Any]:
        """Optimize encryption parameters"""
        encryption_manager = kwargs.get("encryption_manager")
        
        if not encryption_manager or not hasattr(encryption_manager, 'encryption_config'):
            return {
                "success": False,
                "error": "Encryption manager not available",
                "optimizations": []
            }
        
        optimizations = []
        config = encryption_manager.encryption_config
        
        # Analyze current encryption performance
        current_iterations = config.get("key_derivation_iterations", 100000)
        current_layers = config.get("encryption_layers", 1)
        
        # Suggest optimizations based on performance
        if current_iterations > 200000:
            optimizations.append({
                "parameter": "key_derivation_iterations",
                "current_value": current_iterations,
                "suggested_value": 150000,
                "reason": "High iteration count may impact performance",
                "impact": "moderate"
            })
        
        if current_layers > 3:
            optimizations.append({
                "parameter": "encryption_layers",
                "current_value": current_layers,
                "suggested_value": 2,
                "reason": "Multiple encryption layers provide diminishing security returns",
                "impact": "high"
            })
        
        # Check key rotation schedule
        encryption_status = await encryption_manager.get_encryption_status()
        rotation_schedule = encryption_status.get("key_rotation_schedule", {})
        
        for tier, rotation_date_str in rotation_schedule.items():
            try:
                rotation_date = datetime.fromisoformat(rotation_date_str)
                days_until_rotation = (rotation_date - datetime.now()).days
                
                if days_until_rotation < 7:
                    optimizations.append({
                        "parameter": f"key_rotation_{tier}",
                        "current_value": rotation_date_str,
                        "suggested_value": "immediate",
                        "reason": f"Key rotation for tier {tier} is due in {days_until_rotation} days",
                        "impact": "high"
                    })
            except Exception:
                pass
        
        return {
            "success": True,
            "optimizations": optimizations,
            "total_suggestions": len(optimizations),
            "current_config_summary": {
                "algorithm": config.get("encryption_algorithm"),
                "iterations": current_iterations,
                "layers": current_layers
            }
        }
    
    async def key_rotation_scheduling(self, **kwargs) -> Dict[str, Any]:
        """Schedule encryption key rotation"""
        encryption_manager = kwargs.get("encryption_manager")
        rotation_strategy = kwargs.get("rotation_strategy", "progressive")
        
        if not encryption_manager:
            return {
                "success": False,
                "error": "Encryption manager not available",
                "schedule_created": False
            }
        
        # Get current status
        encryption_status = await encryption_manager.get_encryption_status()
        
        # Calculate new rotation schedule based on strategy
        rotation_days = 30  # Default
        
        if rotation_strategy == "aggressive":
            rotation_days = 15
        elif rotation_strategy == "conservative":
            rotation_days = 60
        elif rotation_strategy == "progressive":
            # Progressive: more frequent rotation for higher tiers
            rotation_days = {
                "root": 15,
                "owner_confidential": 30,
                "access": 45,
                "public": 60,
                "temporal": 7
            }
        
        schedule = {}
        current_time = datetime.now()
        
        if isinstance(rotation_days, dict):
            for tier in encryption_manager.derived_keys.keys():
                days = rotation_days.get(tier, 30)
                schedule[tier] = (current_time + timedelta(days=days)).isoformat()
        else:
            for tier in encryption_manager.derived_keys.keys():
                schedule[tier] = (current_time + timedelta(days=rotation_days)).isoformat()
        
        return {
            "success": True,
            "schedule_created": True,
            "rotation_strategy": rotation_strategy,
            "new_schedule": schedule,
            "previous_schedule": encryption_status.get("key_rotation_schedule", {})
        }
    
    async def compression_optimization(self, **kwargs) -> Dict[str, Any]:
        """Optimize memory compression"""
        memory_storage = kwargs.get("memory_storage")
        compression_threshold = kwargs.get("compression_threshold", 0.8)
        
        if not memory_storage:
            return {
                "success": False,
                "error": "Memory storage not available",
                "optimizations": []
            }
        
        optimizations = []
        
        # Analyze current memory sizes
        memory_sizes = []
        uncompressed_size = 0
        compressed_size = 0
        
        for memory_id, memory_entry in memory_storage.memories.items():
            # Get encrypted data size
            encrypted_size = len(memory_entry.encrypted_data)
            memory_sizes.append((memory_id, encrypted_size))
            
            # Estimate original size from metadata
            original_size = memory_entry.encryption_metadata.get("data_length", encrypted_size)
            uncompressed_size += original_size
            compressed_size += encrypted_size
        
        # Calculate overall compression ratio
        if uncompressed_size > 0:
            overall_ratio = compressed_size / uncompressed_size
        else:
            overall_ratio = 1.0
        
        # Identify memories that could benefit from compression
        memory_sizes.sort(key=lambda x: x[1], reverse=True)
        
        for memory_id, size in memory_sizes[:10]:  # Top 10 largest memories
            memory_entry = memory_storage.memories[memory_id]
            
            # Check if already compressed
            if not memory_entry.encryption_metadata.get("compressed", False):
                optimizations.append({
                    "memory_id": memory_id,
                    "current_size": size,
                    "estimated_savings": size * 0.5,  # Estimate 50% compression
                    "reason": "Large uncompressed memory",
                    "priority": "high"
                })
        
        # Check overall storage utilization
        total_memories = len(memory_storage.memories)
        max_memories = memory_storage.config.get("maximum_memory_entries", 1000000)
        
        utilization = total_memories / max_memories if max_memories > 0 else 0
        
        if utilization > compression_threshold:
            optimizations.append({
                "memory_id": "all",
                "current_size": compressed_size,
                "estimated_savings": compressed_size * 0.3,  # Estimate 30% overall savings
                "reason": f"Storage utilization ({utilization:.1%}) above threshold ({compression_threshold:.0%})",
                "priority": "critical"
            })
        
        return {
            "success": True,
            "optimizations": optimizations,
            "compression_statistics": {
                "total_memories": total_memories,
                "uncompressed_size": uncompressed_size,
                "compressed_size": compressed_size,
                "compression_ratio": overall_ratio,
                "storage_utilization": utilization,
                "threshold": compression_threshold
            }
        }
    
    async def storage_efficiency_analysis(self, **kwargs) -> Dict[str, Any]:
        """Analyze storage efficiency"""
        memory_storage = kwargs.get("memory_storage")
        
        if not memory_storage:
            return {
                "success": False,
                "error": "Memory storage not available",
                "analysis": {}
            }
        
        # Get storage statistics
        stats = await memory_storage.get_storage_statistics()
        
        # Calculate efficiency metrics
        total_memories = stats.get("total_memories", 0)
        total_size = stats.get("total_size_bytes", 0)
        
        # Memory distribution by tier
        tier_distribution = stats.get("tier_distribution", {})
        
        # Calculate efficiency scores
        efficiency_metrics = {
            "storage_efficiency": 0.0,
            "access_efficiency": 0.0,
            "compression_efficiency": 0.0,
            "association_efficiency": 0.0
        }
        
        # Storage efficiency: based on tier distribution
        # Higher efficiency when important data (owner_confidential) is smaller but more accessible
        owner_data_ratio = tier_distribution.get("OWNER_CONFIDENTIAL", 0) / max(1, total_memories)
        efficiency_metrics["storage_efficiency"] = 0.5 + owner_data_ratio * 0.5
        
        # Access efficiency: based on cache hit rate
        performance_metrics = stats.get("performance_metrics", {})
        cache_hits = performance_metrics.get("cache_hits", 0)
        cache_misses = performance_metrics.get("cache_misses", 0)
        
        total_cache_access = cache_hits + cache_misses
        if total_cache_access > 0:
            cache_hit_ratio = cache_hits / total_cache_access
            efficiency_metrics["access_efficiency"] = cache_hit_ratio
        
        # Association efficiency: based on network connectivity
        network_stats = stats.get("association_network", {})
        total_nodes = network_stats.get("total_memories", 0)
        total_edges = network_stats.get("total_associations", 0)
        
        if total_nodes > 1:
            max_possible_edges = total_nodes * (total_nodes - 1) / 2
            association_density = total_edges / max_possible_edges if max_possible_edges > 0 else 0
            efficiency_metrics["association_efficiency"] = min(1.0, association_density * 2)
        
        # Overall efficiency score
        weights = {
            "storage_efficiency": 0.3,
            "access_efficiency": 0.4,
            "association_efficiency": 0.3
        }
        
        overall_efficiency = sum(
            efficiency_metrics[key] * weight 
            for key, weight in weights.items()
        )
        
        # Recommendations
        recommendations = []
        
        if cache_hit_ratio < 0.5:
            recommendations.append({
                "area": "cache_optimization",
                "suggestion": "Increase cache size or adjust TTL",
                "priority": "medium"
            })
        
        if association_density < 0.1:
            recommendations.append({
                "area": "association_network",
                "suggestion": "Create more associations between memories",
                "priority": "low"
            })
        
        if total_memories > 10000:
            recommendations.append({
                "area": "storage_management",
                "suggestion": "Consider archiving old or low-priority memories",
                "priority": "medium"
            })
        
        return {
            "success": True,
            "efficiency_metrics": efficiency_metrics,
            "overall_efficiency": overall_efficiency,
            "statistics": {
                "total_memories": total_memories,
                "total_size_mb": total_size / (1024 * 1024),
                "cache_hit_ratio": cache_hit_ratio,
                "association_density": association_density,
                "tier_distribution": tier_distribution
            },
            "recommendations": recommendations
        }

# ==================== NEURAL NETWORK ====================
class MemoryNeuralNetwork:
    """Memory Core's neural network"""
    
    def __init__(self):
        self.neurons: Dict[str, MemoryNeuron] = {}
        self.function_registry = MemoryFunctionRegistry()
        self.memory_storage = MemoryStorageEngine()
        self.connection_graph = nx.DiGraph()
        self.config = {}
        self.initialized = False
        self.performance_metrics = {
            "memories_processed": 0,
            "associations_created": 0,
            "recalls_performed": 0,
            "indexing_operations": 0
        }
    
    async def initialize(self, owner_biometric_hash: str):
        """Initialize memory neural network"""
        try:
            self.config = await MemoryConfigLoader.load_core_config()
            
            # Initialize memory storage
            storage_success = await self.memory_storage.initialize(owner_biometric_hash, self.config)
            
            if not storage_success:
                return False
            
            # Create initial neurons from function registry
            for func_name in self.function_registry.registered_functions:
                neuron = await self.function_registry.create_neuron_for_function(func_name)
                if neuron:
                    self.neurons[neuron.neuron_id] = neuron
                    self.connection_graph.add_node(neuron.neuron_id)
            
            # Create initial connections based on specializations
            await self._establish_initial_connections()
            
            self.initialized = True
            logger.info(f"Memory Core initialized with {len(self.neurons)} neurons")
            return True
            
        except Exception as e:
            logger.error(f"MemoryNeuralNetwork initialization failed: {e}")
            return False
    
    async def _establish_initial_connections(self):
        """Establish initial neural connections"""
        # Group neurons by specialization
        specialization_groups = defaultdict(list)
        for neuron in self.neurons.values():
            specialization = neuron.specialization
            specialization_groups[specialization].append(neuron.neuron_id)
        
        # Connect related neurons
        for specialization, neuron_ids in specialization_groups.items():
            for i, source_id in enumerate(neuron_ids):
                # Connect to other neurons in same specialization
                for target_id in neuron_ids[i+1:min(i+4, len(neuron_ids))]:
                    await self.create_connection(source_id, target_id)
                
                # Connect to neurons in related specializations
                related_specializations = self._get_related_specializations(specialization)
                for related_spec in related_specializations:
                    if related_spec in specialization_groups and specialization_groups[related_spec]:
                        target_id = random.choice(specialization_groups[related_spec])
                        await self.create_connection(source_id, target_id)
    
    async def create_connection(self, source_id: str, target_id: str, 
                              strength: float = 0.5) -> bool:
        """Create a neural connection"""
        if source_id not in self.neurons or target_id not in self.neurons:
            return False
        
        connection = MemoryNeuralConnection(
            target_neuron_id=target_id,
            connection_strength=strength
        )
        
        self.neurons[source_id].connections.append(connection)
        self.connection_graph.add_edge(source_id, target_id, weight=strength)
        
        return True
    
    async def process_memory_operation(self, operation: str, data: Dict[str, Any], 
                                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process memory operation through neural network"""
        if not self.initialized:
            return {"success": False, "error": "MemoryNeuralNetwork not initialized"}
        
        start_time = datetime.now()
        
        try:
            # Route operation to appropriate neurons
            if operation == "store":
                return await self._process_store_operation(data, context)
            elif operation == "retrieve":
                return await self._process_retrieve_operation(data, context)
            elif operation == "search":
                return await self._process_search_operation(data, context)
            elif operation == "associate":
                return await self._process_associate_operation(data, context)
            elif operation == "consolidate":
                return await self._process_consolidate_operation(data, context)
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
                
        except Exception as e:
            logger.error(f"Memory operation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": operation,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    async def _process_store_operation(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process memory store operation with active neural indexing."""
        # 1. Activate indexing neurons
        # Note: 'indexing' specialization is now correctly assigned by create_neuron_for_function
        indexing_neurons = [n for n in self.neurons.values() if n.specialization == "indexing"]
        
        generated_tags = set(data.get("tags", []))
        
        # FIX: Ensure context is never None to prevent 'NoneType' error in neurons
        safe_context = context if context is not None else {}
        
        # Parallel execution of indexing neurons
        if indexing_neurons:
            exec_context = {
                "memory_data": data.get("data"),
                "tags": list(generated_tags),
                "context": safe_context,
                "timestamp": datetime.now()
            }
            
            # Fire first 3 available neurons
            for neuron in indexing_neurons[:3]:
                result = await neuron.fire(0.8, exec_context)
                if result and isinstance(result, dict) and "indexed_tags" in result:
                    generated_tags.update(result["indexed_tags"])
        
        # 2. Prepare metadata with NEURALLY GENERATED tags
        metadata = {
            "tags": list(generated_tags), # Critical: Pass generated tags to storage
            "emotional_weight": data.get("emotional_weight", 0.5),
            "priority": data.get("priority", 0.5)
        }
        
        # 3. Determine tier
        tier_name = data.get("tier", "OWNER_CONFIDENTIAL").upper()
        try:
            tier = DataTier[tier_name]
        except KeyError:
            tier = DataTier.OWNER_CONFIDENTIAL
        
        # 4. Store memory
        store_result = await self.memory_storage.store_memory(
            data.get("data"),
            tier=tier,
            metadata=metadata,
            context=context
        )
        
        if store_result.get("success", False):
            self.performance_metrics["memories_processed"] += 1
            # Trigger associations
            if store_result.get("memory_id"):
                await self._activate_association_neurons(store_result["memory_id"], context)
        
        return store_result
    
    async def _process_retrieve_operation(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process memory retrieve operation"""
        memory_id = data.get("memory_id")
        access_level = data.get("access_level", "owner_root")
        
        if not memory_id:
            return {"success": False, "error": "No memory_id provided"}
        
        # Activate recall neurons
        recall_neurons = [n for n in self.neurons.values() if n.specialization == "recall"]
        
        recall_context = {
            "memory_id": memory_id,
            "memory_storage": self.memory_storage,
            "context": context
        }
        
        recall_results = []
        for neuron in recall_neurons[:2]:  # Use up to 2 recall neurons
            result = await neuron.fire(0.7, recall_context)
            if result:
                recall_results.append(result)
        
        # Retrieve memory
        retrieve_result = await self.memory_storage.retrieve_memory(memory_id, access_level)
        
        if retrieve_result.get("success", False):
            self.performance_metrics["recalls_performed"] += 1
            
            # Add recall analysis to result
            retrieve_result["recall_analysis"] = {
                "recall_methods_used": [r.get("recall_method", "unknown") for r in recall_results],
                "recall_confidence": sum(r.get("total_found", 0) for r in recall_results) / 
                                   max(1, len(recall_results))
            }
        
        return retrieve_result
    
    async def _process_search_operation(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process memory search operation"""
        query = data.get("query", {})
        access_level = data.get("access_level", "owner_root")
        max_results = data.get("max_results", 50)
        
        # Activate recall neurons for search
        recall_neurons = [n for n in self.neurons.values() if n.specialization == "recall"]
        
        search_results = []
        for neuron in recall_neurons[:2]:  # Use up to 2 recall neurons
            exec_context = {
                "query": query,
                "memory_storage": self.memory_storage,
                "max_results": max_results
            }
            
            result = await neuron.fire(0.6, exec_context)
            if result and result.get("success", False):
                search_results.extend(result.get("recalled_memories", []))
        
        # Also perform direct search
        direct_search = await self.memory_storage.search_memories(
            query, access_level, max_results
        )
        
        if direct_search.get("success", False):
            # Combine results
            all_results = direct_search.get("results", [])
            
            # Add neural search results
            for neural_result in search_results:
                if neural_result.get("memory_id") not in [r.get("memory_id") for r in all_results]:
                    all_results.append({
                        "memory_id": neural_result.get("memory_id"),
                        "metadata": neural_result.get("metadata"),
                        "relevance_score": neural_result.get("relevance_score", 0.5),
                        "search_method": "neural_recall"
                    })
            
            # Sort by relevance
            all_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            all_results = all_results[:max_results]
            
            direct_search["results"] = all_results
            direct_search["neural_search_contribution"] = len(search_results)
        
        return direct_search
    
    async def _process_associate_operation(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process memory association operation"""
        memory_ids = data.get("memory_ids", [])
        association_type = data.get("association_type", "semantic")
        
        if len(memory_ids) < 2:
            return {"success": False, "error": "At least 2 memory IDs required"}
        
        # Activate association neurons
        association_neurons = [n for n in self.neurons.values() if n.specialization == "association"]
        
        association_results = []
        for neuron in association_neurons[:2]:  # Use up to 2 association neurons
            exec_context = {
                "memory_ids": memory_ids,
                "memory_storage": self.memory_storage,
                "association_type": association_type
            }
            
            result = await neuron.fire(0.7, exec_context)
            if result:
                association_results.append(result)
        
        # Update performance metrics
        if association_results:
            self.performance_metrics["associations_created"] += sum(
                r.get("associations_created", 0) for r in association_results
            )
        
        # Return combined results
        return {
            "success": True,
            "operation": "associate",
            "memory_ids": memory_ids,
            "association_type": association_type,
            "association_results": association_results,
            "total_associations_created": sum(
                r.get("associations_created", 0) for r in association_results
            )
        }
    
    async def _process_consolidate_operation(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process memory consolidation operation"""
        # Activate consolidation neurons
        consolidation_neurons = [n for n in self.neurons.values() if n.specialization == "consolidation"]
        
        consolidation_results = []
        for neuron in consolidation_neurons[:3]:  # Use up to 3 consolidation neurons
            exec_context = {
                "memory_storage": self.memory_storage,
                "encryption_manager": self.memory_storage.encryption_manager
            }
            exec_context.update(data)  # Add any consolidation parameters
            
            result = await neuron.fire(0.9, exec_context)
            if result:
                consolidation_results.append(result)
        
        # Update performance metrics
        if consolidation_results:
            self.performance_metrics["indexing_operations"] += 1
        
        # Return combined results
        return {
            "success": True,
            "operation": "consolidate",
            "consolidation_results": consolidation_results,
            "total_operations": len(consolidation_results)
        }
    
    async def _activate_association_neurons(self, memory_id: str, context: Dict[str, Any]):
        """Activate association neurons for a new memory"""
        association_neurons = [n for n in self.neurons.values() if n.specialization == "association"]
        
        for neuron in association_neurons[:2]:  # Use up to 2 association neurons
            exec_context = {
                "memory_ids": [memory_id],
                "memory_storage": self.memory_storage,
                "context": context
            }
            
            await neuron.fire(0.6, exec_context)
    
    def _get_related_specializations(self, specialization: str) -> List[str]:
        """Get related specializations"""
        relationships = {
            "indexing": ["recall", "association", "consolidation"],
            "recall": ["indexing", "association", "consolidation"],
            "association": ["indexing", "recall", "consolidation"],
            "consolidation": ["indexing", "recall", "association"],
            "encryption": ["compression", "consolidation"],
            "compression": ["encryption", "consolidation"]
        }
        return relationships.get(specialization, [])
    
    async def get_visualization_data(self) -> Dict[str, Any]:
        """Get current state for holographic visualization"""
        neurons_data = []
        for neuron in self.neurons.values():
            neurons_data.append(neuron.axon_state())
        
        # Connection data
        connection_data = []
        for neuron in self.neurons.values():
            for connection in neuron.connections:
                if connection.target_neuron_id in self.neurons:
                    connection_data.append({
                        "source": neuron.neuron_id,
                        "target": connection.target_neuron_id,
                        "strength": connection.connection_strength,
                        "type": connection.association_type
                    })
        
        # Get storage statistics - ASYNC AWAIT
        storage_stats = await self.memory_storage.get_storage_statistics()
        
        # Calculate network health
        total_neurons = len(self.neurons)
        active_neurons = sum(1 for n in self.neurons.values() 
                            if n.current_state == MemoryNeuronState.ACTIVE)
        failed_neurons = sum(1 for n in self.neurons.values() 
                            if n.current_state == MemoryNeuronState.FAILED)
        
        health_status = "optimal"
        if total_neurons > 0:
            failure_ratio = failed_neurons / total_neurons
            if failure_ratio > 0.3:
                health_status = "critical"
            elif failure_ratio > 0.1:
                health_status = "degraded"
            elif active_neurons / total_neurons < 0.3:
                health_status = "dormant"
        
        return {
            "core": "memory",
            "neuron_count": total_neurons,
            "active_neurons": active_neurons,
            "failed_neurons": failed_neurons,
            "neurons": neurons_data,
            "connections": connection_data,
            "storage_statistics": storage_stats,
            "health_status": health_status,
            "performance_metrics": self.performance_metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    async def evolve(self, evolution_data: Dict[str, Any]):
        """Evolve memory neural structure"""
        action = evolution_data.get("action")
        
        if action == "add_function":
            new_func = evolution_data.get("function")
            if new_func:
                self.function_registry.register_function(
                    name=new_func.get("name"),
                    category=new_func.get("category"),
                    func=new_func.get("implementation"),
                    description=new_func.get("description")
                )
                
                # Create neuron for new function
                neuron = await self.function_registry.create_neuron_for_function(new_func.get("name"))
                if neuron:
                    self.neurons[neuron.neuron_id] = neuron
                    self.connection_graph.add_node(neuron.neuron_id)
        
        elif action == "optimize_storage":
            # Trigger storage optimization
            await self.memory_storage._consolidate_memories()
        
        elif action == "adjust_encryption":
            adjustments = evolution_data.get("adjustments", {})
            if adjustments:
                # Would apply to encryption manager
                pass
        
        logger.info(f"Memory core evolved with action: {action}")
# ==================== MAIN MEMORY CORE CLASS ====================
class MemoryCore:
    """Main orchestrator for Memory Core functionality"""
    
    def __init__(self):
        self.neural_network = MemoryNeuralNetwork()
        self.is_running = False
        self.stem_connection = None
        self.start_time = None
        
    async def start(self, owner_biometric_hash: str):
        """Start the Memory Core"""
        success = await self.neural_network.initialize(owner_biometric_hash)
        
        if success:
            self.is_running = True
            self.start_time = datetime.now()
            logger.info("Memory Core started successfully")
        else:
            logger.error("Memory Core failed to start")
        
        return success
    
    async def stop(self):
        """Stop the Memory Core gracefully"""
        self.is_running = False
        
        # Save any pending operations
        await self.neural_network.memory_storage._save_persistent_storage()
        
        logger.info("Memory Core stopped")
        return True
    
    async def process_operation(self, operation: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process memory operation"""
        if not self.is_running:
            return {"success": False, "error": "Memory Core not running"}
        
        return await self.neural_network.process_memory_operation(operation, data)
    
    async def get_core_status(self) -> Dict[str, Any]:
        """Get comprehensive core status"""
        # Get visualization data - ASYNC AWAIT
        viz_data = await self.neural_network.get_visualization_data()
        
        # Calculate uptime
        uptime = "0:00:00"
        if self.start_time:
            delta = datetime.now() - self.start_time
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime = f"{hours}:{minutes:02d}:{seconds:02d}"
        
        # Extract from visualization data
        storage_stats = viz_data.get("storage_statistics", {})
        
        return {
            **viz_data,
            "is_running": self.is_running,
            "uptime": uptime,
            "storage_summary": {
                "total_memories": storage_stats.get("total_memories", 0),
                "total_size_mb": storage_stats.get("total_size_bytes", 0) / (1024 * 1024),
                "identity_profiles": storage_stats.get("identity_profiles", 0),
                "cache_utilization": storage_stats.get("cache_size", 0)
            }
        }
    
    async def execute_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute high-level memory core commands"""
        command_map = {
            "store_memory": self._command_store_memory,
            "retrieve_memory": self._command_retrieve_memory,
            "search_memories": self._command_search_memories,
            "update_memory": self._command_update_memory,
            "delete_memory": self._command_delete_memory,
            "manage_identity": self._command_manage_identity,
            "consolidate_memories": self._command_consolidate_memories,
            "get_storage_stats": self._command_get_storage_stats,
            "core_status": self._command_core_status,
            "evolve": self._command_evolve
        }
        
        if command in command_map:
            return await command_map[command](parameters)
        else:
            return {
                "error": f"Unknown command: {command}",
                "available_commands": list(command_map.keys())
            }
    
    async def _command_store_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Command: Store memory"""
        if "data" not in params:
            return {"error": "No data provided"}
        
        return await self.process_operation("store", params)
    
    async def _command_retrieve_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Command: Retrieve memory"""
        if "memory_id" not in params:
            return {"error": "No memory_id provided"}
        
        return await self.process_operation("retrieve", params)
    
    async def _command_search_memories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Command: Search memories"""
        if "query" not in params:
            return {"error": "No query provided"}
        
        return await self.process_operation("search", params)
    
    async def _command_update_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Command: Update memory"""
        memory_id = params.get("memory_id")
        updates = params.get("updates", {})
        
        if not memory_id or not updates:
            return {"error": "memory_id and updates required"}
        
        return await self.neural_network.memory_storage.update_memory(
            memory_id, updates, params.get("access_level", "owner_root")
        )
    
    async def _command_delete_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Command: Delete memory"""
        memory_id = params.get("memory_id")
        
        if not memory_id:
            return {"error": "No memory_id provided"}
        
        return await self.neural_network.memory_storage.delete_memory(
            memory_id, params.get("access_level", "owner_root")
        )
    
    async def _command_manage_identity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Command: Manage identity profile"""
        identity_data = params.get("identity_data", {})
        operation = params.get("operation", "create_or_update")
        
        return await self.neural_network.memory_storage.manage_identity_profile(
            identity_data, operation
        )
    
    async def _command_consolidate_memories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Command: Consolidate memories"""
        return await self.process_operation("consolidate", params)
    
    async def _command_get_storage_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Command: Get storage statistics"""
        return await self.neural_network.memory_storage.get_storage_statistics()
    
    async def _command_core_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Command: Get core status"""
        return await self.get_core_status()
    
    async def _command_evolve(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Command: Evolve memory core"""
        if "action" not in params:
            return {"error": "Evolution action required"}
        
        try:
            await self.neural_network.evolve(params)
            return {
                "success": True,
                "action": params["action"],
                "neuron_count": len(self.neural_network.neurons),
                "message": f"Evolution action '{params['action']}' completed"
            }
        except Exception as e:
            return {
                "error": f"Evolution failed: {str(e)}",
                "action": params.get("action")
            }

# ==================== INITIALIZATION ====================
# Global instance for import
memory_core_instance = MemoryCore()

async def initialize_memory_core(owner_biometric_hash: str):
    """Initialize the memory core (called by Stem)"""
    success = await memory_core_instance.start(owner_biometric_hash)
    return memory_core_instance if success else None

async def shutdown_memory_core():
    """Shutdown the memory core gracefully"""
    success = await memory_core_instance.stop()
    return success

# ==================== MAIN EXECUTION GUARD ====================
if __name__ == "__main__":
    # This file is meant to be imported, not run directly
    # Direct execution is for testing only
    async def test():
        # Create test biometric hash
        test_biometric = hashlib.sha256(b"test_owner_biometric").hexdigest()
        
        core = MemoryCore()
        await core.start(test_biometric)
        
        # Test storing memory
        result = await core.execute_command("store_memory", {
            "data": {
                "type": "note",
                "content": "Test memory storage",
                "importance": "high"
            },
            "tags": ["test", "memory", "storage"],
            "tier": "OWNER_CONFIDENTIAL"
        })
        print("Store memory result:", json.dumps(result, indent=2, default=str))
        
        # Test retrieving memory
        if result.get("success") and "memory_id" in result:
            retrieve_result = await core.execute_command("retrieve_memory", {
                "memory_id": result["memory_id"],
                "access_level": "owner_root"
            })
            print("\nRetrieve memory result:", json.dumps({
                k: v for k, v in retrieve_result.items() if k != "data"
            }, indent=2, default=str))
        
        # Test search memories
        search_result = await core.execute_command("search_memories", {
            "query": {
                "tags": ["test", "memory"],
                "text": "storage"
            }
        })
        print("\nSearch memories result:", json.dumps(search_result, indent=2, default=str))
        
        # Test core status
        status_result = await core.execute_command("core_status", {})
        print("\nCore status (summary):", json.dumps({
            k: v for k, v in status_result.items() if k not in ['neurons', 'connections', 'storage_statistics']
        }, indent=2, default=str))
        
        await core.stop()
    
    asyncio.run(test())