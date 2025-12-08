# // AARIA/Backend/llm_gateway.py
# // VERSION: 1.1.1
# // DESCRIPTION: Enterprise LLM Gateway with Circuit Breaker, DeepSeek Default, and Resilience Patterns.
# // UPDATE NOTES: 
# // - Fixed aiohttp ContentTypeError by relaxing JSON MIME type enforcement (fixes Ollama text/plain headers).
# // - Refined connection checking logic.

import asyncio
import json
import os
import re
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

# Configuration constants
LLM_ENV_FILE = 'llm.env'
DEFAULT_LOCAL_MODEL = "deepseek-v3.1:671b-cloud"
DEFAULT_OLLAMA_ENDPOINT = "http://localhost:11434"

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / LLM_ENV_FILE
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("AARIA_LLM_GATEWAY")

# ==================== CIRCUIT BREAKER PATTERN ====================
class CircuitBreakerState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing fast, service assumed down
    HALF_OPEN = "half_open" # Testing recovery

class CircuitBreaker:
    """
    Enterprise reliability pattern to prevent cascading failures.
    Monitors failure rates and 'trips' to prevent resource exhaustion on dead services.
    """
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = CircuitBreakerState.CLOSED

    def can_execute(self) -> bool:
        """Check if request allowed to proceed"""
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info("Circuit Breaker entering HALF_OPEN state - Probing service...")
                return True
            return False
        return True

    def record_success(self):
        """Reset counters on success"""
        if self.state != CircuitBreakerState.CLOSED:
            logger.info("Circuit Breaker recovering to CLOSED state.")
            self.state = CircuitBreakerState.CLOSED
            self.failures = 0

    def record_failure(self):
        """Increment failure count and potentially trip breaker"""
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            if self.state != CircuitBreakerState.OPEN:
                logger.warning(f"Circuit Breaker TRIPPED to OPEN state. Failures: {self.failures}")
            self.state = CircuitBreakerState.OPEN

# ==================== LLM PROVIDER TYPES ====================
class LLMProvider(Enum):
    """Supported LLM providers"""
    LOCAL = "local"           # Ollama (DeepSeek, LLaMA, etc.)
    OPENAI = "openai"         # OpenAI GPT models
    ANTHROPIC = "anthropic"   # Claude models
    GEMINI = "gemini"         # Google Gemini models
    GROQ = "groq"             # Groq (fast inference)
    FALLBACK = "fallback"     # Rule-based fallback

class PrivacyLevel(Enum):
    """Data privacy levels"""
    PUBLIC = "public"           # No sensitive data
    CONFIDENTIAL = "confidential"  # Some filtering needed
    OWNER_ONLY = "owner_only"   # Maximum privacy, local only

# ==================== PRIVACY FILTER ====================
class PrivacyFilter:
    """Filters sensitive data before sending to cloud LLMs"""
    
    def __init__(self):
        self.patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "api_key": r'\b[A-Za-z0-9_-]{32,}\b',
        }
    
    def sanitize(self, text: str, privacy_level: PrivacyLevel) -> str:
        if privacy_level == PrivacyLevel.OWNER_ONLY:
            return "[PRIVATE_DATA_REDACTED]"
        sanitized = text
        for pattern_name, pattern in self.patterns.items():
            sanitized = re.sub(pattern, f"[{pattern_name.upper()}_REDACTED]", sanitized)
        return sanitized
    
    def is_safe_for_cloud(self, text: str, privacy_level: PrivacyLevel) -> bool:
        if privacy_level == PrivacyLevel.OWNER_ONLY: return False
        for pattern in self.patterns.values():
            if re.search(pattern, text): return False
        return True

# ==================== DATA MODELS ====================
@dataclass
class LLMRequest:
    prompt: str
    provider: LLMProvider = LLMProvider.LOCAL
    privacy_level: PrivacyLevel = PrivacyLevel.CONFIDENTIAL
    context: Dict[str, Any] = field(default_factory=dict)
    max_tokens: int = 1000
    temperature: float = 0.7
    system_prompt: Optional[str] = None

@dataclass
class LLMResponse:
    text: str
    provider: str
    tokens_used: int = 0
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None

# ==================== LLM GATEWAY ====================
class LLMGateway:
    """Central Enterprise Gateway for all LLM interactions with Dynamic Configuration"""
    
    def __init__(self):
        self.privacy_filter = PrivacyFilter()
        self.providers_config = {}
        self.enabled = False
        self.default_provider = LLMProvider.LOCAL 
        self._circuit_breakers = {p: CircuitBreaker() for p in LLMProvider}
        
        # Configuration Defaults (overridden by initialize)
        self.default_local_model = DEFAULT_LOCAL_MODEL
        self._available_ollama_models = []
        
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize LLM Gateway with configuration"""
        try:
            self.enabled = config.get("enabled", True)
            self.providers_config = config.get("providers", {})
            
            # Map requested string to Enum
            requested_provider = config.get("default_provider", "local").upper()
            if requested_provider in LLMProvider.__members__:
                self.default_provider = LLMProvider[requested_provider]
            else:
                self.default_provider = LLMProvider.LOCAL

            # Resolve Model Config
            local_config = self.providers_config.get("local", {})
            self.default_local_model = local_config.get("model", DEFAULT_LOCAL_MODEL)

            # Initial Background Connectivity Check
            if self.default_provider == LLMProvider.LOCAL:
                asyncio.create_task(self._check_ollama_startup())
            
            logger.info(f"LLM Gateway Initialized. Active: {self.default_provider.name}, Local Model: {self.default_local_model}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize LLM Gateway: {e}")
            return False

    async def _check_ollama_startup(self):
        """Perform a startup check for Ollama to prime the circuit breaker"""
        try:
            is_up = await self.check_connection(LLMProvider.LOCAL)
            if not is_up:
                logger.warning(f"⚠️  Ollama connection failed on startup. Ensure Ollama is running at {DEFAULT_OLLAMA_ENDPOINT}")
            else:
                logger.info(f"✅ Ollama connection established.")
        except Exception:
            pass

    async def check_connection(self, provider: LLMProvider) -> bool:
        """Explicit connectivity check useful for CLI 'retry' commands"""
        try:
            import aiohttp
            if provider == LLMProvider.LOCAL:
                endpoint = self.providers_config.get("local", {}).get("endpoint", DEFAULT_OLLAMA_ENDPOINT)
                async with aiohttp.ClientSession() as session:
                    # Check tags endpoint to verify connectivity
                    async with session.get(f"{endpoint}/api/tags", timeout=2) as resp:
                        return resp.status == 200
            return True # Assume cloud providers are up if config exists
        except Exception:
            return False

    async def update_configuration(self, provider_name: str, api_key: str = None) -> str:
        """Dynamically update provider configuration at runtime."""
        try:
            provider_name = provider_name.lower()
            provider_enum = None
            
            try:
                provider_enum = LLMProvider[provider_name.upper()]
            except KeyError:
                return f"Error: Unknown provider '{provider_name}'. Supported: local, openai, gemini, groq, anthropic."

            if api_key:
                if provider_name not in self.providers_config:
                    self.providers_config[provider_name] = {}
                self.providers_config[provider_name]["api_key"] = api_key
                
                # Update environment variable for immediate effect
                env_var_map = {
                    "openai": "OPENAI_API_KEY",
                    "gemini": "GEMINI_API_KEY",
                    "groq": "GROQ_API_KEY",
                    "anthropic": "ANTHROPIC_API_KEY"
                }
                if provider_name in env_var_map:
                    os.environ[env_var_map[provider_name]] = api_key

            self.default_provider = provider_enum
            
            # Reset circuit breaker for this provider
            self._circuit_breakers[provider_enum] = CircuitBreaker()
            
            return f"Success: Switched to {provider_enum.name}" + (" and updated API key." if api_key else ".")
            
        except Exception as e:
            logger.error(f"Configuration update failed: {e}")
            return f"Error updating configuration: {str(e)}"

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response from LLM with Circuit Breaker and Privacy protection"""
        try:
            # Privacy & Routing Logic
            if request.privacy_level != PrivacyLevel.PUBLIC:
                request.prompt = self.privacy_filter.sanitize(request.prompt, request.privacy_level)
            
            if request.provider != LLMProvider.LOCAL and not self.privacy_filter.is_safe_for_cloud(request.prompt, request.privacy_level):
                logger.warning("Sensitive data - Forcing Local LLM")
                request.provider = LLMProvider.LOCAL
            
            # Determine Provider
            provider = request.provider if request.provider != LLMProvider.FALLBACK else self.default_provider
            
            # Check Circuit Breaker
            cb = self._circuit_breakers.get(provider, self._circuit_breakers[LLMProvider.LOCAL])
            if not cb.can_execute():
                return LLMResponse(
                    text="[SYSTEM] LLM Circuit Breaker Open. Service unavailable.",
                    provider=provider.name,
                    error="Circuit Breaker Open",
                    confidence=0.0
                )

            # Dispatch
            response = None
            if provider == LLMProvider.LOCAL:
                response = await self._local_llm(request)
            elif provider == LLMProvider.GEMINI:
                response = await self._gemini_llm(request)
            elif provider == LLMProvider.OPENAI:
                response = await self._openai_llm(request)
            elif provider == LLMProvider.GROQ:
                response = await self._groq_llm(request)
            elif provider == LLMProvider.ANTHROPIC:
                response = await self._anthropic_llm(request)
            else:
                response = await self._fallback_llm(request)

            # Update Circuit Breaker State
            if response.error:
                cb.record_failure()
            else:
                cb.record_success()

            return response
                
        except Exception as e:
            logger.error(f"LLM Generation Critical Error: {e}")
            # If dispatch failed completely, record failure on the intended provider
            provider = request.provider if request.provider != LLMProvider.FALLBACK else self.default_provider
            self._circuit_breakers.get(provider).record_failure()
            return await self._try_ollama_fallback(request)

    # ==================== IMPLEMENTATIONS ====================

    async def _local_llm(self, request: LLMRequest) -> LLMResponse:
        """Generate using Ollama with DeepSeek Default"""
        try:
            import aiohttp
            config = self.providers_config.get("local", {})
            endpoint = config.get("endpoint", DEFAULT_OLLAMA_ENDPOINT)
            
            # Use configured default or the fallback constant
            model_to_use = self.default_local_model

            payload = {
                "model": model_to_use,
                "prompt": request.prompt,
                "stream": False,
                "options": {"temperature": request.temperature, "num_predict": request.max_tokens}
            }
            if request.system_prompt: payload["system"] = request.system_prompt

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(f"{endpoint}/api/generate", json=payload, timeout=60) as response:
                        if response.status == 200:
                            # FIX: Pass content_type=None to handle cases where Ollama returns text/plain but body is JSON
                            data = await response.json(content_type=None)
                            return LLMResponse(
                                text=data.get("response", ""),
                                provider="local_ollama",
                                confidence=1.0,
                                metadata={"model": model_to_use}
                            )
                        elif response.status == 404:
                            # 404 often means model not pulled
                            return LLMResponse(
                                text=f"[SYSTEM] Model '{model_to_use}' not found. Run `ollama pull {model_to_use}`", 
                                provider="local", 
                                error="Model missing"
                            )
                        else:
                            logger.error(f"Ollama Error {response.status}")
                            return LLMResponse(text=f"[SYSTEM] Ollama HTTP {response.status}", provider="local", error=f"HTTP {response.status}")
                            
                except aiohttp.ClientConnectorError:
                    return LLMResponse(
                        text=f"[SYSTEM] Connection Refused. Is Ollama running at {endpoint}?", 
                        provider="local", 
                        error="Connection Refused"
                    )
                except asyncio.TimeoutError:
                    return LLMResponse(text="[SYSTEM] Request Timed Out.", provider="local", error="Timeout")
                except Exception as e:
                    logger.error(f"Ollama Internal Logic Error: {e}")
                    return LLMResponse(text=f"[SYSTEM] Ollama Logic Error: {e}", provider="local", error=str(e))

        except Exception as e:
            logger.error(f"Local LLM Error: {e}")
            return LLMResponse(text=f"[SYSTEM] Local LLM Exception: {e}", provider="local", error=str(e))

    async def _gemini_llm(self, request: LLMRequest) -> LLMResponse:
        """Gemini with fallback"""
        try:
            import aiohttp
            config = self.providers_config.get("gemini", {})
            api_key = os.getenv("GEMINI_API_KEY") or config.get("api_key")
            if not api_key: return await self._fallback_llm(request)

            models = ["gemini-1.5-flash", "gemini-1.5-pro"]
            
            async with aiohttp.ClientSession() as session:
                for model in models:
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                        payload = {
                            "contents": [{"parts": [{"text": request.prompt}]}],
                            "generationConfig": {"temperature": request.temperature, "maxOutputTokens": request.max_tokens}
                        }
                        if request.system_prompt: payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}
                        
                        async with session.post(url, json=payload, timeout=30) as response:
                            if response.status == 200:
                                data = await response.json(content_type=None)
                                if "candidates" in data and data["candidates"]:
                                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                                    return LLMResponse(text=text, provider="gemini", confidence=0.95, metadata={"model": model})
                            elif response.status == 429: break 
                    except: continue
            return await self._fallback_llm(request)
        except: return await self._fallback_llm(request)

    async def _openai_llm(self, request: LLMRequest) -> LLMResponse:
        try:
            import aiohttp
            api_key = os.getenv("OPENAI_API_KEY") or self.providers_config.get("openai", {}).get("api_key")
            if not api_key: return await self._fallback_llm(request)
            
            payload = {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": request.prompt}]}
            if request.system_prompt: payload["messages"].insert(0, {"role": "system", "content": request.system_prompt})
            
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.openai.com/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {api_key}"}) as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        return LLMResponse(text=data["choices"][0]["message"]["content"], provider="openai", confidence=0.9)
            return await self._fallback_llm(request)
        except: return await self._fallback_llm(request)

    async def _groq_llm(self, request: LLMRequest) -> LLMResponse:
        try:
            import aiohttp
            api_key = os.getenv("GROQ_API_KEY") or self.providers_config.get("groq", {}).get("api_key")
            if not api_key: return await self._fallback_llm(request)
            
            payload = {"model": "llama3-70b-8192", "messages": [{"role": "user", "content": request.prompt}]}
            if request.system_prompt: payload["messages"].insert(0, {"role": "system", "content": request.system_prompt})
            
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {api_key}"}) as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        return LLMResponse(text=data["choices"][0]["message"]["content"], provider="groq", confidence=0.9)
            return await self._fallback_llm(request)
        except: return await self._fallback_llm(request)
        
    async def _anthropic_llm(self, request: LLMRequest) -> LLMResponse:
        try:
            import aiohttp
            api_key = os.getenv("ANTHROPIC_API_KEY") or self.providers_config.get("anthropic", {}).get("api_key")
            if not api_key: return await self._fallback_llm(request)
            
            # Prepare request for Gemini
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": request.prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": request.temperature,
                    "maxOutputTokens": request.max_tokens,
                }
            }
            
            # Add system instruction if provided
            if request.system_prompt:
                payload["systemInstruction"] = {
                    "parts": [{"text": request.system_prompt}]
                }
            
            # Make request to Gemini (using v1 API, not v1beta)
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.anthropic.com/v1/messages", json=payload, headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"}) as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        return LLMResponse(text=data["content"][0]["text"], provider="anthropic", confidence=0.9)
            return await self._fallback_llm(request)
        except: return await self._fallback_llm(request)

    async def _try_ollama_fallback(self, request: LLMRequest) -> LLMResponse:
        if request.provider == LLMProvider.LOCAL: return await self._fallback_llm(request)
        request.provider = LLMProvider.LOCAL
        return await self._local_llm(request)

    async def _fallback_llm(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text="[NO LLM] System offline. Please check Ollama (localhost:11434) or API Keys.", 
            provider="fallback", 
            confidence=0.0,
            error="Fallback Active"
        )

# ==================== GLOBAL INSTANCE ====================
_llm_gateway_instance: Optional[LLMGateway] = None

async def get_llm_gateway(config: Dict[str, Any] = None) -> LLMGateway:
    global _llm_gateway_instance
    if _llm_gateway_instance is None:
        _llm_gateway_instance = LLMGateway()
        # Safe default init with DeepSeek Cloud enforced
        default_config = {
            "enabled": True, 
            "default_provider": "local",
            "providers": {
                "local": {"model": DEFAULT_LOCAL_MODEL}
            }
        }
        await _llm_gateway_instance.initialize(config or default_config)
    return _llm_gateway_instance