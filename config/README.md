# AARIA Configuration Directory

This directory contains configuration files for AARIA, including API keys for LLM providers.

## Files in This Directory

### .env.example
Template file showing all available API key configuration options. **This file is safe to commit to git.**

### llm.env
Your actual API keys file. **This file should NEVER be committed to git** (it's automatically ignored).

To set up:
```bash
# Copy the example file
cp .env.example llm.env

# Edit llm.env and add your actual API keys
# Use any text editor: notepad, vim, nano, VS Code, etc.
```

Example `llm.env` content:
```bash
# Add your actual API keys here
GROQ_API_KEY=gsk_your_actual_groq_key_here
OPENAI_API_KEY=sk-your_actual_openai_key_here
```

## Security Notes

✅ **SAFE TO COMMIT:**
- `.env.example` - Template file with no real keys
- This `README.md` file

❌ **NEVER COMMIT:**
- `llm.env` - Contains your real API keys
- `aaria_config.json` - May contain sensitive settings
- Any file with "key", "secret", or "token" in the name

## Getting API Keys

### Free Options

1. **Groq** (Recommended - Free & Fast)
   - Sign up: https://console.groq.com/
   - Create API key
   - Add to `llm.env`: `GROQ_API_KEY=gsk_...`

2. **Ollama** (100% Free - Local)
   - Install: https://ollama.ai/
   - No API key needed!
   - Runs on your computer

3. **Google Gemini** (Free Tier)
   - Get key: https://makersuite.google.com/app/apikey
   - Add to `llm.env`: `GEMINI_API_KEY=...`

### Paid Options

4. **OpenAI** (Most Capable)
   - Get key: https://platform.openai.com/api-keys
   - Add to `llm.env`: `OPENAI_API_KEY=sk-...`

5. **Anthropic Claude** (High Quality)
   - Get key: https://console.anthropic.com/account/keys
   - Add to `llm.env`: `ANTHROPIC_API_KEY=...`

## Troubleshooting

### "No LLM providers available"
**Solution:** Create `config/llm.env` and add at least one API key, or install Ollama.

### "API key not detected"
**Solution:** 
1. Check file is named exactly `llm.env` (not `llm.env.txt`)
2. Check keys are in format: `KEY_NAME=value` (no spaces around `=`)
3. Restart AARIA after adding keys

### "Permission denied"
**Solution:** On Linux/Mac, check file permissions:
```bash
chmod 600 llm.env  # Only you can read/write
```

## Environment Variable Priority

AARIA checks for API keys in this order:
1. `config/llm.env` file (highest priority)
2. System environment variables
3. Defaults to Ollama if available

You can use both methods - the file takes precedence.

## Advanced: Using Different Locations

By default, AARIA looks for `config/llm.env`. To use a different location:

```python
from Backend.env_loader import EnvironmentLoader

# Load from custom location
loader = EnvironmentLoader("/path/to/my/custom.env")
loader.load()
```

## Quick Reference

```bash
# Create config file from template
cp config/.env.example config/llm.env

# Edit and add your keys
nano config/llm.env   # or vim, notepad, etc.

# Verify AARIA detects them
cd Backend
python env_loader.py

# Run AARIA
python stem.py
```

## Support

For more detailed setup instructions, see: [LLM_SETUP.md](../LLM_SETUP.md)
