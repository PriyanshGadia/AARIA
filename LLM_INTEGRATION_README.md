# AARIA LLM Integration Guide

## Overview

AARIA now includes a flexible LLM (Large Language Model) Gateway that allows integration with local and cloud-based language models while maintaining privacy and security.

## Features

✅ **Privacy-First Architecture** - Automatic PII filtering before cloud calls  
✅ **Multi-Provider Support** - OpenAI, Anthropic, Gemini, Groq, Ollama (local), and fallback  
✅ **Seamless Fallback** - Works without LLM, gracefully degrades  
✅ **Token Usage Tracking** - Monitor costs and usage  
✅ **Personality Integration** - Responses reflect AARIA's personality traits  
✅ **llama3:latest Support** - Latest LLaMA 3 models via Ollama

## Supported Providers

| Provider | Type | Privacy | Speed | Cost | Recommended For |
|----------|------|---------|-------|------|-----------------|
| **Ollama (Local)** | Local | 🔒 Private | Medium | Free | Default, privacy-focused |
| **Groq** | Cloud | ⚠️ Public | 🚀 Ultra-fast | Low | Speed-critical tasks |
| **OpenAI** | Cloud | ⚠️ Public | Fast | Medium | General purpose |
| **Anthropic Claude** | Cloud | ⚠️ Public | Medium | Medium | Complex reasoning |
| **Google Gemini** | Cloud | ⚠️ Public | Fast | Low | Multi-modal tasks |
| **Fallback** | Local | 🔒 Private | Instant | Free | No LLM available |

## Quick Start

### Option 1: Use Fallback (Default - No Setup Required)

AARIA works out of the box with minimal responses. No configuration needed.

```bash
python Backend/stem.py
```

### Option 2: Enable Local LLM (Recommended - Private & Free)

1. Install Ollama:
```bash
curl https://ollama.ai/install.sh | sh
```

2. Pull a model:
```bash
# Recommended - Latest LLaMA 3 (best quality)
ollama pull llama3:latest

# Alternative options:
ollama pull llama2
ollama pull mistral
ollama pull mixtral
```

3. AARIA will auto-detect Ollama on startup. No code changes needed!

### Option 3: Enable Cloud LLM

Set API key as environment variable:

```bash
# For OpenAI:
export OPENAI_API_KEY="your-api-key-here"

# For Anthropic Claude:
export ANTHROPIC_API_KEY="your-api-key-here"

# For Google Gemini:
export GEMINI_API_KEY="your-api-key-here"

# For Groq (ultra-fast):
export GROQ_API_KEY="your-api-key-here"
```

Then edit `stem.py` (around line 328) to change default provider:

```python
llm_config = {
    "enabled": True,
    "default_provider": "gemini",  # or "openai", "anthropic", "groq", "local"
    "providers": {
        "local": {
            "endpoint": "http://localhost:11434",
            "model": "llama3:latest"
        },
        "openai": {
            "model": "gpt-3.5-turbo"  # or "gpt-4"
        },
        "anthropic": {
            "model": "claude-3-sonnet-20240229"
        },
        "gemini": {
            "model": "gemini-pro"
        },
        "groq": {
            "model": "llama3-70b-8192"  # ultra-fast LLaMA 3
        }
    }
}
```

## Privacy & Security

### Automatic Data Filtering

The LLM Gateway automatically filters sensitive data before sending to cloud:

- ✅ Email addresses → `[EMAIL_REDACTED]`
- ✅ Phone numbers → `[PHONE_REDACTED]`
- ✅ File paths → `[FILE_PATH_REDACTED]`
- ✅ API keys → `[API_KEY_REDACTED]`
- ✅ Credit card numbers → `[CREDIT_CARD_REDACTED]`
- ✅ IP addresses → `[IP_ADDRESS_REDACTED]`

### Privacy Levels

- **PUBLIC**: No sensitive data, safe for cloud
- **CONFIDENTIAL**: Some filtering applied
- **OWNER_ONLY**: Never sent to cloud, local-only

### Data Flow

```
User Input
    ↓
[Privacy Filter]
    ├─→ Sensitive Data → Local LLM Only
    └─→ Safe Data → Cloud LLM (if enabled)
            ↓
    [Response Filter]
            ↓
    Output to User
```

## Architecture

### LLMGateway Class

**Location**: `Backend/llm_gateway.py`

Main interface for all LLM interactions:

```python
from llm_gateway import get_llm_gateway, LLMRequest, LLMProvider, PrivacyLevel

# Get gateway instance
llm_gateway = await get_llm_gateway()

# Create request
request = LLMRequest(
    prompt="What is machine learning?",
    provider=LLMProvider.LOCAL,
    privacy_level=PrivacyLevel.PUBLIC,
    max_tokens=150,
    temperature=0.7
)

# Generate response
response = await llm_gateway.generate_response(request)
print(response.text)
```

### Integration Points

1. **Temporal Core** (`temporal_core.py`)
   - Enhanced `_generate_response()` method
   - Uses LLM for natural conversation
   - Falls back to rule-based if LLM unavailable

2. **Stem** (`stem.py`)
   - Initializes LLM Gateway during boot
   - Configures providers and settings

3. **Privacy Filter** (`llm_gateway.py`)
   - Sanitizes prompts before cloud calls
   - Blocks sensitive data patterns

## Cost Estimates

### Cloud LLMs

**Groq (Ultra-Fast):**
- LLaMA 3 70B: $0.59 per 1M input tokens, $0.79 per 1M output tokens
- LLaMA 3 8B: $0.05 per 1M input tokens, $0.08 per 1M output tokens
- ~100 conversations/day with 70B = ~$0.14/month
- **⚡ Fastest option - 10x faster than GPT-4**

**OpenAI GPT-3.5-Turbo:**
- Input: $0.50 per 1M tokens
- Output: $1.50 per 1M tokens
- ~100 conversations/day = ~$0.20/month

**OpenAI GPT-4:**
- Input: $10 per 1M tokens  
- Output: $30 per 1M tokens
- ~100 conversations/day = ~$4/month

**Anthropic Claude 3 Sonnet:**
- Input: $3 per 1M tokens
- Output: $15 per 1M tokens
- ~100 conversations/day = ~$1.80/month

**Google Gemini Pro:**
- Input: $0.50 per 1M tokens (first 1M free)
- Output: $1.50 per 1M tokens (first 1M free)
- ~100 conversations/day = ~$0.20/month (or FREE under quota)

### Local LLMs (Free)

**Ollama with LLaMA 3 / LLaMA 2 / Mistral:**
- No API costs
- Requires GPU (RTX 3060 12GB minimum recommended)
- One-time hardware cost only

## Configuration Options

### Complete Configuration Example

```python
llm_config = {
    "enabled": True,
    "default_provider": "local",
    
    # Provider configurations
    "providers": {
        "local": {
            "endpoint": "http://localhost:11434",
            "model": "mistral",
            "timeout": 30
        },
        "openai": {
            "api_key": None,  # Uses OPENAI_API_KEY env var
            "model": "gpt-4-turbo-preview",
            "max_tokens": 1000,
            "temperature": 0.7
        },
        "anthropic": {
            "api_key": None,  # Uses ANTHROPIC_API_KEY env var
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 1000,
            "temperature": 0.7
        }
    },
    
    # Privacy settings
    "privacy_filters": {
        "strip_pii": True,
        "strip_file_paths": True,
        "allowed_privacy_levels": ["public", "confidential"]
    },
    
    # Budget controls
    "budget": {
        "max_tokens_per_day": 100000,
        "max_cost_per_month": 50.0  # USD
    }
}
```

## Testing

### Test LLM Integration

```python
import asyncio
from llm_gateway import get_llm_gateway, LLMRequest, LLMProvider

async def test():
    gateway = await get_llm_gateway()
    
    # Test fallback
    request = LLMRequest(prompt="Hello!", provider=LLMProvider.FALLBACK)
    response = await gateway.generate_response(request)
    print(f"Fallback: {response.text}")
    
    # Test local (if Ollama running)
    request = LLMRequest(prompt="What is AI?", provider=LLMProvider.LOCAL)
    response = await gateway.generate_response(request)
    print(f"Local: {response.text}")

asyncio.run(test())
```

### Test Privacy Filter

```python
from llm_gateway import PrivacyFilter, PrivacyLevel

filter = PrivacyFilter()

# Test sensitive data filtering
text = "My email is john@example.com and phone is 555-123-4567"
sanitized = filter.sanitize(text, PrivacyLevel.CONFIDENTIAL)
print(sanitized)
# Output: "My email is [EMAIL_REDACTED] and phone is [PHONE_REDACTED]"
```

## Troubleshooting

### "Local LLM failed"

**Cause**: Ollama not running or model not pulled  
**Solution**: 
```bash
# Start Ollama service
ollama serve

# Pull model
ollama pull llama2
```

### "OpenAI request failed"

**Cause**: Invalid API key or no credits  
**Solution**: Check `OPENAI_API_KEY` environment variable and account balance

### "Using fallback"

**Cause**: LLM provider failed, system automatically degraded  
**Solution**: This is expected behavior. System continues working with rule-based responses.

### InvalidTag Errors

**Cause**: Encryption key changed (different biometric hash between runs)  
**Solution**: Database automatically reinitializes with new key. Old encrypted data is cleared.

## Performance Optimization

### Caching

Implement response caching to reduce API calls:

```python
# TODO: Add semantic caching
# Cache similar prompts for 1 hour
# Use embeddings to detect similar questions
```

### Streaming

For long responses, enable streaming:

```python
# TODO: Implement streaming responses
# Better UX for cloud LLMs with long generation times
```

### Batch Processing

Process multiple requests efficiently:

```python
# TODO: Batch similar requests
# Send multiple prompts in one API call
```

## Roadmap

- [ ] Semantic caching to reduce redundant API calls
- [ ] Streaming responses for better UX
- [ ] RAG (Retrieval-Augmented Generation) with local knowledge base
- [ ] Fine-tuning local models on owner's conversation style
- [ ] Multi-turn conversation context management
- [ ] Token budget enforcement and alerts
- [ ] Automatic model selection based on task complexity

## Support

For issues or questions:
1. Check logs in `aaria_system.log`
2. Test with fallback provider first
3. Verify API keys and network connectivity
4. Review privacy filter logs for data leakage concerns

## Security Notes

⚠️ **Never commit API keys to version control**  
✅ Always use environment variables for secrets  
✅ Review privacy filter logs regularly  
✅ Test with sensitive data to verify filtering  
✅ Use local LLM for maximum privacy  

## License

Part of the AARIA project. See main README for license information.
