# LLM Environment Configuration Setup

## Quick Start

1. **Copy the example file:**
   ```bash
   cd Backend
   cp llm.env.example llm.env
   ```

2. **Edit llm.env and add your API keys:**
   ```bash
   nano llm.env  # or use any text editor
   ```

3. **Install dependencies:**
   ```bash
   pip install -r ../requirements.txt
   ```

4. **Run AARIA:**
   ```bash
   python stem.py
   ```

## Configuration Options

### Local LLM (Recommended - Free & Private)

**Ollama Setup:**
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull a model (recommended: llama3.2)
ollama pull llama3.2

# Alternative models:
ollama pull llama3:latest
ollama pull mistral
ollama pull mixtral
```

In `llm.env`:
```env
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=llama3.2
DEFAULT_LLM_PROVIDER=local
```

### Google Gemini (Free Tier Available)

1. Get API key from: https://makersuite.google.com/app/apikey
2. Add to `llm.env`:
   ```env
   GEMINI_API_KEY=your_api_key_here
   DEFAULT_LLM_PROVIDER=gemini
   ```

**Important:** Use `gemini-1.5-flash` or `gemini-1.5-pro`. The old `gemini-pro` model is deprecated.

### Groq (Ultra-Fast, Low Cost)

1. Get API key from: https://console.groq.com
2. Add to `llm.env`:
   ```env
   GROQ_API_KEY=your_api_key_here
   DEFAULT_LLM_PROVIDER=groq
   ```

### OpenAI (GPT-3.5/GPT-4)

1. Get API key from: https://platform.openai.com/api-keys
2. Add to `llm.env`:
   ```env
   OPENAI_API_KEY=your_api_key_here
   DEFAULT_LLM_PROVIDER=openai
   ```

### Anthropic Claude

1. Get API key from: https://console.anthropic.com/
2. Add to `llm.env`:
   ```env
   ANTHROPIC_API_KEY=your_api_key_here
   DEFAULT_LLM_PROVIDER=anthropic
   ```

## Troubleshooting

### "404 - models/gemini-pro is not found"

**Solution:** Update to use the new Gemini models:
- Change model in `llm.env` or config to `gemini-1.5-flash` or `gemini-1.5-pro`
- The old `gemini-pro` model is no longer supported in v1beta API

### "Local LLM failed"

**Solution:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start Ollama
ollama serve

# Pull a model if needed
ollama pull llama3.2
```

### "No LLM Active"

**Solution:**
1. Check that `llm.env` exists in the `Backend/` directory
2. Verify at least one API key is set or Ollama is running
3. Check that `python-dotenv` is installed: `pip install python-dotenv`

### Environment variables not loading

**Verification steps:**
```bash
# Check if llm.env exists
ls -la Backend/llm.env

# Check file contents (make sure keys are set)
cat Backend/llm.env

# Ensure python-dotenv is installed
pip show python-dotenv
```

## Security Notes

⚠️ **IMPORTANT:**
- Never commit `llm.env` to version control
- `llm.env` is already in `.gitignore`
- Only commit `llm.env.example`
- Keep your API keys private

## Environment Variables Priority

AARIA loads configuration in this order:
1. `Backend/llm.env` file (if exists)
2. System environment variables
3. Config database settings

If you set environment variables in your shell, they will override `llm.env`:
```bash
export GEMINI_API_KEY="your_key"
python Backend/stem.py
```

## Provider Selection Logic

AARIA automatically selects the best available provider:
1. If `DEFAULT_LLM_PROVIDER` is set in `llm.env`, tries that first
2. Falls back to Ollama if running locally
3. Falls back to any available cloud provider with API key
4. Falls back to basic responses if no LLM available

## Cost Comparison

| Provider | Cost (per 1M tokens) | Privacy | Speed | Recommended For |
|----------|---------------------|---------|-------|-----------------|
| **Ollama (Local)** | Free | 🔒 Private | Medium | Daily use, privacy-focused |
| **Gemini 1.5 Flash** | Free tier available | ⚠️ Cloud | Fast | Testing, light use |
| **Groq** | $0.05-$0.79 | ⚠️ Cloud | Ultra-fast | Production, speed-critical |
| **OpenAI GPT-3.5** | $0.50-$1.50 | ⚠️ Cloud | Fast | General purpose |
| **OpenAI GPT-4** | $10-$30 | ⚠️ Cloud | Medium | Complex tasks |
| **Claude 3** | $3-$15 | ⚠️ Cloud | Medium | Reasoning tasks |

## Testing Your Setup

After configuring `llm.env`, test with:
```bash
cd Backend
python stem.py
```

Expected output:
```
2025-12-07 13:24:25,989 - INFO - LLM Gateway initialized: enabled=True, default=gemini
2025-12-07 13:24:25,989 - INFO - Available providers: gemini: Google Gemini (gemini-1.5-flash)
```

Then interact:
```
You: hi
>> AARIA: Hello! How can I assist you today?
```

If you see `[NO LLM ACTIVE]`, check your configuration following the troubleshooting steps above.
