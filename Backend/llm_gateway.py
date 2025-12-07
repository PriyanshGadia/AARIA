# // LLM_GATEWAY.PY
# // VERSION: 1.3.0 (Model Auto-Fix)
# // DESCRIPTION: LLM Gateway - Integrated OpenAI-Standard logic with Model Auto-Correction.
# // UPDATE NOTES: Updated Groq to llama-3.3-70b-versatile. Added intelligent model scanning for Local/Ollama to prevent 404s.

import asyncio
import json
import os
import re
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    LOCAL = "local"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    GROQ = "groq"
    FALLBACK = "fallback"

class PrivacyLevel(Enum):
    PUBLIC = "public"
    CONFIDENTIAL = "confidential"
    OWNER_ONLY = "owner_only"

# ==================== PRIVACY FILTER ====================
class PrivacyFilter:
    def __init__(self):
        self.patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "ip": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            "key": r'\b[A-Za-z0-9_-]{32,}\b',
        }
    
    def sanitize(self, text: str, privacy_level: PrivacyLevel) -> str:
        if privacy_level == PrivacyLevel.OWNER_ONLY: return "[REDACTED]"
        for p in self.patterns.values():
            text = re.sub(p, "[REDACTED]", text)
        return text

    def is_safe_for_cloud(self, text: str, privacy_level: PrivacyLevel) -> bool:
        return privacy_level != PrivacyLevel.OWNER_ONLY

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

# ==================== LLM GATEWAY ====================
class LLMGateway:
    def __init__(self):
        self.privacy_filter = PrivacyFilter()
        self.providers_config = {}
        self.enabled = False
        self.default_provider = LLMProvider.FALLBACK
        self.detected_local_model = None
        
    async def initialize(self, config: Dict[str, Any]) -> bool:
        try:
            self.enabled = config.get("enabled", False)
            self.providers_config = config.get("providers", {})
            
            # Detect Providers (Priority: Config -> Env)
            available = {}
            
            # 1. Smart Local Ollama Check
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    # Check /api/tags to get ACTUAL installed models
                    async with session.get("http://localhost:11434/api/tags", timeout=2) as r:
                        if r.status == 200:
                            data = await r.json()
                            models = [m['name'] for m in data.get('models', [])]
                            
                            # Find best match
                            requested = self.providers_config.get('local', {}).get('model', 'llama3:latest')
                            
                            if requested in models:
                                self.detected_local_model = requested
                            else:
                                # Auto-correct to what is actually installed
                                # Priority: llama3.x -> llama3 -> llama2 -> first available
                                best_match = next((m for m in models if "llama3." in m), 
                                             next((m for m in models if "llama3" in m), 
                                             next((m for m in models if "llama2" in m), 
                                             models[0] if models else None)))
                                
                                if best_match:
                                    logger.warning(f"Requested '{requested}' not found. Auto-switching to '{best_match}'")
                                    self.detected_local_model = best_match
                                    
                            available["local"] = f"Ollama ({self.detected_local_model})"
            except Exception as e: 
                logger.debug(f"Ollama check failed: {e}")

            # 2. Check Cloud Keys
            if os.getenv("GEMINI_API_KEY"): available["gemini"] = "Gemini"
            if os.getenv("GROQ_API_KEY"): available["groq"] = "Groq"
            if os.getenv("OPENAI_API_KEY"): available["openai"] = "OpenAI"

            # 3. Set Default
            req = config.get("default_provider", "local").lower()
            if req == "local" and "local" in available:
                self.default_provider = LLMProvider.LOCAL
            elif req in available:
                self.default_provider = LLMProvider(req)
            elif available:
                self.default_provider = LLMProvider(list(available.keys())[0])
            else:
                self.default_provider = LLMProvider.FALLBACK

            logger.info(f"LLM Gateway Initialized. Active: {self.default_provider.value}")
            if self.default_provider == LLMProvider.LOCAL:
                logger.info(f"Using Local Model: {self.detected_local_model}")
                
            return True
        except Exception as e:
            logger.error(f"Gateway init failed: {e}")
            return False

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Route requests with automatic failover"""
        # Privacy Check
        if request.provider != LLMProvider.LOCAL and not self.privacy_filter.is_safe_for_cloud(request.prompt, request.privacy_level):
            request.provider = LLMProvider.LOCAL

        # Try Primary
        response = await self._route_request(request.provider, request)
        
        # Automatic Failover (Local -> Cloud)
        if response.provider == "fallback" and request.provider == LLMProvider.LOCAL:
            if os.getenv("GROQ_API_KEY"):
                logger.warning("Local failed. Failover to Groq.")
                return await self._route_request(LLMProvider.GROQ, request)
            elif os.getenv("GEMINI_API_KEY"):
                logger.warning("Local failed. Failover to Gemini.")
                return await self._route_request(LLMProvider.GEMINI, request)
                
        return response

    async def _route_request(self, provider: LLMProvider, request: LLMRequest) -> LLMResponse:
        if provider == LLMProvider.LOCAL: 
            # Use detected model or fallback to safe default
            model = self.detected_local_model or "llama3:latest"
            return await self._openai_standard_call(request, "http://localhost:11434/v1", model, "local")
            
        elif provider == LLMProvider.GROQ: 
            # UPDATED: Use new versatile model (llama3-70b-8192 is decommissioned)
            return await self._openai_standard_call(request, "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", "groq", os.getenv("GROQ_API_KEY"))
            
        elif provider == LLMProvider.OPENAI: 
            return await self._openai_standard_call(request, "https://api.openai.com/v1", "gpt-3.5-turbo", "openai", os.getenv("OPENAI_API_KEY"))
            
        elif provider == LLMProvider.GEMINI: 
            return await self._gemini_native_call(request)
            
        return await self._fallback_response(request)

    async def _openai_standard_call(self, request: LLMRequest, base_url: str, default_model: str, provider_name: str, api_key: str = "ollama") -> LLMResponse:
        """
        Unified handler for Ollama, Groq, and OpenAI.
        """
        try:
            import aiohttp
            
            # Determine model (config overrides default if present, unless it's local which is already resolved)
            config = self.providers_config.get(provider_name, {})
            model = default_model if provider_name == "local" else config.get("model", default_model)

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

            payload = {
                "model": model,
                "messages": messages,
                "temperature": float(request.temperature), # Strict typing
                "max_tokens": int(request.max_tokens),     # Strict typing
                "stream": False
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=45) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = data["choices"][0]["message"]["content"]
                        tokens = data.get("usage", {}).get("total_tokens", 0)
                        return LLMResponse(text=text, provider=provider_name, tokens_used=tokens, confidence=1.0)
                    else:
                        err = await resp.text()
                        logger.error(f"{provider_name} Error {resp.status}: {err}")
                        return await self._fallback_response(request)
        except Exception as e:
            logger.error(f"{provider_name} Exception: {e}")
            return await self._fallback_response(request)

    async def _gemini_native_call(self, request: LLMRequest) -> LLMResponse:
        """Robust Gemini implementation"""
        try:
            import aiohttp
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key: return await self._fallback_response(request)

            models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
            
            async with aiohttp.ClientSession() as session:
                for model in models:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                    payload = {
                        "contents": [{"parts": [{"text": request.prompt}]}],
                        "generationConfig": {"temperature": request.temperature, "maxOutputTokens": request.max_tokens}
                    }
                    if request.system_prompt:
                        payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}
                    
                    try:
                        async with session.post(url, json=payload, timeout=30) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                text = data["candidates"][0]["content"]["parts"][0]["text"]
                                return LLMResponse(text=text, provider="gemini", confidence=0.9, metadata={"model": model})
                    except: continue
            
            return await self._fallback_response(request)
        except: return await self._fallback_response(request)

    async def _fallback_response(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text="[SYSTEM NOTICE] No LLM available. Please check connections or keys.",
            provider="fallback",
            confidence=0.0
        )

# Global Instance
_gateway = None
async def get_llm_gateway(config=None):
    global _gateway
    if not _gateway:
        _gateway = LLMGateway()
        if config: await _gateway.initialize(config)
    return _gateway