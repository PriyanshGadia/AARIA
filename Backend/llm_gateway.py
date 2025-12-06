"""
AARIA - LLM Gateway v1.1
Primary Module: Unified interface for multiple LLM providers with environment-based API key detection
Update Notes: v1.1 - Added support for loading API keys from config/llm.env file
Security Level: API keys loaded from .env file or environment variables - never hardcoded
Architecture: Provider abstraction with automatic fallback and health checking
"""

import os
import logging
import asyncio
import json
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Import environment loader
try:
    from env_loader import load_llm_environment
except ImportError:
    # Fallback if env_loader not available
    def load_llm_environment():
        return {}

logger = logging.getLogger(__name__)

# ==================== PROVIDER TYPES ====================
class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    GROQ = "groq"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"

# ==================== PROVIDER INTERFACE ====================
@dataclass
class LLMResponse:
    """Standard response format from any LLM provider"""
    content: str
    provider: str
    model: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None

class LLMProviderInterface(ABC):
    """Abstract interface for LLM providers"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.available = False
        
    @abstractmethod
    async def generate(self, prompt: str, model: str, temperature: float = 0.7) -> LLMResponse:
        """Generate response from LLM"""
        pass
    
    @abstractmethod
    async def check_availability(self) -> bool:
        """Check if provider is available and configured"""
        pass

# ==================== OPENAI PROVIDER ====================
class OpenAIProvider(LLMProviderInterface):
    """OpenAI GPT provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.default_model = "gpt-3.5-turbo"
        
    async def check_availability(self) -> bool:
        """Check if OpenAI API key is configured"""
        self.available = self.api_key is not None and len(self.api_key) > 0
        if self.available:
            logger.info("OpenAI provider is available")
        else:
            logger.debug("OpenAI provider not available - no API key")
        return self.available
    
    async def generate(self, prompt: str, model: str = None, temperature: float = 0.7) -> LLMResponse:
        """Generate response using OpenAI API"""
        if not self.available:
            return LLMResponse(
                content="",
                provider="openai",
                model=model or self.default_model,
                success=False,
                error="OpenAI API key not configured"
            )
        
        try:
            # Import here to avoid dependency if not used
            import openai
            
            openai.api_key = self.api_key
            
            import time
            start = time.time()
            
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model=model or self.default_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
            
            latency = (time.time() - start) * 1000
            
            return LLMResponse(
                content=response.choices[0].message.content,
                provider="openai",
                model=model or self.default_model,
                tokens_used=response.usage.total_tokens,
                latency_ms=latency,
                success=True
            )
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {str(e)}")
            return LLMResponse(
                content="",
                provider="openai",
                model=model or self.default_model,
                success=False,
                error=str(e)
            )

# ==================== GROQ PROVIDER ====================
class GroqProvider(LLMProviderInterface):
    """Groq ultra-fast LLM provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.default_model = "llama3-70b-8192"
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        
    async def check_availability(self) -> bool:
        """Check if Groq API key is configured"""
        self.available = self.api_key is not None and len(self.api_key) > 0
        if self.available:
            logger.info("Groq provider is available (ultra-fast)")
        else:
            logger.debug("Groq provider not available - no API key")
        return self.available
    
    async def generate(self, prompt: str, model: str = None, temperature: float = 0.7) -> LLMResponse:
        """Generate response using Groq API"""
        if not self.available:
            return LLMResponse(
                content="",
                provider="groq",
                model=model or self.default_model,
                success=False,
                error="Groq API key not configured"
            )
        
        try:
            import aiohttp
            import time
            
            start = time.time()
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model or self.default_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        latency = (time.time() - start) * 1000
                        
                        return LLMResponse(
                            content=data["choices"][0]["message"]["content"],
                            provider="groq",
                            model=model or self.default_model,
                            tokens_used=data.get("usage", {}).get("total_tokens", 0),
                            latency_ms=latency,
                            success=True
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"Groq API error {response.status}: {error_text}")
                        return LLMResponse(
                            content="",
                            provider="groq",
                            model=model or self.default_model,
                            success=False,
                            error=f"HTTP {response.status}: {error_text}"
                        )
                        
        except Exception as e:
            logger.error(f"Groq generation failed: {str(e)}")
            return LLMResponse(
                content="",
                provider="groq",
                model=model or self.default_model,
                success=False,
                error=str(e)
            )

# ==================== GEMINI PROVIDER ====================
class GeminiProvider(LLMProviderInterface):
    """Google Gemini provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.default_model = "gemini-pro"
        
    async def check_availability(self) -> bool:
        """Check if Gemini API key is configured"""
        self.available = self.api_key is not None and len(self.api_key) > 0
        if self.available:
            logger.info("Google Gemini provider is available")
        else:
            logger.debug("Gemini provider not available - no API key")
        return self.available
    
    async def generate(self, prompt: str, model: str = None, temperature: float = 0.7) -> LLMResponse:
        """Generate response using Gemini API"""
        if not self.available:
            return LLMResponse(
                content="",
                provider="gemini",
                model=model or self.default_model,
                success=False,
                error="Gemini API key not configured"
            )
        
        try:
            import google.generativeai as genai
            import time
            
            genai.configure(api_key=self.api_key)
            model_obj = genai.GenerativeModel(model or self.default_model)
            
            start = time.time()
            response = await asyncio.to_thread(
                model_obj.generate_content,
                prompt
            )
            latency = (time.time() - start) * 1000
            
            return LLMResponse(
                content=response.text,
                provider="gemini",
                model=model or self.default_model,
                latency_ms=latency,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {str(e)}")
            return LLMResponse(
                content="",
                provider="gemini",
                model=model or self.default_model,
                success=False,
                error=str(e)
            )

# ==================== ANTHROPIC PROVIDER ====================
class AnthropicProvider(LLMProviderInterface):
    """Anthropic Claude provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.default_model = "claude-3-sonnet-20240229"
        
    async def check_availability(self) -> bool:
        """Check if Anthropic API key is configured"""
        self.available = self.api_key is not None and len(self.api_key) > 0
        if self.available:
            logger.info("Anthropic Claude provider is available")
        else:
            logger.debug("Anthropic provider not available - no API key")
        return self.available
    
    async def generate(self, prompt: str, model: str = None, temperature: float = 0.7) -> LLMResponse:
        """Generate response using Anthropic API"""
        if not self.available:
            return LLMResponse(
                content="",
                provider="anthropic",
                model=model or self.default_model,
                success=False,
                error="Anthropic API key not configured"
            )
        
        try:
            import anthropic
            import time
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            start = time.time()
            response = await asyncio.to_thread(
                client.messages.create,
                model=model or self.default_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
            latency = (time.time() - start) * 1000
            
            return LLMResponse(
                content=response.content[0].text,
                provider="anthropic",
                model=model or self.default_model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                latency_ms=latency,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Anthropic generation failed: {str(e)}")
            return LLMResponse(
                content="",
                provider="anthropic",
                model=model or self.default_model,
                success=False,
                error=str(e)
            )

# ==================== OLLAMA PROVIDER ====================
class OllamaProvider(LLMProviderInterface):
    """Local Ollama provider (no API key needed)"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.default_model = "llama3:latest"
        self.base_url = "http://localhost:11434"
        
    async def check_availability(self) -> bool:
        """Check if Ollama is running locally"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=2)) as response:
                    self.available = response.status == 200
                    if self.available:
                        data = await response.json()
                        models = [m["name"] for m in data.get("models", [])]
                        logger.info(f"Local Ollama is available with models: {', '.join(models)}")
                    return self.available
        except Exception as e:
            logger.debug(f"Ollama not available: {str(e)}")
            self.available = False
            return False
    
    async def generate(self, prompt: str, model: str = None, temperature: float = 0.7) -> LLMResponse:
        """Generate response using local Ollama"""
        if not self.available:
            return LLMResponse(
                content="",
                provider="ollama",
                model=model or self.default_model,
                success=False,
                error="Ollama not running locally. Install: curl https://ollama.ai/install.sh | sh"
            )
        
        try:
            import aiohttp
            import time
            
            start = time.time()
            
            payload = {
                "model": model or self.default_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        latency = (time.time() - start) * 1000
                        
                        return LLMResponse(
                            content=data["response"],
                            provider="ollama",
                            model=model or self.default_model,
                            latency_ms=latency,
                            success=True
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama error {response.status}: {error_text}")
                        return LLMResponse(
                            content="",
                            provider="ollama",
                            model=model or self.default_model,
                            success=False,
                            error=f"HTTP {response.status}: {error_text}"
                        )
                        
        except Exception as e:
            logger.error(f"Ollama generation failed: {str(e)}")
            return LLMResponse(
                content="",
                provider="ollama",
                model=model or self.default_model,
                success=False,
                error=str(e)
            )

# ==================== LLM GATEWAY ====================
class LLMGateway:
    """Unified gateway for multiple LLM providers with automatic environment variable detection"""
    
    def __init__(self):
        self.providers: Dict[str, LLMProviderInterface] = {}
        self.default_provider: Optional[str] = None
        self.fallback_order: List[str] = []
        
        # Load API keys from config/llm.env file first (if exists)
        logger.info("Loading LLM configuration...")
        env_vars = load_llm_environment()
        if env_vars:
            logger.info(f"✓ Loaded {len(env_vars)} API key(s) from config/llm.env")
        else:
            logger.debug("No config/llm.env file found, using system environment variables only")
        
        # Initialize providers by reading from environment variables
        self._initialize_providers()
        
    def _initialize_providers(self):
        """Initialize all providers by detecting API keys from environment variables"""
        logger.info("Detecting LLM providers from environment variables...")
        
        # OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.providers["openai"] = OpenAIProvider(openai_key)
            logger.info("✓ OpenAI API key detected")
        else:
            logger.debug("✗ OPENAI_API_KEY not found in environment")
        
        # Groq
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            self.providers["groq"] = GroqProvider(groq_key)
            logger.info("✓ Groq API key detected")
        else:
            logger.debug("✗ GROQ_API_KEY not found in environment")
        
        # Gemini
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key:
            self.providers["gemini"] = GeminiProvider(gemini_key)
            logger.info("✓ Gemini API key detected")
        else:
            logger.debug("✗ GEMINI_API_KEY not found in environment")
        
        # Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            self.providers["anthropic"] = AnthropicProvider(anthropic_key)
            logger.info("✓ Anthropic API key detected")
        else:
            logger.debug("✗ ANTHROPIC_API_KEY not found in environment")
        
        # Ollama (always available if running)
        self.providers["ollama"] = OllamaProvider()
        logger.debug("Ollama provider initialized (will check availability)")
        
    async def initialize(self):
        """Check availability of all providers"""
        logger.info("Checking availability of LLM providers...")
        
        available_providers = []
        
        for name, provider in self.providers.items():
            try:
                is_available = await provider.check_availability()
                if is_available:
                    available_providers.append(name)
            except Exception as e:
                logger.warning(f"Error checking {name} provider: {str(e)}")
        
        if not available_providers:
            logger.warning("⚠️  No LLM providers available!")
            logger.warning("To enable AI responses, set one of these environment variables:")
            logger.warning("  • OPENAI_API_KEY")
            logger.warning("  • GROQ_API_KEY")
            logger.warning("  • GEMINI_API_KEY or GOOGLE_API_KEY")
            logger.warning("  • ANTHROPIC_API_KEY")
            logger.warning("  • Or install Ollama: curl https://ollama.ai/install.sh | sh")
            return False
        
        # Set default and fallback order
        # Priority: Groq (fastest) > OpenAI > Gemini > Anthropic > Ollama
        priority_order = ["groq", "openai", "gemini", "anthropic", "ollama"]
        self.fallback_order = [p for p in priority_order if p in available_providers]
        self.default_provider = self.fallback_order[0] if self.fallback_order else None
        
        logger.info(f"✓ {len(available_providers)} LLM provider(s) available: {', '.join(available_providers)}")
        logger.info(f"✓ Default provider: {self.default_provider}")
        logger.info(f"✓ Fallback order: {' → '.join(self.fallback_order)}")
        
        return True
    
    async def generate(self, prompt: str, provider: Optional[str] = None, 
                      model: Optional[str] = None, temperature: float = 0.7) -> LLMResponse:
        """Generate response using specified or default provider with automatic fallback"""
        
        # Use specified provider or default
        target_provider = provider or self.default_provider
        
        if not target_provider:
            return LLMResponse(
                content="",
                provider="none",
                model="none",
                success=False,
                error="No LLM providers available. Please configure API keys."
            )
        
        # Try target provider
        if target_provider in self.providers:
            provider_obj = self.providers[target_provider]
            if provider_obj.available:
                response = await provider_obj.generate(prompt, model, temperature)
                if response.success:
                    return response
                else:
                    logger.warning(f"{target_provider} failed: {response.error}")
        
        # Try fallback providers
        for fallback_provider in self.fallback_order:
            if fallback_provider == target_provider:
                continue  # Already tried
            
            provider_obj = self.providers[fallback_provider]
            if provider_obj.available:
                logger.info(f"Falling back to {fallback_provider}...")
                response = await provider_obj.generate(prompt, model, temperature)
                if response.success:
                    return response
                else:
                    logger.warning(f"{fallback_provider} failed: {response.error}")
        
        # All providers failed
        return LLMResponse(
            content="",
            provider="none",
            model="none",
            success=False,
            error="All LLM providers failed or unavailable"
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        return {
            "providers": {
                name: {
                    "available": provider.available,
                    "type": name
                }
                for name, provider in self.providers.items()
            },
            "default_provider": self.default_provider,
            "fallback_order": self.fallback_order
        }

# ==================== INITIALIZATION ====================
async def initialize_llm_gateway() -> LLMGateway:
    """Initialize and return configured LLM Gateway"""
    gateway = LLMGateway()
    await gateway.initialize()
    return gateway

# ==================== TESTING ====================
if __name__ == "__main__":
    async def test_gateway():
        """Test LLM Gateway"""
        print("=" * 60)
        print("AARIA LLM Gateway Test")
        print("=" * 60)
        
        gateway = await initialize_llm_gateway()
        
        print("\nProvider Status:")
        status = gateway.get_status()
        for name, info in status["providers"].items():
            status_icon = "✓" if info["available"] else "✗"
            print(f"  {status_icon} {name}: {'Available' if info['available'] else 'Not available'}")
        
        print(f"\nDefault Provider: {status['default_provider']}")
        print(f"Fallback Order: {' → '.join(status['fallback_order'])}")
        
        if gateway.default_provider:
            print("\nTesting generation...")
            response = await gateway.generate("Say hello in one sentence.")
            print(f"\nProvider: {response.provider}")
            print(f"Model: {response.model}")
            print(f"Success: {response.success}")
            print(f"Latency: {response.latency_ms:.0f}ms")
            if response.success:
                print(f"Response: {response.content}")
            else:
                print(f"Error: {response.error}")
        else:
            print("\n⚠️  No providers available for testing")
    
    asyncio.run(test_gateway())
