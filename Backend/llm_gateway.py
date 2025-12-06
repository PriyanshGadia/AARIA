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
import logging

logger = logging.getLogger(__name__)

# ==================== LLM PROVIDER TYPES ====================
class LLMProvider(Enum):
    """Supported LLM providers"""
    LOCAL = "local"           # Local models (Ollama, LLaMA)
    OPENAI = "openai"         # OpenAI GPT models
    ANTHROPIC = "anthropic"   # Claude models
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
        
        Args:
            config: LLM configuration dictionary
            
        Returns:
            bool: True if successful
        """
        try:
            self.enabled = config.get("enabled", False)
            self.default_provider = LLMProvider[config.get("default_provider", "FALLBACK").upper()]
            self.providers_config = config.get("providers", {})
            
            logger.info(f"LLM Gateway initialized: enabled={self.enabled}, default={self.default_provider.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize LLM Gateway: {e}")
            return False
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response from LLM with privacy filtering
        
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
                return await self._openai_llm(request)
            elif request.provider == LLMProvider.ANTHROPIC:
                return await self._anthropic_llm(request)
            else:
                return await self._fallback_llm(request)
                
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            # Fallback on error
            return await self._fallback_llm(request)
    
    async def _local_llm(self, request: LLMRequest) -> LLMResponse:
        """Generate response using local LLM (Ollama)"""
        try:
            import aiohttp
            
            ollama_config = self.providers_config.get("local", {})
            endpoint = ollama_config.get("endpoint", "http://localhost:11434")
            model = ollama_config.get("model", "llama2")
            
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
    
    async def _anthropic_llm(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Anthropic Claude API"""
        try:
            import aiohttp
            
            anthropic_config = self.providers_config.get("anthropic", {})
            api_key = os.getenv("ANTHROPIC_API_KEY") or anthropic_config.get("api_key")
            model = anthropic_config.get("model", "claude-3-sonnet-20240229")
            
            if not api_key:
                logger.warning("Anthropic API key not found, using fallback")
                return await self._fallback_llm(request)
            
            # Prepare request
            payload = {
                "model": model,
                "max_tokens": request.max_tokens,
                "messages": [{"role": "user", "content": request.prompt}],
                "temperature": request.temperature
            }
            
            if request.system_prompt:
                payload["system"] = request.system_prompt
            
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            
            # Make request to Anthropic
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    json=payload,
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
                        
                        # Update token usage
                        self.token_usage["total"] += tokens
                        self.token_usage["today"] += tokens
                        
                        return LLMResponse(
                            text=data["content"][0]["text"],
                            provider="anthropic",
                            tokens_used=tokens,
                            confidence=0.9,
                            metadata={"model": model, "stop_reason": data.get("stop_reason")}
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"Anthropic request failed: {response.status} - {error_text}")
                        return await self._fallback_llm(request)
                        
        except Exception as e:
            logger.warning(f"Anthropic LLM failed: {e}. Using fallback.")
            return await self._fallback_llm(request)
    
    async def _fallback_llm(self, request: LLMRequest) -> LLMResponse:
        """
        MINIMAL FALLBACK - NOT REAL AI
        
        This is a placeholder that provides a generic response and clear instructions
        for enabling actual AI capabilities. No hardcoded responses or if-else logic.
        
        TO ENABLE REAL AI:
        1. Install Ollama: curl https://ollama.ai/install.sh | sh
        2. Pull a model: ollama pull llama2
        3. Restart AARIA
        
        OR use cloud LLM: export OPENAI_API_KEY='your-key'
        """
        
        # Extract basic information without hardcoding responses
        context = request.context or {}
        intent = context.get("intent", "unknown")
        
        # Generate a response that clearly indicates limitations
        response = (
            f"[NO LLM ACTIVE] I detected your message (intent: {intent}). "
            "However, I'm currently operating without a language model, so I cannot provide intelligent responses. "
            "\n\nTO ENABLE REAL AI RESPONSES:\n"
            "• Install Ollama (FREE, LOCAL): curl https://ollama.ai/install.sh | sh && ollama pull llama2\n"
            "• Or use Cloud AI (PAID): export OPENAI_API_KEY='your-key'\n"
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
                "instructions": "curl https://ollama.ai/install.sh | sh && ollama pull llama2"
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
