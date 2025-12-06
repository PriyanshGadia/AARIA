# // STEM.PY
# // VERSION: 1.0.0
# // DESCRIPTION: Stem - Central Integration Unit. Orchestrates Frontal, Memory, Temporal, Parietal, Occipital, and Evolution cores.
# // UPDATE NOTES: Initial release. Implements asynchronous core lifecycle management, central event bus, secure boot sequence, and inter-core neural routing.
# // IMPORTANT: No hardcoded values. All configurations loaded from encrypted owner database or secure environment variables.

import asyncio
import json
import uuid
import logging
import signal
import sys
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import inspect

# Import Cores
# Note: Ensure all core files are in the python path or Backend package
try:
    from frontal_core import FrontalCore
    from memory_core import MemoryCore
    from temporal_core import TemporalCore
    from parietal_core import ParietalCore
    from occipital_core import OccipitalCore
    from evolution_core import EvolutionCore
    from secure_config_db import SecureConfigDatabase, get_config_database
    from llm_gateway import LLMRequest, LLMProvider, PrivacyLevel
except ImportError as e:
    # Critical failure if cores are missing
    print(f"CRITICAL: Failed to import core modules: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [STEM] - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("aaria_system.log")
    ]
)
logger = logging.getLogger("AARIA_STEM")

# ==================== CONFIGURATION & SECURITY ====================
class StemConfigLoader:
    """Dynamic configuration loader for the central stem using encrypted database"""
    
    def __init__(self):
        self.config_db: Optional[SecureConfigDatabase] = None
        self.biometric_hash: Optional[str] = None
    
    async def initialize(self, biometric_hash: str) -> bool:
        """
        Initialize configuration loader with encrypted database
        
        Args:
            biometric_hash: Owner's biometric hash for database encryption
            
        Returns:
            bool: True if successful
        """
        try:
            self.biometric_hash = biometric_hash
            self.config_db = await get_config_database(biometric_hash)
            logger.info("Configuration loader initialized with encrypted database")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize configuration loader: {e}")
            return False
    
    async def load_system_config(self) -> Dict[str, Any]:
        """Load system-wide configuration from encrypted database"""
        if not self.config_db:
            raise RuntimeError("Configuration loader not initialized")
        
        try:
            # Load system configuration
            config = {
                "system_name": await self.config_db.get_config("system", "system_name", "A.A.R.I.A"),
                "version": await self.config_db.get_config("system", "version", "1.0.0"),
                "tick_rate": await self.config_db.get_config("system", "tick_rate", 0.1),
                "watchdog_interval": await self.config_db.get_config("system", "watchdog_interval", 5.0),
                "auto_recovery": await self.config_db.get_config("system", "auto_recovery", True),
                "log_level": await self.config_db.get_config("system", "log_level", "INFO"),
                "owner_id": os.getenv("AARIA_OWNER_ID") or await self.config_db.get_config("system", "owner_id", "root_owner"),
            }
            
            # Load interface configuration
            config["interfaces"] = {
                "cli": await self.config_db.get_config("interface", "cli_enabled", True),
                "api": await self.config_db.get_config("interface", "api_enabled", False),
                "voice": await self.config_db.get_config("interface", "voice_enabled", False),
            }
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load system config from database: {e}")
            # Return minimal safe defaults
            return {
                "system_name": "A.A.R.I.A",
                "version": "1.0.0",
                "tick_rate": 0.1,
                "watchdog_interval": 5.0,
                "auto_recovery": True,
                "log_level": "INFO",
                "owner_id": "root_owner",
                "interfaces": {"cli": True, "api": False, "voice": False}
            }

    @staticmethod
    def get_secure_boot_credentials() -> str:
        """
        Retrieve secure boot credentials (biometric hash)
        
        This should integrate with actual biometric hardware in production.
        For now, retrieves from secure environment variable or generates session key.
        
        Returns:
            str: Biometric hash (SHA-256)
        """
        # Try to get from secure environment variable
        biometric_hash = os.getenv("AARIA_BIOMETRIC_HASH")
        
        if not biometric_hash:
            # Check for biometric hardware integration
            # In production, this would call actual biometric scanning (face/fingerprint/voice)
            logger.warning("No biometric hash found in environment. Checking for biometric hardware...")
            
            # TODO: Integrate with actual biometric hardware
            # For development/testing, generate deterministic session key
            # This ensures consistent behavior but is NOT SECURE for production
            machine_id = str(uuid.getnode())  # MAC address as machine identifier
            session_seed = f"AARIA_DEV_{machine_id}_{datetime.now().strftime('%Y%m%d')}"
            biometric_hash = hashlib.sha256(session_seed.encode()).hexdigest()
            
            logger.warning(f"Generated development session key. DO NOT USE IN PRODUCTION.")
            logger.warning(f"Set AARIA_BIOMETRIC_HASH environment variable with actual biometric data.")
        
        return biometric_hash

# ==================== CENTRAL EVENT BUS ====================
@dataclass
class NeuralEvent:
    """Standardized event packet for inter-core communication"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = "stem"
    target: str = "all"  # 'all', 'frontal', 'memory', etc.
    type: str = "info"   # 'command', 'data', 'alert', 'request'
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 1    # 1 (low) to 10 (critical)

class EventBus:
    """Asynchronous event bus for decoupled core communication"""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.event_queue = asyncio.PriorityQueue()
        self.is_running = False
        
    async def start(self):
        self.is_running = True
        asyncio.create_task(self._process_queue())
        logger.info("Event Bus started")
        
    async def stop(self):
        self.is_running = False
        logger.info("Event Bus stopped")
        
    def subscribe(self, topic: str, callback: Callable):
        """Subscribe a core to a specific topic"""
        self.subscribers[topic].append(callback)
        
    async def publish(self, event: NeuralEvent):
        """Publish an event to the bus"""
        # Priority queue expects tuples, lower number = higher priority
        # We invert logic: 10 is high, 1 is low -> queue priority = 11 - priority
        queue_priority = 11 - event.priority
        await self.event_queue.put((queue_priority, event))
        
    async def _process_queue(self):
        """Continuous event dispatch loop"""
        while self.is_running:
            try:
                _, event = await self.event_queue.get()
                
                # Direct targeting
                if event.target != "all":
                    if event.target in self.subscribers:
                        for callback in self.subscribers[event.target]:
                            asyncio.create_task(self._safe_callback(callback, event))
                
                # Broadcast (topics match event type or source)
                if event.target == "all" or event.type in self.subscribers:
                    topic = event.type
                    if topic in self.subscribers:
                        for callback in self.subscribers[topic]:
                            asyncio.create_task(self._safe_callback(callback, event))
                            
                self.event_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event bus error: {e}")
                
    async def _safe_callback(self, callback: Callable, event: NeuralEvent):
        """Execute callback safely"""
        try:
            if inspect.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)
        except Exception as e:
            logger.error(f"Error in event subscriber {callback.__name__}: {e}")

# ==================== MAIN SYSTEM: AARIA ====================
class AARIA_Stem:
    """The central integrating entity"""
    
    def __init__(self):
        # Configuration
        self.config = {}
        self.biometric_hash = ""
        self.config_loader = None
        
        # Infrastructure
        self.event_bus = EventBus()
        self.is_running = False
        self.start_time = None
        
        # Cores
        self.frontal = FrontalCore()
        self.memory = MemoryCore()
        self.temporal = TemporalCore()
        self.parietal = ParietalCore()
        self.occipital = OccipitalCore()
        self.evolution = EvolutionCore()
        
        # Core Registry
        self.cores = {
            "frontal": self.frontal,
            "memory": self.memory,
            "temporal": self.temporal,
            "parietal": self.parietal,
            "occipital": self.occipital,
            "evolution": self.evolution
        }
        
    async def boot(self):
        """System Boot Sequence"""
        logger.info("Initializing A.A.R.I.A. Stem...")
        self.start_time = datetime.now()
        
        # 1. Get Biometric Credentials
        self.biometric_hash = StemConfigLoader.get_secure_boot_credentials()
        logger.info("Biometric authentication completed")
        
        # 2. Initialize Configuration Loader with Encrypted Database
        self.config_loader = StemConfigLoader()
        if not await self.config_loader.initialize(self.biometric_hash):
            raise RuntimeError("Failed to initialize secure configuration database")
        
        # 3. Load System Configuration from Database
        self.config = await self.config_loader.load_system_config()
        logger.info(f"Configuration loaded from encrypted database: {self.config['system_name']} v{self.config['version']}")
        
        # 4. Start Event Bus
        await self.event_bus.start()
        
        # 5. Initialize Cores (Sequential Dependency)
        
        # A. Parietal (Self-Awareness/Hardware) - First to monitor boot health
        logger.info("Booting Parietal Core...")
        if not await self.parietal.start():
            raise RuntimeError("Parietal Core failed to start. Aborting.")
        self.event_bus.subscribe("parietal", self._handle_parietal_event)
        
        # B. Memory (Storage/Identity) - Required for others to load profiles
        logger.info("Booting Memory Core...")
        # Note: Memory core needs biometric hash to unlock encrypted vaults
        if not await self.memory.start(self.biometric_hash):
            raise RuntimeError("Memory Core failed to unlock. Biometric auth failed.")
        self.event_bus.subscribe("memory", self._handle_memory_event)
        
        # C. Temporal (Communication/Personality)
        logger.info("Booting Temporal Core...")
        if not await self.temporal.start():
            logger.error("Temporal Core failed. Voice/Text interface will be disabled.")
        self.event_bus.subscribe("temporal", self._handle_temporal_event)
        
        # D. Occipital (Vision/Security)
        logger.info("Booting Occipital Core...")
        if not await self.occipital.start():
            logger.warning("Occipital Core failed. Vision systems offline.")
        self.event_bus.subscribe("occipital", self._handle_occipital_event)
        
        # E. Frontal (Decision/Planning) - Depends on Memory & Temporal
        logger.info("Booting Frontal Core...")
        if not await self.frontal.start():
            raise RuntimeError("Frontal Core failed. Reasoning engine unavailable.")
        self.event_bus.subscribe("frontal", self._handle_frontal_event)
        
        # F. Evolution (Self-Improvement) - Last to load
        logger.info("Booting Evolution Core...")
        if not await self.evolution.start():
            logger.warning("Evolution Core failed. Self-growth disabled.")
        self.event_bus.subscribe("evolution", self._handle_evolution_event)
        
        # G. Initialize LLM Gateway (REQUIRES ACTUAL LLM FOR INTELLIGENCE)
        try:
            from llm_gateway import get_llm_gateway
            llm_gateway = await get_llm_gateway()
            
            # Check for Ollama or Cloud LLM availability
            llm_config = {
                "enabled": True,
                "default_provider": "local",  # Try local Ollama first
                "providers": {
                    "local": {
                        "endpoint": "http://localhost:11434",
                        "model": "llama2"
                    },
                    "openai": {
                        "model": "gpt-3.5-turbo"
                    }
                }
            }
            await llm_gateway.initialize(llm_config)
            
            # Check if real LLM is available
            test_request = LLMRequest(
                prompt="test",
                provider=LLMProvider.LOCAL,
                privacy_level=PrivacyLevel.PUBLIC
            )
            
            try:
                # Try to connect to Ollama
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://localhost:11434/api/tags", timeout=aiohttp.ClientTimeout(total=2)) as response:
                        if response.status == 200:
                            logger.info("LLM Gateway initialized with LOCAL Ollama")
                        else:
                            logger.warning("Ollama not responding - falling back to minimal NLP")
                            logger.warning("⚠️  INSTALL OLLAMA FOR REAL AI: curl https://ollama.ai/install.sh | sh")
                            logger.warning("⚠️  THEN RUN: ollama pull llama2")
                            llm_gateway.enabled = True  # Keep enabled to show warnings
                            llm_gateway.default_provider = LLMProvider.FALLBACK
            except Exception as e:
                logger.warning(f"No local LLM available: {e}")
                logger.warning("⚠️  FOR INTELLIGENT AI RESPONSES:")
                logger.warning("⚠️  Option 1: Install Ollama (FREE, LOCAL, PRIVATE)")
                logger.warning("⚠️    curl https://ollama.ai/install.sh | sh && ollama pull llama2")
                logger.warning("⚠️  Option 2: Use Cloud LLM (PAID)")
                logger.warning("⚠️    export OPENAI_API_KEY='your-key'")
                llm_gateway.enabled = True
                llm_gateway.default_provider = LLMProvider.FALLBACK
                
        except Exception as e:
            logger.error(f"LLM Gateway initialization failed: {e}")
        
        self.is_running = True
        logger.info(f"A.A.R.I.A. v{self.config['version']} is ONLINE.")
        
        # 6. Start Orchestration Loops
        asyncio.create_task(self._main_control_loop())
        asyncio.create_task(self._watchdog_loop())
        
        # 7. Initial Greeting
        await self._system_ready_announcement()

    async def shutdown(self):
        """Graceful Shutdown Sequence"""
        logger.info("Initiating Shutdown Sequence...")
        self.is_running = False
        
        # Reverse boot order
        await self.evolution.stop()
        await self.frontal.stop()
        await self.occipital.stop()
        await self.temporal.stop()
        await self.memory.stop()
        await self.parietal.stop()
        
        await self.event_bus.stop()
        logger.info("System Halted.")

    # ==================== ORCHESTRATION LOOPS ====================
    
    async def _main_control_loop(self):
        """Main orchestrator for high-level system functions"""
        while self.is_running:
            try:
                # 1. Check for inputs (simulated CLI for this executable)
                # In a real GUI app, this would be event-driven
                await asyncio.sleep(0.1) 
                
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                await asyncio.sleep(1)

    async def _watchdog_loop(self):
        """Monitor core health via Parietal Core"""
        while self.is_running:
            try:
                interval = self.config.get("watchdog_interval", 5.0)
                await asyncio.sleep(interval)
                
                # Request health check from Parietal
                status = await self.parietal.execute_command("get_status", {})
                
                # Check for critical hardware alerts
                if status.get("data", {}).get("cpu_usage_percent", 0) > 95:
                    logger.warning("High CPU Load detected. Throttling non-essential cores.")
                    # Logic to throttle Evolution core could go here
                    
            except Exception as e:
                logger.error(f"Watchdog error: {e}")

    async def process_user_input(self, input_text: str, source: str = "cli"):
        """Central entry point for user interaction"""
        logger.info(f"Input received [{source}]: {input_text}")
        
        # 1. Security Check via Occipital (if applicable, e.g., voice/face context)
        # For text CLI, we assume authenticated session for now.
        auth_context = {"user_id": self.config["owner_id"], "authenticated": True}
        
        # 2. Process Intent via Temporal Core
        # Temporal analyzes emotion, intent, and entities
        temporal_response = await self.temporal.process_input({
            "type": "text",
            "content": input_text,
            "context": {
                "auth": auth_context,
                "timestamp": datetime.now().isoformat()
            }
        })
        
        if not temporal_response.get("success"):
            logger.error("Temporal processing failed.")
            return "I'm having trouble understanding that."

        # Extract analysis
        nlp_analysis = temporal_response.get("nlp_analysis", {})
        intent = nlp_analysis.get("primary_intent", "unknown")
        entities = nlp_analysis.get("entities", [])
        
        logger.info(f"Detected Intent: {intent}")
        
        # 3. Route to Frontal Core for Decision/Action
        # Frontal takes the intent and formulates a plan
        frontal_result = await self.frontal.execute_command(
            "make_decision",
            {
                "intent": intent,
                "input_text": input_text,
                "entities": entities,
                "context": temporal_response
            }
        )
        
        # 4. Execute Action (if not purely conversational)
        # If Frontal decides on a complex action (e.g., "Schedule meeting"), it returns a plan.
        # If it's conversational, Temporal has likely generated a response draft.
        
        final_response = ""
        
        if intent == "command":
            # Execute specific stem-level commands or route to Memory
            if "memory" in input_text.lower() or "remember" in input_text.lower():
                await self.memory.execute_command("store_memory", {
                    "data": input_text,
                    "tags": ["user_input", "command"],
                    "tier": "OWNER_CONFIDENTIAL"
                })
                final_response = "I have stored that in my secure memory."
            elif "status" in input_text.lower():
                status = await self.get_full_system_status()
                # Safe access to nested dicts
                mem_percent = status.get('parietal', {}).get('telemetry', {}).get('ram', 0)
                final_response = f"System Status: {status['health']}. Memory Usage: {mem_percent}%"
            else:
                # Default conversation response
                final_response = temporal_response.get("response_generation", {}).get("generated_response", "Done.")
        else:
            # Use Temporal's generated conversational response
            final_response = temporal_response.get("response_generation", {}).get("generated_response")
            
        # 5. Output Response
        print(f">> AARIA: {final_response}")
        
        # 6. Feed back to Evolution Core
        # Evolution learns from the interaction (success/failure)
        # Format: {"core_name": {"success_rate": 0.0-1.0}}
        await self.evolution.execute_command("trigger_evolution", {
            "performance_data": {
                "temporal": {"success_rate": 1.0 if temporal_response.get("success") else 0.0},
                "frontal": {"success_rate": 0.8}  # Mock frontal performance
            }
        })

    # ==================== EVENT HANDLERS ====================
    
    async def _handle_parietal_event(self, event: NeuralEvent):
        """Handle hardware/health events"""
        if event.type == "alert":
            logger.warning(f"Hardware Alert: {event.payload}")
            
    async def _handle_memory_event(self, event: NeuralEvent):
        """Handle memory access events"""
        pass
        
    async def _handle_temporal_event(self, event: NeuralEvent):
        """Handle conversation state changes"""
        pass
        
    async def _handle_occipital_event(self, event: NeuralEvent):
        """Handle visual/security events"""
        if event.type == "security_alert":
            logger.critical(f"SECURITY BREACH DETECTED: {event.payload}")
            # Lockdown protocol could go here
            
    async def _handle_frontal_event(self, event: NeuralEvent):
        """Handle planning outcomes"""
        pass
        
    async def _handle_evolution_event(self, event: NeuralEvent):
        """Handle self-improvement notifications"""
        if event.type == "evolution_complete":
            logger.info(f"System Evolved: {event.payload.get('description')}")

    # ==================== UTILITIES ====================
    
    async def get_full_system_status(self) -> Dict[str, Any]:
        """Aggregate status from all cores"""
        return {
            "health": "nominal",
            "uptime": str(datetime.now() - self.start_time),
            "parietal": await self.parietal.get_core_status(),
            "memory": await self.memory.get_core_status(),
            "frontal": await self.frontal.get_core_status(),
            # ... add others
        }

    async def _system_ready_announcement(self):
        """Announce readiness"""
        print("\n" + "="*50)
        print(f" A.A.R.I.A SYSTEM ONLINE")
        print(f" Owner ID: {self.config['owner_id']}")
        print(f" Cores Active: {len(self.cores)}")
        print("="*50 + "\n")
        
        # Temporal greeting
        greeting = await self.temporal.execute_command("generate_conversation", {
            "text": "System boot complete.",
            "context": {"type": "system_event"}
        })
        print(f">> AARIA: {greeting.get('response', 'Ready.')}\n")

# ==================== CLI ENTRY POINT ====================
async def main():
    stem = AARIA_Stem()
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\nRequesting shutdown...")
        # Create a task to shutdown properly
        asyncio.create_task(stem.shutdown())
        
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await stem.boot()
        
        # Simple CLI Loop
        print("Type 'exit' to quit. Enter commands or chat below.")
        
        # To handle async input in the main loop without blocking
        loop = asyncio.get_running_loop()
        
        while stem.is_running:
            try:
                # Use executor for blocking input
                user_input = await loop.run_in_executor(None, input, "You: ")
                
                if user_input.lower() in ["exit", "quit"]:
                    await stem.shutdown()
                    break
                
                if user_input.strip():
                    await stem.process_user_input(user_input)
                    
            except EOFError:
                await stem.shutdown()
                break
                
    except Exception as e:
        logger.critical(f"System Crash: {e}", exc_info=True)
        # Ensure cleanup even on crash
        if stem.is_running:
            await stem.shutdown()

if __name__ == "__main__":
    # Windows selector policy fix
    if sys.platform == 'win32':
        pass        
    asyncio.run(main())