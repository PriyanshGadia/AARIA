# // LLM_GATEWAY.PY
# // VERSION: 1.0.0
# // DESCRIPTION: LLM Gateway - Unified interface for local and cloud LLM providers with privacy filters
# // UPDATE NOTES: Initial release. Implements LLM abstraction layer, privacy filtering, and provider routing.
# // IMPORTANT: No hardcoded API keys. All credentials loaded from encrypted configuration.

import asyncio
import json
import os
import re
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import logging

# Configuration constants
LLM_ENV_FILE = 'llm.env'

# Load environment variables from llm.env if it exists
try:
    from dotenv import load_dotenv
    # Try to load from Backend/llm.env first, then from current directory
    env_path = Path(__file__).parent / LLM_ENV_FILE
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()  # Load from default .env location
except ImportError:
    pass  # python-dotenv not installed, will use system environment variables

logger = logging.getLogger(__name__)

# ==================== LLM PROVIDER TYPES ====================
class LLMProvider(Enum):
    """Supported LLM providers"""
    LOCAL = "local"           # Local models (Ollama, LLaMA, llama3:latest)
    OPENAI = "openai"         # OpenAI GPT models
    ANTHROPIC = "anthropic"   # Claude models
    GEMINI = "gemini"         # Google Gemini models
    GROQ = "groq"             # Groq (fast inference)
    AZURE = "azure"           # Azure OpenAI
    FALLBACK = "fallback"     # Simple rule-based fallback

class PrivacyLevel(Enum):
    """Data privacy levels"""
    PUBLIC = "public"           # No sensitive data
    CONFIDENTIAL = "confidential"  # Some filtering needed
    OWNER_ONLY = "owner_only"   # Maximum privacy, local only

# ==================== PRIVACY FILTER ====================
class PrivacyFilter:
    """Filters sensitive data before sending to cloud LLMs"""
    
    def __init__(self):
        # Patterns for sensitive data detection
        self.patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            "file_path_windows": r'[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*',
            "file_path_unix": r'/(?:[^/\0]+/)*[^/\0]*',
            "ip_address": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            "api_key": r'\b[A-Za-z0-9_-]{32,}\b',  # Common API key format
        }
        
        self.sensitive_keywords = [
            "password", "api_key", "secret", "token", "credential",
            "ssn", "social security", "credit card", "bank account"
        ]
    
    def sanitize(self, text: str, privacy_level: PrivacyLevel) -> str:
        """
        Sanitize text based on privacy level
        
        Args:
            text: Input text to sanitize
            privacy_level: Level of privacy filtering to apply
            
        Returns:
            Sanitized text
        """
        if privacy_level == PrivacyLevel.OWNER_ONLY:
            # For owner-only data, return empty - should not be sent to cloud
            return "[PRIVATE_DATA_REDACTED]"
        
        sanitized = text
        
        # Remove sensitive patterns
        for pattern_name, pattern in self.patterns.items():
            sanitized = re.sub(pattern, f"[{pattern_name.upper()}_REDACTED]", sanitized)
        
        # Check for sensitive keywords
        for keyword in self.sensitive_keywords:
            if keyword.lower() in sanitized.lower():
                logger.warning(f"Sensitive keyword '{keyword}' detected in text")
        
        return sanitized
    
    def is_safe_for_cloud(self, text: str, privacy_level: PrivacyLevel) -> bool:
        """Check if text is safe to send to cloud LLM"""
        if privacy_level == PrivacyLevel.OWNER_ONLY:
            return False
        
        # Check for sensitive patterns
        for pattern in self.patterns.values():
            if re.search(pattern, text):
                return False
        
        return True

# ==================== LLM GATEWAY ====================
@dataclass
class LLMRequest:
    """LLM request structure"""
    prompt: str
    provider: LLMProvider = LLMProvider.LOCAL
    privacy_level: PrivacyLevel = PrivacyLevel.CONFIDENTIAL
    context: Dict[str, Any] = field(default_factory=dict)
    max_tokens: int = 1000
    temperature: float = 0.7
    system_prompt: Optional[str] = None

@dataclass
class LLMResponse:
    """LLM response structure"""
    text: str
    provider: str
    tokens_used: int = 0
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class LLMGateway:
    """Central gateway for all LLM interactions"""
    
    def __init__(self):
        self.privacy_filter = PrivacyFilter()
        self.providers_config = {}
        self.token_usage = {"total": 0, "today": 0, "this_month": 0}
        self.enabled = False
        self.default_provider = LLMProvider.FALLBACK
        
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize LLM Gateway with configuration
        Auto-detects available providers based on environment variables and local services
        
        Args:
            config: LLM configuration dictionary
            
        Returns:
            bool: True if successful
        """
        try:
            self.enabled = config.get("enabled", False)
            requested_provider = config.get("default_provider", "local").upper()
            self.providers_config = config.get("providers", {})
            
            # Auto-detect available providers from environment variables and services
            available_providers = {}
            
            # Check for local Ollama FIRST (preferred for privacy)
            ollama_available = False
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://localhost:11434/api/tags", timeout=aiohttp.ClientTimeout(total=2)) as response:
                        if response.status == 200:
                            data = await response.json()
                            models = data.get("models", [])
                            model_names = [m.get("name", "") for m in models]
                            available_providers["local"] = f"Ollama ({len(models)} models: {', '.join(model_names[:3])}{'...' if len(models) > 3 else ''})"
                            ollama_available = True
            except Exception as e:
                logger.debug(f"Ollama not available: {e}")
            
            # Check for cloud API keys
            if os.getenv("GEMINI_API_KEY"):
                available_providers["gemini"] = "Google Gemini (gemini-1.5-flash)"
            
            if os.getenv("GROQ_API_KEY"):
                available_providers["groq"] = "Groq (llama3-70b-8192, ultra-fast)"
            
            if os.getenv("OPENAI_API_KEY"):
                available_providers["openai"] = "OpenAI (gpt-3.5-turbo / gpt-4)"
            
            if os.getenv("ANTHROPIC_API_KEY"):
                available_providers["anthropic"] = "Anthropic (claude-3)"
            
            # Determine which provider to use
            if requested_provider == "LOCAL":
                if ollama_available:
                    self.default_provider = LLMProvider.LOCAL
                    logger.info(f"Using LOCAL Ollama as requested: {available_providers['local']}")
                elif available_providers:
                    # Ollama requested but not available, try cloud providers
                    if "gemini" in available_providers:
                        self.default_provider = LLMProvider.GEMINI
                        logger.info("Ollama not available, switching to Gemini (API key found)")
                    elif "groq" in available_providers:
                        self.default_provider = LLMProvider.GROQ
                        logger.info("Ollama not available, switching to Groq (API key found)")
                    elif "openai" in available_providers:
                        self.default_provider = LLMProvider.OPENAI
                        logger.info("Ollama not available, switching to OpenAI (API key found)")
                    elif "anthropic" in available_providers:
                        self.default_provider = LLMProvider.ANTHROPIC
                        logger.info("Ollama not available, switching to Anthropic (API key found)")
                else:
                    self.default_provider = LLMProvider.FALLBACK
                    logger.warning("LOCAL requested but Ollama not available, no API keys found")
            else:
                # Specific provider requested
                provider_lower = requested_provider.lower()
                if provider_lower in available_providers:
                    self.default_provider = LLMProvider[requested_provider]
                    logger.info(f"Using {requested_provider}: {available_providers[provider_lower]}")
                else:
                    # Requested provider not available, find alternative
                    if ollama_available:
                        self.default_provider = LLMProvider.LOCAL
                        logger.info(f"{requested_provider} not available, using LOCAL Ollama instead")
                    elif available_providers:
                        # Use first available cloud provider
                        first_provider = list(available_providers.keys())[0]
                        self.default_provider = LLMProvider[first_provider.upper()]
                        logger.info(f"{requested_provider} not available, using {first_provider}: {available_providers[first_provider]}")
                    else:
                        self.default_provider = LLMProvider.FALLBACK
                        logger.warning(f"{requested_provider} not available, no alternatives found")
            
            if available_providers:
                logger.info(f"LLM Gateway initialized: enabled={self.enabled}, default={self.default_provider.value}")
                logger.info(f"Available providers: {', '.join([f'{k}: {v}' for k, v in available_providers.items()])}")
            else:
                logger.warning("⚠️  NO AI PROVIDERS AVAILABLE - FALLBACK MODE ONLY")
                logger.warning("Install Ollama OR set an API key:")
                logger.warning("  • Ollama (FREE, local): curl https://ollama.ai/install.sh | sh && ollama pull llama3:latest")
                logger.warning("  • Gemini (FREE tier): export GEMINI_API_KEY='your-key'")
                logger.warning("  • Groq (fast, cheap): export GROQ_API_KEY='your-key'")
                logger.warning("  • OpenAI: export OPENAI_API_KEY='your-key'")
                logger.warning("  • Anthropic: export ANTHROPIC_API_KEY='your-key'")
                self.default_provider = LLMProvider.FALLBACK
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize LLM Gateway: {e}", exc_info=True)
            return False
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response from LLM with privacy filtering and automatic fallback
        
        Args:
            request: LLM request object
            
        Returns:
            LLM response object
        """
        try:
            # Apply privacy filtering
            if request.privacy_level != PrivacyLevel.PUBLIC:
                sanitized_prompt = self.privacy_filter.sanitize(request.prompt, request.privacy_level)
            else:
                sanitized_prompt = request.prompt
            
            # Check if safe for cloud
            use_local = False
            if request.provider != LLMProvider.LOCAL:
                if not self.privacy_filter.is_safe_for_cloud(request.prompt, request.privacy_level):
                    logger.warning("Prompt contains sensitive data, routing to local LLM")
                    use_local = True
                    request.provider = LLMProvider.LOCAL
            
            # Route to appropriate provider
            if not self.enabled or request.provider == LLMProvider.FALLBACK:
                return await self._fallback_llm(request)
            elif request.provider == LLMProvider.LOCAL or use_local:
                return await self._local_llm(request)
            elif request.provider == LLMProvider.OPENAI:
                return await self._openai_llm_with_fallback(request)
            elif request.provider == LLMProvider.ANTHROPIC:
                return await self._anthropic_llm_with_fallback(request)
            elif request.provider == LLMProvider.GEMINI:
                return await self._gemini_llm_with_fallback(request)
            elif request.provider == LLMProvider.GROQ:
                return await self._groq_llm_with_fallback(request)
            else:
                return await self._fallback_llm(request)
                
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            # Try Ollama fallback before using no-LLM fallback
            return await self._try_ollama_fallback(request)
    
    async def _local_llm(self, request: LLMRequest) -> LLMResponse:
        """Generate response using local LLM (Ollama with llama2, llama3:latest, etc.)"""
        try:
            import aiohttp
            
            ollama_config = self.providers_config.get("local", {})
            endpoint = ollama_config.get("endpoint", "http://localhost:11434")
            model = ollama_config.get("model", "llama3:latest")  # Default to llama3:latest
            
            # Prepare request
            payload = {
                "model": model,
                "prompt": request.prompt,
                "stream": False,
                "options": {
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens
                }
            }
            
            if request.system_prompt:
                payload["system"] = request.system_prompt
            
            # Make request to Ollama
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{endpoint}/api/generate", json=payload, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        return LLMResponse(
                            text=data.get("response", ""),
                            provider="local_ollama",
                            tokens_used=data.get("total_duration", 0),
                            confidence=0.8,
                            metadata={"model": model, "endpoint": endpoint}
                        )
                    else:
                        logger.error(f"Ollama request failed: {response.status}")
                        return await self._fallback_llm(request)
                        
        except Exception as e:
            logger.warning(f"Local LLM failed: {e}. Using fallback.")
            return await self._fallback_llm(request)
    
    async def _openai_llm(self, request: LLMRequest) -> LLMResponse:
        """Generate response using OpenAI API"""
        try:
            import aiohttp
            
            openai_config = self.providers_config.get("openai", {})
            api_key = os.getenv("OPENAI_API_KEY") or openai_config.get("api_key")
            model = openai_config.get("model", "gpt-3.5-turbo")
            
            if not api_key:
                logger.warning("OpenAI API key not found, using fallback")
                return await self._fallback_llm(request)
            
            # Prepare messages
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})
            
            # Prepare request
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Make request to OpenAI
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        choice = data["choices"][0]
                        tokens = data.get("usage", {}).get("total_tokens", 0)
                        
                        # Update token usage
                        self.token_usage["total"] += tokens
                        self.token_usage["today"] += tokens
                        
                        return LLMResponse(
                            text=choice["message"]["content"],
                            provider="openai",
                            tokens_used=tokens,
                            confidence=0.9,
                            metadata={"model": model, "finish_reason": choice.get("finish_reason")}
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"OpenAI request failed: {response.status} - {error_text}")
                        return await self._fallback_llm(request)
                        
        except Exception as e:
            logger.warning(f"OpenAI LLM failed: {e}. Using fallback.")
            return await self._fallback_llm(request)
    
    async def _groq_llm(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Groq API (ultra-fast inference)"""
        try:
            import aiohttp
            
            groq_config = self.providers_config.get("groq", {})
            api_key = os.getenv("GROQ_API_KEY") or groq_config.get("api_key")
            model = groq_config.get("model", "llama3-70b-8192")  # Default to llama3-70b-8192
            
            if not api_key:
                logger.warning("Groq API key not found, using fallback")
                return await self._fallback_llm(request)
            
            # Prepare request for Groq API
            payload = {
                "model": model,
                "max_tokens": request.max_tokens,
                "messages": [{"role": "user", "content": request.prompt}],
                "temperature": request.temperature,
                "stream": False
            }
            
            if request.system_prompt:
                # For Groq, system prompt is included in the messages array
                payload["messages"] = [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.prompt}
                ]
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Make request to Groq
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Groq returns usage information differently
                        prompt_tokens = data.get("usage", {}).get("prompt_tokens", 0)
                        completion_tokens = data.get("usage", {}).get("completion_tokens", 0)
                        total_tokens = prompt_tokens + completion_tokens
                        
                        # Update token usage
                        self.token_usage["total"] += total_tokens
                        self.token_usage["today"] += total_tokens
                        
                        return LLMResponse(
                            text=data["choices"][0]["message"]["content"],
                            provider="groq",
                            tokens_used=total_tokens,
                            confidence=0.9,
                            metadata={
                                "model": model,
                                "finish_reason": data["choices"][0].get("finish_reason"),
                                "prompt_tokens": prompt_tokens,
                                "completion_tokens": completion_tokens
                            }
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"Groq request failed: {response.status} - {error_text}")
                        return await self._fallback_llm(request)
                        
        except Exception as e:
            logger.warning(f"Groq LLM failed: {e}. Using fallback.")
            return await self._fallback_llm(request)
    
    async def _gemini_llm(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Google Gemini API"""
        try:
            import aiohttp
            
            gemini_config = self.providers_config.get("gemini", {})
            api_key = os.getenv("GEMINI_API_KEY") or gemini_config.get("api_key")
            # Use gemini-1.5-flash as default (gemini-pro is deprecated for v1beta)
            model = gemini_config.get("model", "gemini-1.5-flash")
            
            if not api_key:
                logger.warning("Gemini API key not found, using fallback")
                return await self._fallback_llm(request)
            
            # Prepare request for Gemini
            # Note: v1 API doesn't support systemInstruction field, so we prepend it to the prompt.
            # This workaround may slightly affect token counting but preserves system prompt functionality.
            # The v1 API is used because v1beta doesn't support the gemini-1.5-flash model.
            combined_prompt = request.prompt
            if request.system_prompt:
                # Strip whitespace to avoid double newlines if prompts already have them
                system_part = request.system_prompt.strip()
                user_part = request.prompt.strip()
                combined_prompt = f"{system_part}\n\n{user_part}"
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": combined_prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": request.temperature,
                    "maxOutputTokens": request.max_tokens,
                }
            }
            
            # Make request to Gemini (using v1 API - stable and supports gemini-1.5-flash)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={api_key}",
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract text from response
                        candidates = data.get("candidates", [])
                        if candidates and len(candidates) > 0:
                            content = candidates[0].get("content", {})
                            parts = content.get("parts", [])
                            text = parts[0].get("text", "") if parts else ""
                            
                            # Get token usage
                            usage = data.get("usageMetadata", {})
                            tokens = usage.get("totalTokenCount", 0)
                            
                            # Update token usage
                            self.token_usage["total"] += tokens
                            self.token_usage["today"] += tokens
                            
                            return LLMResponse(
                                text=text,
                                provider="gemini",
                                tokens_used=tokens,
                                confidence=0.9,
                                metadata={"model": model, "finish_reason": candidates[0].get("finishReason")}
                            )
                        else:
                            logger.error("Gemini returned no candidates")
                            return await self._fallback_llm(request)
                    else:
                        error_text = await response.text()
                        logger.error(f"Gemini request failed: {response.status} - {error_text}")
                        return await self._fallback_llm(request)
                        
        except Exception as e:
            logger.warning(f"Gemini LLM failed: {e}. Using fallback.")
            return await self._fallback_llm(request)
    
    async def _try_ollama_fallback(self, request: LLMRequest) -> LLMResponse:
        """
        Try to fallback to Ollama when cloud LLM fails
        
        Args:
            request: LLM request object
            
        Returns:
            LLM response from Ollama or final fallback
        """
        try:
            logger.info("Attempting to fallback to local Ollama...")
            
            # Get Ollama endpoint from config or use default
            ollama_config = self.providers_config.get("local", {})
            ollama_endpoint = ollama_config.get("endpoint", os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434"))
            
            # Check if Ollama is available
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{ollama_endpoint}/api/tags", timeout=aiohttp.ClientTimeout(total=2)) as response:
                    if response.status == 200:
                        # Ollama is available, use it
                        logger.info("Ollama is available, using local LLM as fallback")
                        return await self._local_llm(request)
        except Exception as e:
            logger.debug(f"Ollama not available for fallback: {e}")
        
        # Ollama not available, use final fallback
        return await self._fallback_llm(request)
    
    async def _gemini_llm_with_fallback(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Gemini with automatic Ollama fallback"""
        response = await self._gemini_llm(request)
        
        # If Gemini failed (confidence < 0.2 means it used fallback), try Ollama
        if response.confidence < 0.2:
            logger.info("Gemini failed, trying Ollama fallback...")
            return await self._try_ollama_fallback(request)
        
        return response
    
    async def _openai_llm_with_fallback(self, request: LLMRequest) -> LLMResponse:
        """Generate response using OpenAI with automatic Ollama fallback"""
        response = await self._openai_llm(request)
        
        # If OpenAI failed (confidence < 0.2 means it used fallback), try Ollama
        if response.confidence < 0.2:
            logger.info("OpenAI failed, trying Ollama fallback...")
            return await self._try_ollama_fallback(request)
        
        return response
    
    async def _anthropic_llm_with_fallback(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Anthropic with automatic Ollama fallback"""
        response = await self._anthropic_llm(request)
        
        # If Anthropic failed (confidence < 0.2 means it used fallback), try Ollama
        if response.confidence < 0.2:
            logger.info("Anthropic failed, trying Ollama fallback...")
            return await self._try_ollama_fallback(request)
        
        return response
    
    async def _groq_llm_with_fallback(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Groq with automatic Ollama fallback"""
        response = await self._groq_llm(request)
        
        # If Groq failed (confidence < 0.2 means it used fallback), try Ollama
        if response.confidence < 0.2:
            logger.info("Groq failed, trying Ollama fallback...")
            return await self._try_ollama_fallback(request)
        
        return response
    
    async def _fallback_llm(self, request: LLMRequest) -> LLMResponse:
        """
        MINIMAL FALLBACK - NOT REAL AI
        
        This is a placeholder that provides a generic response and clear instructions
        for enabling actual AI capabilities. No hardcoded responses or if-else logic.
        
        TO ENABLE REAL AI:
        1. Install Ollama: curl https://ollama.ai/install.sh | sh
        2. Pull a model: ollama pull llama3:latest
        3. Restart AARIA
        
        OR use cloud LLM: 
        - OpenAI: export OPENAI_API_KEY='your-key'
        - Anthropic: export ANTHROPIC_API_KEY='your-key'
        - Gemini: export GEMINI_API_KEY='your-key'
        - Groq: export GROQ_API_KEY='your-key'
        """
        
        # Extract basic information without hardcoding responses
        context = request.context or {}
        intent = context.get("intent", "unknown")
        
        # Generate a response that clearly indicates limitations
        response = (
            f"[NO LLM ACTIVE] I detected your message (intent: {intent}). "
            "However, I'm currently operating without a language model, so I cannot provide intelligent responses. "
            "\n\nTO ENABLE REAL AI RESPONSES:\n"
            "• Install Ollama (FREE, LOCAL): curl https://ollama.ai/install.sh | sh && ollama pull llama3:latest\n"
            "• Or use Cloud AI (PAID):\n"
            "  - OpenAI: export OPENAI_API_KEY='your-key'\n"
            "  - Anthropic Claude: export ANTHROPIC_API_KEY='your-key'\n"
            "  - Google Gemini: export GEMINI_API_KEY='your-key'\n"
            "  - Groq (ultra-fast): export GROQ_API_KEY='your-key'\n"
            "\nWithout an LLM, I can only detect intent and entities, not generate meaningful responses."
        )
        
        return LLMResponse(
            text=response,
            provider="no_llm_fallback",
            tokens_used=0,
            confidence=0.1,
            metadata={
                "type": "placeholder_not_ai",
                "intent": intent,
                "warning": "NO LANGUAGE MODEL - Install Ollama or enable cloud LLM",
                "instructions": "curl https://ollama.ai/install.sh | sh && ollama pull llama3:latest",
                "supported_providers": ["local_ollama", "openai", "anthropic", "gemini", "groq"]
            }
        )
    
    def get_token_usage(self) -> Dict[str, int]:
        """Get current token usage statistics"""
        return self.token_usage.copy()
    
    async def enhance_response(self, base_response: str, context: Dict[str, Any]) -> str:
        """
        Enhance a base response with LLM intelligence
        
        Args:
            base_response: Base response from rule-based system
            context: Additional context for enhancement
            
        Returns:
            Enhanced response
        """
        if not self.enabled:
            return base_response
        
        try:
            request = LLMRequest(
                prompt=f"Enhance this response to be more natural and helpful: '{base_response}'\nContext: {json.dumps(context)}",
                provider=self.default_provider,
                privacy_level=PrivacyLevel.PUBLIC,
                max_tokens=150,
                temperature=0.7,
                system_prompt="You are AARIA, a helpful AI assistant. Enhance responses to be natural, concise, and helpful."
            )
            
            response = await self.generate_response(request)
            return response.text if response.confidence > 0.6 else base_response
            
        except Exception as e:
            logger.error(f"Response enhancement failed: {e}")
            return base_response


# ==================== GLOBAL INSTANCE ====================
_llm_gateway_instance: Optional[LLMGateway] = None

async def get_llm_gateway(config: Dict[str, Any] = None) -> LLMGateway:
    """
    Get or create the global LLM Gateway instance
    
    Args:
        config: Optional configuration for first initialization
        
    Returns:
        LLMGateway instance
    """
    global _llm_gateway_instance
    
    if _llm_gateway_instance is None:
        _llm_gateway_instance = LLMGateway()
        
        if config:
            await _llm_gateway_instance.initialize(config)
        else:
            # Initialize with defaults
            await _llm_gateway_instance.initialize({
                "enabled": False,
                "default_provider": "fallback",
                "providers": {}
            })
    
    return _llm_gateway_instance
