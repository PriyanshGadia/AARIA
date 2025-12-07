# Troubleshooting LLM Issues in AARIA

## Issue: "No LLM Available" or No Response Generated

If you're seeing messages like "[SYSTEM NOTICE] No LLM available" even though the logs show "LLM Gateway Initialized", this guide will help you diagnose and fix the issue.

## Diagnosis Steps

### Step 1: Check the Logs

Look for these key log messages:

```
INFO - LLM Gateway Initialized. Active: <provider>
INFO - ✅ LLM Gateway ENABLED with provider: <provider>
```

If you see "⚠️ No LLM provider active, using FALLBACK mode", then no valid LLM was detected.

### Step 2: Check for Error Messages

Look for error messages starting with ❌:

```
ERROR - ❌ Gemini API key not found! Set GEMINI_API_KEY environment variable.
ERROR - ❌ Gemini API request failed: 401
ERROR - ❌ Gemini LLM failed with exception: ...
```

These errors tell you exactly what's wrong.

## Common Issues and Solutions

### Issue 1: Gemini API Key Not Found

**Error:**
```
ERROR - ❌ Gemini API key not found! Set GEMINI_API_KEY environment variable.
```

**Solution:**
1. Check that `Backend/llm.env` exists
2. Open `Backend/llm.env` and verify `GEMINI_API_KEY=your_actual_key_here`
3. Make sure there are no extra spaces around the `=` sign
4. Restart AARIA

### Issue 2: Gemini API Key Invalid or Expired

**Error:**
```
ERROR - ❌ Gemini API request failed: 401
ERROR - Error details: {"error": {"code": 401, "message": "API key not valid"}}
```

**Solution:**
1. Go to https://makersuite.google.com/app/apikey
2. Generate a new API key
3. Update `Backend/llm.env` with the new key
4. Restart AARIA

### Issue 3: Gemini API Quota Exceeded

**Error:**
```
ERROR - ❌ Gemini API request failed: 429
ERROR - Error details: {"error": {"code": 429, "message": "Resource exhausted"}}
```

**Solution:**
- You've exceeded your free quota
- Wait until the quota resets (usually daily)
- OR switch to a different LLM provider (Ollama is free and unlimited)

### Issue 4: Ollama Not Running

**Logs show:**
```
INFO - Ollama not available
INFO - Ollama not available, switching to Gemini (API key found)
```

**Solution to use Ollama (Free, Local, Unlimited):**

#### On Linux/Mac:
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3.2

# Verify it's running
ollama list
curl http://localhost:11434/api/tags
```

#### On Windows:
1. Download Ollama from https://ollama.ai/download
2. Install and start Ollama
3. Open Command Prompt:
```cmd
ollama pull llama3.2
ollama list
```

#### Update llm.env:
```env
DEFAULT_LLM_PROVIDER=local
```

### Issue 5: Network/Connectivity Issues

**Error:**
```
ERROR - ❌ Gemini LLM failed with exception: Cannot connect to host
```

**Solution:**
1. Check your internet connection
2. Check if your firewall is blocking the API request
3. Try using Ollama (local, no internet required)

## Testing Your Setup

### Test 1: Check Environment Variables
```bash
cd Backend
python -c "from dotenv import load_dotenv; import os; load_dotenv('llm.env'); print('GEMINI_API_KEY:', 'SET' if os.getenv('GEMINI_API_KEY') else 'NOT SET')"
```

### Test 2: Test Gemini API Directly
```bash
# Replace YOUR_API_KEY with your actual key
curl -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

If this returns a proper response, your API key works.
If it returns an error, that's your issue.

### Test 3: Check Ollama
```bash
curl http://localhost:11434/api/tags
```

If this returns JSON with models, Ollama is working.

## Recommended Setup

For the best experience, we recommend:

### Option 1: Ollama (Best for Privacy & No Cost)
```bash
# Install
curl https://ollama.ai/install.sh | sh  # Linux/Mac
# OR download from https://ollama.ai/download for Windows

# Pull a good model
ollama pull llama3.2

# Configure AARIA
# Edit Backend/llm.env:
DEFAULT_LLM_PROVIDER=local
```

**Pros:**
- ✅ Free and unlimited
- ✅ Private (data never leaves your computer)
- ✅ Fast
- ✅ No API keys needed
- ✅ No internet required

**Cons:**
- Requires 8GB+ RAM
- Slower than cloud on older hardware

### Option 2: Google Gemini (Good for Testing)
```bash
# Get free API key from https://makersuite.google.com/app/apikey

# Configure AARIA
# Edit Backend/llm.env:
GEMINI_API_KEY=your_key_here
DEFAULT_LLM_PROVIDER=gemini
```

**Pros:**
- ✅ Free tier available
- ✅ Fast responses
- ✅ No local setup needed

**Cons:**
- Limited free quota
- Requires internet
- Data sent to Google

### Option 3: Mix of Both
```bash
# Set up both Ollama AND Gemini

# Ollama as primary (privacy + unlimited)
ollama pull llama3.2

# Gemini as backup (when you need extra power)
# Edit Backend/llm.env:
GEMINI_API_KEY=your_key_here
DEFAULT_LLM_PROVIDER=local  # Uses Ollama first, Gemini if Ollama fails
```

## Getting More Help

### Enable Debug Logging

Edit the start of your `Backend/stem.py`:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - [STEM] - %(levelname)s - %(message)s',
    ...
)
```

This will show much more detailed information about what's happening.

### Check Recent Changes

The latest improvements include:
- ✅ Better error messages for LLM failures
- ✅ Automatic fallback detection
- ✅ Clear logging of API issues
- ✅ Support for all major LLM providers

If you're still having issues after following this guide, the error messages should now clearly tell you what's wrong!

## Quick Fixes Checklist

- [ ] `Backend/llm.env` file exists
- [ ] API key is set and valid (test with curl)
- [ ] No extra spaces in llm.env file
- [ ] Internet connection working (for cloud LLMs)
- [ ] Ollama installed and running (for local LLM)
- [ ] Latest version of AARIA pulled from git
- [ ] Python requirements installed: `pip install -r requirements.txt`
- [ ] Restart AARIA after making changes

---

**Note**: The latest code improvements include much better error handling and logging. Make sure you have the latest version by pulling from the repository!
