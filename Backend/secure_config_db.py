# // SECURE_CONFIG_DB.PY
# // VERSION: 1.0.0
# // DESCRIPTION: Secure Configuration Database - Encrypted SQLite database for AARIA system configuration
# // UPDATE NOTES: Initial release. Implements AES-256 encrypted SQLite storage with biometric key derivation
# // IMPORTANT: No hardcoded values. All sensitive data encrypted at rest.

import sqlite3
import json
import hashlib
import os
import base64
from datetime import datetime
from typing import Dict, Any, Optional, List
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)

class SecureConfigDatabase:
    """
    Encrypted configuration database using SQLite with AES-256-GCM encryption.
    All sensitive configuration data is encrypted using owner's biometric-derived key.
    """
    
    def __init__(self, db_path: str = None):
        """Initialize secure configuration database"""
        if db_path is None:
            # Default to Backend directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, ".aaria_config.db")
        
        self.db_path = db_path
        self.connection = None
        self.master_key = None
        self.backend = default_backend()
        self.initialized = False
        
    async def initialize(self, biometric_hash: str) -> bool:
        """
        Initialize database with biometric-derived encryption key
        
        Args:
            biometric_hash: SHA-256 hash of owner's biometric data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Derive master encryption key from biometric hash
            self.master_key = await self._derive_master_key(biometric_hash)
            
            # Create database connection
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            
            # Create schema if not exists
            await self._create_schema()
            
            # Initialize with default values if empty
            await self._initialize_defaults()
            
            self.initialized = True
            logger.info(f"Secure configuration database initialized at {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize secure config database: {e}")
            return False
    
    async def _derive_master_key(self, biometric_hash: str) -> bytes:
        """Derive 256-bit master key from biometric hash using PBKDF2"""
        # Use fixed salt stored in environment or generate on first run
        salt_key = "AARIA_CONFIG_SALT"
        salt = os.getenv(salt_key)
        
        if not salt:
            # Generate new salt on first run
            salt = base64.urlsafe_b64encode(os.urandom(32)).decode()
            logger.warning(f"Generated new config salt. Set environment variable {salt_key}={salt}")
        else:
            # Decode existing salt
            salt = base64.urlsafe_b64decode(salt.encode())
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32,  # 256 bits for AES-256
            salt=salt if isinstance(salt, bytes) else salt.encode(),
            iterations=310000,  # NIST recommendation
            backend=self.backend
        )
        
        return kdf.derive(biometric_hash.encode())
    
    async def _create_schema(self):
        """Create database schema for configuration storage"""
        cursor = self.connection.cursor()
        
        # Main configuration table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value_encrypted BLOB NOT NULL,
                nonce BLOB NOT NULL,
                tag BLOB NOT NULL,
                category TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Core-specific configurations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core_config (
                core_name TEXT NOT NULL,
                key TEXT NOT NULL,
                value_encrypted BLOB NOT NULL,
                nonce BLOB NOT NULL,
                tag BLOB NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (core_name, key)
            )
        """)
        
        # Security policies
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_policies (
                policy_name TEXT PRIMARY KEY,
                policy_data_encrypted BLOB NOT NULL,
                nonce BLOB NOT NULL,
                tag BLOB NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        self.connection.commit()
        logger.debug("Database schema created/verified")
    
    async def _initialize_defaults(self):
        """Initialize database with default configuration values"""
        cursor = self.connection.cursor()
        
        # Check if already initialized
        cursor.execute("SELECT COUNT(*) FROM system_config")
        count = cursor.fetchone()[0]
        
        if count > 0:
            logger.debug("Configuration database already contains data")
            return
        
        logger.info("Initializing configuration database with default values...")
        
        # System configuration defaults
        system_defaults = {
            "system_name": "A.A.R.I.A",
            "version": "1.0.0",
            "tick_rate": 0.1,
            "watchdog_interval": 5.0,
            "auto_recovery": True,
            "log_level": "INFO",
        }
        
        for key, value in system_defaults.items():
            await self.set_config("system", key, value)
        
        # Interface configuration
        interface_defaults = {
            "cli_enabled": True,
            "api_enabled": False,
            "voice_enabled": False,
        }
        
        for key, value in interface_defaults.items():
            await self.set_config("interface", key, value)
        
        logger.info("Default configuration values initialized")
    
    async def _encrypt_data(self, data: Any) -> tuple:
        """
        Encrypt data using AES-256-GCM
        
        Returns:
            tuple: (encrypted_data, nonce, tag)
        """
        if not self.master_key:
            raise RuntimeError("Database not initialized with encryption key")
        
        # Serialize data to JSON
        if not isinstance(data, (str, bytes)):
            data = json.dumps(data)
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Generate random nonce
        nonce = os.urandom(12)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.master_key),
            modes.GCM(nonce),
            backend=self.backend
        )
        
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(data) + encryptor.finalize()
        tag = encryptor.tag
        
        return encrypted_data, nonce, tag
    
    async def _decrypt_data(self, encrypted_data: bytes, nonce: bytes, tag: bytes) -> Any:
        """
        Decrypt data using AES-256-GCM
        
        Returns:
            Decrypted data (deserialized from JSON if applicable)
        """
        if not self.master_key:
            raise RuntimeError("Database not initialized with encryption key")
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.master_key),
            modes.GCM(nonce, tag),
            backend=self.backend
        )
        
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
        
        # Try to deserialize as JSON
        try:
            return json.loads(decrypted_data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return decrypted_data.decode('utf-8')
    
    async def set_config(self, category: str, key: str, value: Any) -> bool:
        """
        Set a configuration value (encrypted)
        
        Args:
            category: Configuration category (e.g., 'system', 'interface')
            key: Configuration key
            value: Configuration value (will be encrypted)
            
        Returns:
            bool: True if successful
        """
        try:
            encrypted_data, nonce, tag = await self._encrypt_data(value)
            
            cursor = self.connection.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO system_config 
                (key, value_encrypted, nonce, tag, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, COALESCE(
                    (SELECT created_at FROM system_config WHERE key = ?), ?
                ), ?)
            """, (key, encrypted_data, nonce, tag, category, key, now, now))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to set config {category}.{key}: {e}")
            return False
    
    async def get_config(self, category: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value (decrypted)
        
        Args:
            category: Configuration category
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Decrypted configuration value or default
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT value_encrypted, nonce, tag FROM system_config
                WHERE key = ? AND category = ?
            """, (key, category))
            
            row = cursor.fetchone()
            
            if row is None:
                return default
            
            encrypted_data, nonce, tag = row
            return await self._decrypt_data(encrypted_data, nonce, tag)
            
        except Exception as e:
            logger.error(f"Failed to get config {category}.{key}: {e}")
            return default
    
    async def get_all_config(self, category: str) -> Dict[str, Any]:
        """
        Get all configuration values for a category
        
        Args:
            category: Configuration category
            
        Returns:
            Dictionary of all config values in category
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT key, value_encrypted, nonce, tag FROM system_config
                WHERE category = ?
            """, (category,))
            
            config = {}
            for row in cursor.fetchall():
                key, encrypted_data, nonce, tag = row
                config[key] = await self._decrypt_data(encrypted_data, nonce, tag)
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to get all config for {category}: {e}")
            return {}
    
    async def set_core_config(self, core_name: str, key: str, value: Any) -> bool:
        """Set configuration for a specific core"""
        try:
            encrypted_data, nonce, tag = await self._encrypt_data(value)
            
            cursor = self.connection.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO core_config 
                (core_name, key, value_encrypted, nonce, tag, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, COALESCE(
                    (SELECT created_at FROM core_config WHERE core_name = ? AND key = ?), ?
                ), ?)
            """, (core_name, key, encrypted_data, nonce, tag, core_name, key, now, now))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to set core config {core_name}.{key}: {e}")
            return False
    
    async def get_core_config(self, core_name: str) -> Dict[str, Any]:
        """Get all configuration for a specific core"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT key, value_encrypted, nonce, tag FROM core_config
                WHERE core_name = ?
            """, (core_name,))
            
            config = {}
            for row in cursor.fetchall():
                key, encrypted_data, nonce, tag = row
                config[key] = await self._decrypt_data(encrypted_data, nonce, tag)
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to get core config for {core_name}: {e}")
            return {}
    
    async def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Configuration database closed")
    
    def __del__(self):
        """Cleanup on deletion"""
        if self.connection:
            self.connection.close()


# Global database instance
_config_db_instance: Optional[SecureConfigDatabase] = None

async def get_config_database(biometric_hash: str = None) -> SecureConfigDatabase:
    """
    Get or create the global configuration database instance
    
    Args:
        biometric_hash: Required for first initialization
        
    Returns:
        SecureConfigDatabase instance
    """
    global _config_db_instance
    
    if _config_db_instance is None:
        _config_db_instance = SecureConfigDatabase()
        
        if biometric_hash:
            success = await _config_db_instance.initialize(biometric_hash)
            if not success:
                raise RuntimeError("Failed to initialize secure configuration database")
        else:
            raise ValueError("Biometric hash required for first database initialization")
    
    return _config_db_instance
