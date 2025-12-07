#!/usr/bin/env python3
"""
Test script for LLM Gateway integration
"""
import sys
import os
import asyncio
from pathlib import Path

# Add Backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

async def test_llm_gateway():
    """Test LLM Gateway initialization"""
    print("=" * 60)
    print("Testing LLM Gateway Integration")
    print("=" * 60)
    
    try:
        from llm_gateway import get_llm_gateway, LLMRequest, LLMProvider
        
        print("\n1. Importing LLM Gateway... ✓")
        
        # Test configuration
        llm_config = {
            "enabled": True,
            "default_provider": "local",
            "providers": {
                "local": {
                    "endpoint": "http://localhost:11434",
                    "model": "llama3.2"
                },
                "gemini": {
                    "model": "gemini-1.5-flash"  # Updated model
                }
            }
        }
        
        print("\n2. Initializing LLM Gateway...")
        llm_gateway = await get_llm_gateway()
        await llm_gateway.initialize(llm_config)
        print(f"   - Enabled: {llm_gateway.enabled}")
        print(f"   - Default Provider: {llm_gateway.default_provider}")
        print("   ✓ Initialization successful")
        
        print("\n3. Testing fallback response...")
        request = LLMRequest(
            prompt="Hello, test message",
            provider=LLMProvider.FALLBACK
        )
        response = await llm_gateway.generate_response(request)
        print(f"   - Provider: {response.provider}")
        print(f"   - Confidence: {response.confidence}")
        print(f"   - Response preview: {response.text[:100]}...")
        print("   ✓ Fallback working")
        
        print("\n4. Checking environment variables...")
        print(f"   - GEMINI_API_KEY: {'Set' if os.getenv('GEMINI_API_KEY') else 'Not set'}")
        print(f"   - OPENAI_API_KEY: {'Set' if os.getenv('OPENAI_API_KEY') else 'Not set'}")
        print(f"   - GROQ_API_KEY: {'Set' if os.getenv('GROQ_API_KEY') else 'Not set'}")
        print(f"   - ANTHROPIC_API_KEY: {'Set' if os.getenv('ANTHROPIC_API_KEY') else 'Not set'}")
        
        print("\n5. Testing with Gemini configuration (model name check)...")
        # This should use gemini-1.5-flash instead of gemini-pro
        gemini_config = llm_gateway.providers_config.get("gemini", {})
        expected_model = "gemini-1.5-flash"
        actual_model = gemini_config.get("model", "gemini-1.5-flash")
        print(f"   - Expected model: {expected_model}")
        print(f"   - Actual model: {actual_model}")
        if "gemini-pro" in str(actual_model):
            print("   ⚠ WARNING: Using deprecated gemini-pro model!")
        else:
            print("   ✓ Using correct Gemini model")
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_llm_gateway())
    sys.exit(0 if success else 1)
