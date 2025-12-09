# Testing Guide for LLM Integration Fix

This guide helps you verify that the LLM integration fix is working correctly in your environment.

## Quick Test

The fastest way to verify the fix:

```bash
cd /path/to/AARIA
python Backend/test_llm_integration.py
```

Expected output: All tests should pass with ✅ markers.

## Test Scenarios

### Scenario 1: No LLM Providers Available (Fallback Mode)

**Setup**: Don't set any API keys and don't install Ollama

**Run**:
```bash
python Backend/stem.py
```

**Expected Behavior**:
- System boots successfully
- Shows warnings about no LLM providers available
- Provides instructions for installing Ollama or setting API keys
- Uses fallback mode (no intelligent responses)
- System still functional for all other operations

**Test Command**:
```
You: hello
```

**Expected Response**:
```
>> AARIA: [NO LLM ACTIVE] I detected your message (intent: greeting). 
However, I'm currently operating without a language model...

TO ENABLE REAL AI RESPONSES:
• Install Ollama (FREE, LOCAL): curl https://ollama.ai/install.sh | sh && ollama pull llama3:latest
• Or use Cloud AI (PAID):
  - OpenAI: export OPENAI_API_KEY='your-key'
  ...
```

### Scenario 2: Local Ollama Only

**Setup**: 
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3:latest

# Start Ollama (usually automatic)
ollama serve
```

**Run**:
```bash
python Backend/stem.py
```

**Expected Behavior**:
- System detects Ollama is available
- Uses Ollama as default provider
- Provides intelligent responses
- No API costs

**Test Command**:
```
You: What is artificial intelligence?
```

**Expected Response**:
- Real AI-generated response from Ollama
- Natural language conversation

### Scenario 3: Gemini API with Automatic Ollama Fallback

**Setup**: 
```bash
# Set Gemini API key
export GEMINI_API_KEY='your-actual-gemini-api-key'

# Optional: Install Ollama as backup
curl https://ollama.ai/install.sh | sh
ollama pull llama3:latest
```

**Run**:
```bash
python Backend/stem.py
```

**Expected Behavior**:
- System detects Gemini API key
- Uses Gemini as primary provider
- If Gemini fails (network issue, quota exceeded):
  - Automatically tries Ollama if available
  - Falls back to no-LLM mode if Ollama unavailable

**Test Commands**:

1. Normal operation (Gemini working):
```
You: Explain quantum computing
```

Expected: Response from Gemini API

2. Simulate Gemini failure (disconnect internet or exhaust quota):
```
You: Tell me about machine learning
```

Expected: 
- Log shows "Gemini failed, trying Ollama fallback..."
- Response from Ollama (if installed)
- Or fallback message (if Ollama not installed)

### Scenario 4: Multiple Cloud Providers

**Setup**:
```bash
# Set multiple API keys
export GEMINI_API_KEY='your-gemini-key'
export OPENAI_API_KEY='your-openai-key'
export GROQ_API_KEY='your-groq-key'
```

**Run**:
```bash
python Backend/stem.py
```

**Expected Behavior**:
- System detects multiple providers
- Uses default provider (set in config)
- Automatically fails over to other providers if primary fails

### Scenario 5: Gemini API v1 Endpoint Test

**Purpose**: Verify the Gemini API endpoint fix (v1 vs v1beta)

**Run**:
```bash
python Backend/test_gemini_fix.py
```

**Expected Output**:
```
============================================================
Testing Gemini API Endpoint Fix
============================================================

1. Testing Gemini API endpoint URL...
   - API URL called: https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=test_key
   ✓ Correct API version (v1) is used
   ✓ Correct model name (gemini-1.5-flash)
   - Response text: Test response
   - Provider: gemini

2. Testing automatic Ollama fallback...
   - Fallback confidence: 0.1
   - Fallback provider: no_llm_fallback
   ✓ Automatic fallback triggered correctly

============================================================
✓ All Gemini fix tests passed!
============================================================
```

### Scenario 6: Complete System Boot Test

**Run**:
```bash
python test_system_boot.py
```

**Expected Output**:
- System boots all 6 cores successfully
- LLM Gateway initializes
- All cores start and stop cleanly
- No errors in logs

## Troubleshooting

### Issue: "Gemini request failed: 404"

**Before Fix**: This error would stop AARIA from responding
**After Fix**: System automatically tries Ollama fallback

**Verify Fix**:
```bash
# Check logs
grep "Gemini request failed" aaria_system.log

# Should see:
# "Gemini request failed: 404"
# "Attempting to fallback to local Ollama..."
```

### Issue: "Local LLM failed"

**Cause**: Ollama not running or model not downloaded

**Solution**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running:
ollama serve

# If no models:
ollama pull llama3:latest
```

### Issue: "No AI providers available"

**Cause**: No Ollama and no API keys set

**Solution**: Choose one:
1. Install Ollama (free, local, private)
2. Set an API key for cloud LLM

### Issue: API key set but still using fallback

**Diagnosis**:
```bash
# Check environment variables
echo $GEMINI_API_KEY
echo $OPENAI_API_KEY

# Check logs for initialization
grep "LLM Gateway initialized" aaria_system.log
```

**Solution**:
- Verify API key is valid
- Check API quota/billing
- Verify network connectivity

## Performance Testing

### Latency Test

Compare response times:

1. **Ollama** (local): 1-5 seconds (depends on hardware)
2. **Groq** (cloud): 0.5-2 seconds (fastest cloud)
3. **Gemini** (cloud): 1-3 seconds
4. **OpenAI** (cloud): 2-5 seconds
5. **Fallback** (no LLM): Instant (no AI)

### Cost Test

Track API usage:

```bash
# Enable token tracking (already enabled in code)
# Check logs for token usage:
grep "tokens_used" aaria_system.log
```

## Security Testing

### PII Filtering Test

Verify sensitive data is not sent to cloud:

```bash
# In AARIA prompt:
You: My email is john@example.com and SSN is 123-45-6789

# Check logs - should see:
# "[EMAIL_REDACTED]" instead of real email
# "[SSN_REDACTED]" instead of real SSN
```

### Local-Only Test

Verify owner-only data stays local:

```bash
# Data marked as OWNER_ONLY should never reach cloud
# Check logs for privacy routing
grep "routing to local LLM" aaria_system.log
```

## Automated Test Suite

Run all tests:

```bash
# Test 1: Basic integration
python Backend/test_llm_integration.py

# Test 2: Gemini fix
python Backend/test_gemini_fix.py

# Test 3: System boot
python test_system_boot.py
```

All tests should pass with exit code 0.

## CI/CD Integration

Add to your CI pipeline:

```yaml
# Example GitHub Actions
- name: Test LLM Integration
  run: |
    python Backend/test_llm_integration.py
    python Backend/test_gemini_fix.py
    python test_system_boot.py
```

## Reporting Issues

If tests fail:

1. Check `aaria_system.log` for errors
2. Verify dependencies: `pip install -r requirements.txt`
3. Test internet connectivity
4. Verify API keys are valid
5. Check Ollama status: `curl http://localhost:11434/api/tags`

Include in bug report:
- Test output
- Log file (`aaria_system.log`)
- Python version
- OS version
- Ollama version (if installed)
- API provider being used

## Success Criteria

✅ All tests pass
✅ System boots without errors
✅ Gemini uses v1 API (not v1beta)
✅ Automatic Ollama fallback works
✅ Fallback mode works when no LLM available
✅ No security vulnerabilities detected

## Next Steps

After verifying tests pass:

1. Use AARIA normally with your preferred LLM
2. Monitor logs for any issues
3. Report any problems with test output and logs
4. Enjoy improved reliability and automatic fallback!

## License

Part of the AARIA project. See main README for license information.
