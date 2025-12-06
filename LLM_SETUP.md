# AARIA LLM Gateway - Setup Guide

## Overview

The LLM Gateway provides unified access to multiple LLM providers with automatic API key detection from **config/llm.env file** or system environment variables. It supports automatic fallback and requires zero configuration changes to switch providers.

## Quick Setup

### Method 1: Using config/llm.env File (Recommended)

This is the easiest and most secure way to manage your API keys.

**Step 1:** Create the environment file
```bash
# Copy the example file
cp config/.env.example config/llm.env

# Or let AARIA create it for you
cd Backend
python env_loader.py
```

**Step 2:** Edit config/llm.env and add your API keys
```bash
# Example config/llm.env
GROQ_API_KEY=your-actual-groq-key-here
OPENAI_API_KEY=sk-your-actual-openai-key
```

**Step 3:** Run AARIA
```bash
python Backend/stem.py
```

That's it! AARIA will automatically detect and use your API keys.

### Method 2: Using System Environment Variables

If you prefer using system environment variables instead of a file:

**Linux/Mac:**
```bash
export GROQ_API_KEY='your-key'
python Backend/stem.py
```

**Windows PowerShell:**
```powershell
$env:GROQ_API_KEY='your-key'
python Backend/stem.py
```

**Windows Command Prompt:**
```cmd
set GROQ_API_KEY=your-key
python Backend\stem.py
```

## Priority Order

AARIA loads API keys in this order (first found wins):
1. **config/llm.env file** (most secure, recommended)
2. **System environment variables** (set via export/set commands)
3. **Default/None** (falls back to Ollama local mode)

## Supported Providers

| Provider | Environment Variable | Models | Notes |
|----------|---------------------|---------|-------|
| **Groq** | `GROQ_API_KEY` | llama3-70b-8192 | Ultra-fast, recommended |
| **OpenAI** | `OPENAI_API_KEY` | gpt-3.5-turbo, gpt-4 | Requires paid account |
| **Google Gemini** | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | gemini-pro | Free tier available |
| **Anthropic Claude** | `ANTHROPIC_API_KEY` | claude-3-sonnet | High quality |
| **Ollama** | (none) | llama3:latest, etc. | 100% free, local |

## Quick Start

### Option 1: Using config/llm.env File (Easiest & Most Secure)

```bash
# Step 1: Create your API key file
cp config/.env.example config/llm.env

# Step 2: Edit the file and add your actual API keys
# (Use any text editor: notepad, vim, nano, VS Code, etc.)

# Step 3: Run AARIA - it automatically detects the keys
python Backend/stem.py
```

The `config/llm.env` file is **never committed to git** (it's in .gitignore), keeping your keys secure.

### Option 2: Local Ollama (FREE, No API Key)

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3:latest

# Run AARIA (no environment variables needed)
python Backend/stem.py
```

### Option 3: System Environment Variables

```bash
# Get free API key from https://console.groq.com/

# Set environment variable
export GROQ_API_KEY='your-api-key-here'

# Run AARIA
python Backend/stem.py
```

### Option 3: OpenAI (Paid)

```bash
# Get API key from https://platform.openai.com/

# Set environment variable
export OPENAI_API_KEY='sk-your-api-key-here'

# Run AARIA
python Backend/stem.py
```

### Option 4: Google Gemini (Free Tier)

```bash
# Get API key from https://makersuite.google.com/app/apikey

# Set environment variable
export GEMINI_API_KEY='your-api-key-here'

# Run AARIA
python Backend/stem.py
```

### Option 5: Anthropic Claude (Paid)

```bash
# Get API key from https://console.anthropic.com/

# Set environment variable
export ANTHROPIC_API_KEY='your-api-key-here'

# Run AARIA
python Backend/stem.py
```

## Setting Environment Variables

### Linux/Mac (Temporary)
```bash
export GROQ_API_KEY='your-key'
python Backend/stem.py
```

### Linux/Mac (Permanent)
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export GROQ_API_KEY="your-key"' >> ~/.bashrc
source ~/.bashrc
```

### Windows PowerShell (Temporary)
```powershell
$env:GROQ_API_KEY='your-key'
python Backend/stem.py
```

### Windows PowerShell (Permanent)
```powershell
[System.Environment]::SetEnvironmentVariable('GROQ_API_KEY', 'your-key', 'User')
```

### Windows Command Prompt (Temporary)
```cmd
set GROQ_API_KEY=your-key
python Backend\stem.py
```

## Multiple Providers (Automatic Fallback)

You can set multiple API keys, and AARIA will automatically use the best available provider with fallback:

```bash
# Set multiple providers
export GROQ_API_KEY='groq-key'
export OPENAI_API_KEY='openai-key'
export GEMINI_API_KEY='gemini-key'

# AARIA will use them in this priority order:
# 1. Groq (fastest)
# 2. OpenAI (most capable)
# 3. Gemini (balanced)
# 4. Anthropic (high quality)
# 5. Ollama (local fallback)
```

## Installing Optional Dependencies

```bash
# For OpenAI
pip install openai>=1.3.0

# For Anthropic Claude
pip install anthropic>=0.7.0

# For Google Gemini
pip install google-generativeai>=0.3.0

# For Groq and Ollama (required)
pip install aiohttp>=3.9.0
```

## Testing LLM Gateway

```bash
# Test which providers are detected
cd Backend
python llm_gateway.py
```

Expected output:
```
============================================================
AARIA LLM Gateway Test
============================================================
✓ OpenAI API key detected
✓ Groq API key detected

Provider Status:
  ✓ openai: Available
  ✓ groq: Available
  ✗ ollama: Not available

Default Provider: groq
Fallback Order: groq → openai

Testing generation...
Provider: groq
Model: llama3-70b-8192
Success: True
Response: Hello! How can I assist you today?
```

## Usage in Code

```python
from llm_gateway import initialize_llm_gateway

# Initialize gateway (reads environment variables automatically)
gateway = await initialize_llm_gateway()

# Generate response using default provider
response = await gateway.generate("What is the capital of France?")
print(response.content)  # "The capital of France is Paris."

# Generate with specific provider
response = await gateway.generate(
    "Explain quantum computing",
    provider="openai",
    model="gpt-4",
    temperature=0.7
)

# Check status
status = gateway.get_status()
print(f"Available providers: {list(status['providers'].keys())}")
```

## Troubleshooting

### Issue: "No LLM providers available"
**Solution**: Set at least one API key or install Ollama

### Issue: "Ollama request failed: 500"
**Solutions**:
1. Start Ollama: `ollama serve`
2. Pull a model: `ollama pull llama3:latest`
3. Or set a cloud API key instead

### Issue: API key not detected
**Solutions**:
1. Check spelling: `GROQ_API_KEY` (all caps)
2. Restart terminal after setting variable
3. Use permanent environment variable method
4. Verify with: `echo $GROQ_API_KEY` (Linux/Mac) or `echo %GROQ_API_KEY%` (Windows)

### Issue: "HTTP 401 Unauthorized"
**Solution**: Your API key is invalid or expired. Get a new one from the provider's website.

### Issue: Rate limit errors
**Solution**: 
1. Wait a few minutes
2. Upgrade to paid tier
3. Use a different provider (set multiple keys for automatic fallback)

## Security Best Practices

1. **Never commit API keys to git**
   - API keys should only be in environment variables
   - The `.gitignore` excludes any files with "key" or "secret" in the name

2. **Use different keys for development and production**
   ```bash
   export GROQ_API_KEY_DEV='dev-key'
   export GROQ_API_KEY_PROD='prod-key'
   ```

3. **Rotate keys regularly**
   - Generate new API keys every 90 days
   - Revoke old keys after rotation

4. **Limit key permissions**
   - Use read-only keys where possible
   - Set spending limits on paid providers

## Cost Comparison

| Provider | Cost | Free Tier | Speed | Quality |
|----------|------|-----------|-------|---------|
| Ollama | $0 | ∞ | Medium | Good |
| Groq | $0.27/1M tokens | Yes | ⚡ Ultra-fast | Excellent |
| Gemini | $0-$0.50/1M tokens | 60 req/min | Fast | Very Good |
| OpenAI GPT-4 | $30/1M tokens | $5 credit | Medium | Excellent |
| Claude | $15/1M tokens | Limited | Fast | Excellent |

**Recommendation**: Start with Groq (free + fast) or Ollama (local + free)

## Support

For issues with:
- **LLM Gateway code**: Check logs in `logs/aaria.log`
- **API keys**: Contact the provider's support
- **Ollama**: See https://ollama.ai/

---

**Version**: 1.0.0  
**Last Updated**: December 2024  
**Status**: Production Ready
