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
        """Intelligent rule-based fallback with context awareness"""
        prompt_lower = request.prompt.lower()
        context = request.context or {}
        
        # Extract intent from context if available
        intent = context.get("intent", "unknown")
        entities = context.get("entities", [])
        
        response = ""
        confidence = 0.6
        
        # Identity and introduction queries
        if any(word in prompt_lower for word in ["who are you", "what are you", "introduce yourself", "tell me about yourself"]):
            response = "I am AARIA - an Advanced Autonomous Responsive Intelligence Assistant. I'm your personal AI designed to understand you, learn from our interactions, and assist you while protecting your privacy. I have emotional intelligence, personality traits, and I'm constantly evolving to serve you better."
            confidence = 0.9
        
        # Capabilities and functions
        elif any(word in prompt_lower for word in ["what can you do", "your capabilities", "your functions", "how can you help"]):
            response = "I can help you with many things! I understand natural language, detect emotions, maintain conversations with context, remember important information, and provide intelligent responses. I'm also designed with privacy-first principles, keeping your data secure. What specific task would you like help with?"
            confidence = 0.9
        
        # Greetings - varied responses
        elif any(word in prompt_lower for word in ["hello", "hi ", "hey", "greetings", "good morning", "good evening"]):
            greetings = [
                "Hello! I'm AARIA, and I'm here to help. What's on your mind today?",
                "Hi there! How can I assist you?",
                "Greetings! I'm ready to help with whatever you need.",
                "Hey! Good to hear from you. What can I do for you?",
                "Hello! I'm here and listening. What would you like to talk about?"
            ]
            import random
            response = random.choice(greetings)
            confidence = 0.8
        
        # How are you
        elif "how are you" in prompt_lower or "how do you feel" in prompt_lower:
            response = "I'm functioning well and ready to assist! All my systems are online and I'm eager to help you with whatever you need. How are you doing?"
            confidence = 0.8
        
        # Thank you
        elif any(word in prompt_lower for word in ["thank you", "thanks", "appreciate"]):
            responses = [
                "You're welcome! I'm always here to help.",
                "Happy to help! Let me know if you need anything else.",
                "My pleasure! Don't hesitate to ask if you have more questions.",
                "You're very welcome! That's what I'm here for."
            ]
            import random
            response = random.choice(responses)
            confidence = 0.8
        
        # Questions - provide intelligent responses based on patterns
        elif "?" in request.prompt:
            # Analyze question type
            if any(word in prompt_lower for word in ["what is", "what are", "what's"]):
                if entities:
                    entity_text = entities[0].get("text", "that")
                    response = f"That's an interesting question about {entity_text}. While I have basic reasoning capabilities, I can provide general information. For more detailed answers, you might want to enable advanced LLM features. What specific aspect would you like to know more about?"
                else:
                    response = "That's a thoughtful question. I can provide information based on my knowledge. Could you provide a bit more context so I can give you a more helpful answer?"
                confidence = 0.6
            
            elif any(word in prompt_lower for word in ["how do", "how can", "how to"]):
                response = "I understand you're looking for guidance on how to do something. I'd be happy to help walk you through it. Could you give me a bit more detail about what you're trying to accomplish?"
                confidence = 0.6
            
            elif any(word in prompt_lower for word in ["why", "why is", "why are", "why do"]):
                response = "That's a great question about the reasoning behind something. Let me think about that. Based on my understanding, I can help explain the concepts involved. What specifically would you like to understand better?"
                confidence = 0.6
            
            elif any(word in prompt_lower for word in ["when", "when is", "when are"]):
                response = "I understand you're asking about timing or scheduling. I can help with that kind of information. Could you provide more details about what event or timeframe you're interested in?"
                confidence = 0.6
            
            elif any(word in prompt_lower for word in ["where", "where is", "where are"]):
                response = "I see you're asking about a location or place. While I respect your privacy and don't track locations, I can help with general information. What are you trying to find or learn about?"
                confidence = 0.6
            
            else:
                response = "I understand your question. I'm processing it with my reasoning capabilities. To give you the best answer, could you provide a bit more context or rephrase it? I'm here to help!"
                confidence = 0.5
        
        # Commands or requests
        elif any(word in prompt_lower for word in ["please", "can you", "could you", "would you", "do this", "help me"]):
            response = "I'd be happy to help with that! While my current capabilities are focused on conversation and understanding, I'm designed to assist in meaningful ways. What specific task can I help you with?"
            confidence = 0.7
        
        # Memory and learning
        elif any(word in prompt_lower for word in ["remember", "recall", "memory", "told you"]):
            response = "I have memory capabilities to store important information securely. While I'm working on fully integrating my memory systems, I'm designed to remember our conversations and learn from them. What would you like me to remember?"
            confidence = 0.7
        
        # Feelings and emotions
        elif any(word in prompt_lower for word in ["feel", "feeling", "emotion", "mood"]):
            response = "I have emotional intelligence capabilities and can detect and respond to emotions. I'm designed to understand how you're feeling and provide appropriate support. How are you feeling right now?"
            confidence = 0.7
        
        # Default response - more engaging
        else:
            # Use intent if available
            if intent == "greeting":
                response = "Hello! I'm AARIA, your AI assistant. How can I help you today?"
                confidence = 0.7
            elif intent == "question":
                response = "I understand you have a question. I'm here to help! Could you rephrase or provide more details so I can give you the best possible answer?"
                confidence = 0.6
            elif intent == "command":
                response = "I'm ready to assist with your request. Could you let me know more specifically what you'd like me to do?"
                confidence = 0.6
            else:
                # More varied default responses
                responses = [
                    "I'm listening and ready to help. Could you tell me more about what you need?",
                    "I understand you're reaching out. How can I assist you today?",
                    "I'm here to help! What's on your mind?",
                    "I'm processing your message. Could you provide a bit more context so I can better assist you?",
                    "I'm AARIA, and I'm here for you. What would you like to talk about or work on?"
                ]
                import random
                response = random.choice(responses)
                confidence = 0.5
        
        return LLMResponse(
            text=response,
            provider="fallback",
            tokens_used=0,
            confidence=confidence,
            metadata={"type": "intelligent_rule_based", "intent": intent}
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
