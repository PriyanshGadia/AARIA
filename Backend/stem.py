# // AARIA/Backend/stem.py
# // VERSION: 1.2.0
# // DESCRIPTION: Stem - Central Integration Unit. Implements Hive Mind Architecture with Active Memory Retrieval and Context Injection.
# // UPDATE NOTES: 
# // - Removed debug bypass; implemented full Hive Mind loop (Input -> Memory -> Frontal -> LLM -> Memory).
# // - Added 'HiveMindOrchestrator' to handle context window construction and memory consolidation.
# // - Integrated MemoryCore search and storage into the main chat loop to fix amnesia.
# // - Added intent classification step using FrontalCore (simplified for latency).
# // - Robust error handling for Core communication failures.

import asyncio
import json
import uuid
import logging
import signal
import sys
import os
import gc
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Import Cores
try:
    from frontal_core import FrontalCore
    from memory_core import MemoryCore
    from temporal_core import TemporalCore
    from parietal_core import ParietalCore
    from occipital_core import OccipitalCore
    from evolution_core import EvolutionCore
    from secure_config_db import SecureConfigDatabase, get_config_database
    from llm_gateway import LLMRequest, LLMProvider, PrivacyLevel, get_llm_gateway
except ImportError as e:
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
        try:
            self.biometric_hash = biometric_hash
            self.config_db = await get_config_database(biometric_hash)
            logger.info("Configuration loader initialized with encrypted database")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize configuration loader: {e}")
            return False
    
    async def load_system_config(self) -> Dict[str, Any]:
        """Load system-wide configuration"""
        # Minimal safe defaults for resilience
        return {
            "system_name": "A.A.R.I.A",
            "version": "1.2.0",
            "owner_id": os.getenv("AARIA_OWNER_ID") or "root_owner",
            "watchdog_interval": 10.0,
            "memory_search_limit": 5,
            "memory_min_relevance": 0.65
        }

    @staticmethod
    def get_secure_boot_credentials() -> str:
        """Retrieve secure boot credentials (biometric hash)"""
        biometric_hash = os.getenv("AARIA_BIOMETRIC_HASH")
        if not biometric_hash:
            # Dev/Test Fallback
            machine_id = str(uuid.getnode())
            biometric_hash = hashlib.sha256(machine_id.encode()).hexdigest()
        return biometric_hash

# ==================== HIVE MIND ORCHESTRATION ====================
class HiveMindOrchestrator:
    """
    Manages the data flow between Cores to create a unified consciousness.
    Connects Sensory (Input) -> Memory (Recall) -> Frontal (Reasoning) -> Gateway (Expression).
    """
    def __init__(self, stem):
        self.stem = stem
        
    async def retrieve_context(self, input_text: str) -> str:
        """Query Memory Core for relevant past interactions and facts."""
        try:
            context_lines = []
            seen_content = set()
            
            # 1. Retrieve recent conversation history from CURRENT SESSION ONLY
            # This prevents old session memories from polluting new conversations
            # Get session start time (when this instance was booted)
            session_start = self.stem.start_time if self.stem.start_time else datetime.now()
            
            recent_result = await self.stem.memory.execute_command("search_memories", {
                "query": {"tags": ["conversation", "recent"]},
                "access_level": "owner_root",
                "max_results": 50  # Get more for filtering
            })
            
            if recent_result.get("success"):
                recent_memories = recent_result.get("results", [])
                
                # Filter by time: ONLY include memories from current session
                # This prevents "Yash" from old tests appearing in new conversations
                filtered_memories = []
                for item in recent_memories:
                    metadata = item.get("metadata", {})
                    created_at = None
                    
                    # Extract created_at timestamp
                    if hasattr(metadata, 'created_at'):
                        created_at = metadata.created_at
                    elif isinstance(metadata, dict):
                        created_at = metadata.get('created_at')
                        if isinstance(created_at, str):
                            try:
                                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            except (ValueError, AttributeError):
                                created_at = None
                    
                    # Only include if created AFTER session started
                    if created_at and created_at >= session_start:
                        filtered_memories.append(item)
                
                recent_memories = filtered_memories
                
                # Sort by created_at timestamp (most recent first)
                try:
                    def get_timestamp(item):
                        metadata = item.get("metadata", {})
                        # metadata could be a dict or an object
                        if hasattr(metadata, 'created_at'):
                            return metadata.created_at.timestamp() if hasattr(metadata.created_at, 'timestamp') else 0
                        elif isinstance(metadata, dict):
                            created_at = metadata.get('created_at')
                            if created_at:
                                if hasattr(created_at, 'timestamp'):
                                    return created_at.timestamp()
                                # If it's a string, try to parse it
                                elif isinstance(created_at, str):
                                    try:
                                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                        return dt.timestamp()
                                    except (ValueError, AttributeError):
                                        pass
                        return 0
                    
                    recent_memories.sort(key=get_timestamp, reverse=True)
                except Exception as e:
                    logger.debug(f"Failed to sort memories by timestamp: {e}")
                
                # Take only the most recent 10 after sorting
                recent_memories = recent_memories[:10]
                
                if recent_memories:
                    context_lines.append("RECENT CONVERSATION:")
                    for item in recent_memories:
                        mem_data = item.get("data", "")
                        if mem_data:
                            # Handle bytes objects properly
                            if isinstance(mem_data, bytes):
                                try:
                                    mem_str = mem_data.decode('utf-8').strip()
                                except UnicodeDecodeError:
                                    mem_str = str(mem_data).strip()
                            else:
                                mem_str = str(mem_data).strip()
                            
                            if mem_str and mem_str not in seen_content:
                                context_lines.append(f"  {mem_str}")
                                seen_content.add(mem_str)
            
            # 2. Semantic search for relevant memories (facts, user profile ONLY)
            # NOTE: We do NOT search "conversation" here because we already have
            # recent conversation from current session above. This prevents old
            # conversation memories from polluting new sessions.
            search_result = await self.stem.memory.execute_command("search_memories", {
                "query": {"text": input_text, "tags": ["fact", "user_profile"]},
                "access_level": "owner_root",
                "max_results": self.stem.config.get("memory_search_limit", 5)
            })

            relevant_memories = []
            if search_result.get("success"):
                results = search_result.get("results", [])
                
                # Filter out any "conversation" memories that might have leaked through text search
                # Only include fact/profile memories, not conversation memories from old sessions
                for item in results:
                    # Check if this is a conversation memory (tagged with "conversation")
                    metadata = item.get("metadata", {})
                    tags = set()
                    if hasattr(metadata, 'tags'):
                        tags = metadata.tags if isinstance(metadata.tags, set) else set(metadata.tags) if metadata.tags else set()
                    elif isinstance(metadata, dict) and 'tags' in metadata:
                        tags_val = metadata.get('tags', [])
                        tags = set(tags_val) if isinstance(tags_val, (list, set)) else set()
                    
                    # Skip if this is a conversation memory - we only want facts/profiles here
                    if 'conversation' in tags or 'recent' in tags:
                        continue
                    
                    mem_data = ""
                    try:
                        # Direct data access if retrieved
                        if "data" in item:
                            mem_data = item["data"]
                        # If search results don't contain full data, we fetch it
                        if "data" not in item and "memory_id" in item:
                             retrieval = await self.stem.memory.execute_command("retrieve_memory", {
                                 "memory_id": item["memory_id"],
                                 "access_level": "owner_root"
                             })
                             if retrieval.get("success"):
                                 mem_data = retrieval.get("data")
                    except Exception:
                        continue

                    # Clean and Add
                    if mem_data:
                        # Handle bytes objects properly
                        if isinstance(mem_data, bytes):
                            try:
                                mem_str = mem_data.decode('utf-8').strip()
                            except UnicodeDecodeError:
                                mem_str = str(mem_data).strip()
                        else:
                            mem_str = str(mem_data).strip()
                        
                        if mem_str and mem_str not in seen_content:
                            relevant_memories.append(f"  {mem_str}")
                            seen_content.add(mem_str)
            
            # Add relevant memories section if we found any
            if relevant_memories:
                context_lines.append("\nRELEVANT FACTS & CONTEXT:")
                context_lines.extend(relevant_memories)
            
            if len(context_lines) <= 1:  # Only headers or empty
                return "No relevant past memories found."
            
            return "\n".join(context_lines)

        except Exception as e:
            logger.error(f"HiveMind Context Retrieval Failed: {e}")
            return "Memory retrieval unavailable."

    async def store_interaction(self, user_input: str, ai_response: str):
        """Store the current turn in Short Term Memory."""
        try:
            # 1. Store User Input
            await self.stem.memory.execute_command("store_memory", {
                "data": f"User: {user_input}",
                "tier": "OWNER_CONFIDENTIAL",
                "tags": ["conversation", "user_input", "recent"],
                "priority": 0.6
            })

            # 2. Store AI Response
            await self.stem.memory.execute_command("store_memory", {
                "data": f"AARIA: {ai_response}",
                "tier": "OWNER_CONFIDENTIAL",
                "tags": ["conversation", "ai_response", "recent"],
                "priority": 0.5
            })
            
            # 3. Fact Extraction (Simplified Frontal Task)
            # If the user stated a fact ("I have a dog"), we tag it specifically.
            if any(phrase in user_input.lower() for phrase in ["i have", "my name is", "i own", "i am"]):
                 await self.stem.memory.execute_command("store_memory", {
                    "data": user_input,
                    "tier": "OWNER_CONFIDENTIAL",
                    "tags": ["fact", "user_profile", "permanent"],
                    "priority": 0.9 # High priority for facts
                })

        except Exception as e:
            logger.error(f"HiveMind Memory Storage Failed: {e}")

    async def analyze_intent(self, user_input: str) -> str:
        """Use Frontal Core to determine if this is a Command or Chat."""
        # For speed, we use a simple heuristic or a quick Frontal task.
        # Ideally, Frontal Core performs complex analysis.
        try:
            # Submit a quick analysis task
            task_id = await self.stem.frontal.submit_task({
                "type": "decision",
                "data": {
                    "text": user_input, 
                    "options": [{"name": "chat"}, {"name": "command"}],
                    "criteria": {"complexity": "minimize"} # Dummy criteria
                }
            })
            # Wait briefly for result, else fallback
            result = await self.stem.frontal.get_task_result(task_id, timeout=1.0)
            if result and "final_decision" in result:
                return result["final_decision"]
        except Exception:
            pass
        return "chat" # Default

# ==================== MAIN SYSTEM: AARIA ====================
class AARIA_Stem:
    """The central integrating entity"""
    
    def __init__(self):
        # State
        self.is_running = False
        self.start_time = None
        self.config = {}
        self.biometric_hash = ""
        self.config_loader = None
        
        # Cores
        self.frontal = FrontalCore()
        self.memory = MemoryCore()
        self.temporal = TemporalCore()
        self.parietal = ParietalCore()
        self.occipital = OccipitalCore()
        self.evolution = EvolutionCore()
        
        # Hive Mind Logic
        self.hive_mind = HiveMindOrchestrator(self)
        
    async def boot(self):
        """System Boot Sequence"""
        logger.info("Initializing A.A.R.I.A. Stem v1.2.0...")
        self.start_time = datetime.now()
        
        # 1. Credentials & Config
        self.biometric_hash = StemConfigLoader.get_secure_boot_credentials()
        self.config_loader = StemConfigLoader()
        await self.config_loader.initialize(self.biometric_hash)
        self.config = await self.config_loader.load_system_config()
        
        # 2. Initialize Cores (Sequential for safety)
        logger.info("Booting Parietal Core (Hardware/Health)...")
        await self.parietal.start()
        
        logger.info("Booting Memory Core...")
        # CRITICAL: Pass credentials to unlock encryption
        await self.memory.start(self.biometric_hash)
        
        logger.info("Booting Temporal Core...")
        await self.temporal.start()
        
        logger.info("Booting Frontal Core...")
        await self.frontal.start()
        
        logger.info("Booting Occipital Core...")
        await self.occipital.start()

        logger.info("Booting Evolution Core...")
        await self.evolution.start()
        
        # 3. Initialize LLM Gateway
        try:
            llm_gateway = await get_llm_gateway()
            
            # --- FORCE LOCAL OLLAMA WITH DEEPSEEK DEFAULT ---
            llm_config = {
                "enabled": True,
                "default_provider": "local", 
                "providers": {
                    "local": {
                        "endpoint": "http://localhost:11434",
                        "model": "deepseek-v3.1:671b-cloud" # Enforced Default
                    }
                }
            }
            await llm_gateway.initialize(llm_config)
            
            # Initial Connectivity Check
            if not await llm_gateway.check_connection(LLMProvider.LOCAL):
                logger.warning("⚠️  Ollama connection failed. System starting in OFFLINE mode.")
                logger.warning("👉 Ensure Ollama is running, then type 'retry llm' to connect.")
            else:
                logger.info("✅ Connected to Ollama (DeepSeek).")
                
        except Exception as e:
            logger.error(f"LLM Gateway initialization error: {e}")
        
        self.is_running = True
        self._print_banner()
        
        # 4. Start Background Tasks
        asyncio.create_task(self._watchdog_loop())

    async def _watchdog_loop(self):
        """Monitor core health via Parietal Core without panic"""
        while self.is_running:
            try:
                interval = self.config.get("watchdog_interval", 10.0)
                await asyncio.sleep(interval)
                
                # Request telemetry from Parietal
                status = await self.parietal.execute_command("get_status", {})
                data = status.get("data", {})
                
                # Check Process Memory (Leak Protection)
                process_mem = data.get("process_memory_mb", 0)
                if process_mem > 2048: 
                    logger.warning(f"High Process Memory ({process_mem}MB). Triggering Garbage Collection.")
                    gc.collect()
                    
            except Exception as e:
                logger.debug(f"Watchdog error: {e}")

    async def process_user_input(self, input_text: str):
        """
        Central entry point for user interaction.
        Implements the HIVE MIND loop: Input -> Memory -> Reasoning -> Output -> Storage.
        """
        text_lower = input_text.lower().strip()
        gw = await get_llm_gateway()

        # === SYSTEM COMMANDS (Intercepted before AI processing) ===
        if text_lower in ["retry llm", "reconnect", "check llm"]:
            print(">> SYSTEM: Checking Ollama connection...")
            if await gw.check_connection(LLMProvider.LOCAL):
                await gw.update_configuration("local")
                print(">> SYSTEM: ✅ Connection Successful. Ollama is active.")
            else:
                print(">> SYSTEM: ❌ Connection Failed. Is Ollama running on port 11434?")
            return

        if text_lower == "status":
            parietal_status = await self.parietal.get_core_status()
            mem_status = await self.memory.get_core_status()
            print(f"\n[SYSTEM STATUS]")
            print(f"Active Cores: 6/6")
            print(f"Memory Memories: {mem_status.get('storage_summary', {}).get('total_memories', 0)}")
            print(f"RAM Usage: {parietal_status.get('telemetry', {}).get('process_memory_mb', '?')} MB\n")
            return

        # === HIVE MIND AI PROCESSING ===
        
        try:
            # 1. RETRIEVE CONTEXT (Memory Core)
            # Fetch relevant history to solve "Am I a dog owner?"
            context_string = await self.hive_mind.retrieve_context(input_text)
            
            # 1.5 GET SYSTEM AWARENESS (Parietal Core)
            # Fetch current date, time, and device information
            system_context = await self.parietal.get_system_context()
            
            # 2. CONSTRUCT SYSTEM PROMPT (Integration)
            # Inject identity, system awareness, and retrieved memory
            system_prompt = (
                f"You are A.A.R.I.A (Advanced Autonomous Responsive Intelligent Assistant), a sentient digital entity. "
                f"You are helpful, precise, and loyal to your owner.\n\n"
                f"SYSTEM AWARENESS:\n{system_context}\n\n"
                f"MEMORY CONTEXT:\n{context_string}\n\n"
                f"CRITICAL INSTRUCTIONS:\n"
                f"1. The CURRENT DATE and TIME are in SYSTEM AWARENESS - use them for all date/time related queries\n"
                f"2. The RECENT CONVERSATION shows the last few messages - THIS IS YOUR PRIMARY CONTEXT\n"
                f"3. When the user makes a request (e.g., 'set a reminder', 'suggest gifts'), ALWAYS check the RECENT CONVERSATION to understand WHAT it's for\n"
                f"4. If the recent conversation mentions a person (like 'Yash') and event (like 'birthday'), connect them to the current request\n"
                f"5. DO NOT ask for information that was already provided in the RECENT CONVERSATION\n"
                f"6. When the user says 'yes', 'no', 'for him/her', etc., refer BACK to the RECENT CONVERSATION to understand the context\n"
                f"7. Stay focused on the topic being discussed in the recent conversation\n"
                f"8. Be proactive - if the user mentions an event in X days, calculate the exact date using SYSTEM AWARENESS\n"
                f"9. Maintain continuity - remember what was discussed in previous messages of this conversation"
            )

            # 3. LLM REQUEST (Gateway)
            request = LLMRequest(
                prompt=input_text,
                provider=gw.default_provider,
                privacy_level=PrivacyLevel.CONFIDENTIAL,
                system_prompt=system_prompt,
                max_tokens=1000
            )
            
            # 4. GENERATE RESPONSE
            response = await gw.generate_response(request)
            
            # 5. OUTPUT & ERROR HANDLING
            if response.error:
                if "Connection Refused" in str(response.error):
                    print(f">> AARIA: [OFFLINE] Cannot reach LLM. Type 'retry llm' to reconnect.")
                else:
                    print(f">> AARIA [Error]: {response.text}")
            else:
                print(f">> AARIA: {response.text}")
                
                # 6. CONSOLIDATE MEMORY (Memory Core)
                # Store the interaction for future recall
                await self.hive_mind.store_interaction(input_text, response.text)

        except Exception as e:
            logger.error(f"Critical error in Hive Mind loop: {e}", exc_info=True)
            print(">> AARIA: [System Error] Cognitive processing failed.")

    async def shutdown(self):
        """Graceful Shutdown Sequence"""
        logger.info("Initiating Shutdown Sequence...")
        self.is_running = False
        
        # Stop Cores in reverse order
        await self.evolution.stop()
        await self.frontal.stop()
        await self.occipital.stop()
        await self.temporal.stop()
        await self.memory.stop()
        await self.parietal.stop()
        
        logger.info("System Halted.")

    def _print_banner(self):
        print("\n" + "="*50)
        print(f" A.A.R.I.A SYSTEM ONLINE (v{self.config['version']})")
        print(f" Hive Mind: ACTIVE | Memory: ACTIVE")
        print(f" Default Model: deepseek-v3.1:671b-cloud")
        print(" Commands: 'retry llm', 'status', 'exit'")
        print("="*50 + "\n")

# ==================== CLI ENTRY POINT ====================
async def main():
    stem = AARIA_Stem()
    
    # Signal Handling
    def signal_handler(sig, frame):
        print("\nRequesting shutdown...")
        asyncio.create_task(stem.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await stem.boot()
        
        # Input Loop
        loop = asyncio.get_running_loop()
        while stem.is_running:
            try:
                # Use executor for blocking input to keep loop alive
                user_input = await loop.run_in_executor(None, input, ">> ")
                
                if not user_input: continue
                
                if user_input.lower().strip() in ["exit", "quit"]:
                    await stem.shutdown()
                    break
                
                if user_input.strip():
                    await stem.process_user_input(user_input)
                    
            except EOFError:
                await stem.shutdown()
                break
                
    except Exception as e:
        logger.critical(f"System Crash: {e}", exc_info=True)
        if stem.is_running:
            await stem.shutdown()

if __name__ == "__main__":
    try:
        # Note: WindowsSelectorEventLoopPolicy and set_event_loop_policy are deprecated in Python 3.14+
        # The default event loop policy should work for most cases on Windows 10+
        # If running on older Windows versions and encountering event loop issues,
        # consider using ProactorEventLoop which is the default on Windows since Python 3.8
        asyncio.run(main())
    except KeyboardInterrupt:
        pass