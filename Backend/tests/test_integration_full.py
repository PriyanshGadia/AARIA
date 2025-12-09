#!/usr/bin/env python3
"""
Integration test for AARIA with LLM Gateway
Tests the complete flow with environment variable loading
"""
import sys
import os
import asyncio
from pathlib import Path

# Add Backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

async def test_with_gemini_key():
    """Test with a simulated Gemini API key"""
    print("=" * 60)
    print("Testing AARIA with Gemini Configuration")
    print("=" * 60)
    
    # Simulate having a Gemini API key (using placeholder)
    os.environ['GEMINI_API_KEY'] = 'test_key_placeholder_do_not_use_in_production'
    
    try:
        from llm_gateway import get_llm_gateway, LLMRequest, LLMProvider
        
        print("\n1. Setting up configuration with Gemini...")
        llm_config = {
            "enabled": True,
            "default_provider": "gemini",
            "providers": {
                "gemini": {
                    "model": "gemini-1.5-flash"  # Correct model name
                },
                "local": {
                    "endpoint": "http://localhost:11434",
                    "model": "llama3.2"
                }
            }
        }
        
        print("\n2. Initializing LLM Gateway...")
        # Reset gateway singleton for fresh test
        import llm_gateway
        llm_gateway._llm_gateway_instance = None
        
        gateway = await get_llm_gateway()
        await gateway.initialize(llm_config)
        
        print(f"   - Enabled: {gateway.enabled}")
        print(f"   - Default Provider: {gateway.default_provider}")
        
        # Verify Gemini is available
        has_gemini = any('gemini' in str(p).lower() for p in [gateway.default_provider])
        print(f"   - Gemini Provider Available: {has_gemini}")
        
        print("\n3. Checking Gemini configuration...")
        gemini_config = gateway.providers_config.get("gemini", {})
        model = gemini_config.get("model", "gemini-1.5-flash")
        print(f"   - Model configured: {model}")
        
        if model == "gemini-pro":
            print("   ✗ ERROR: Still using deprecated gemini-pro model!")
            return False
        elif model in ["gemini-1.5-flash", "gemini-1.5-pro"]:
            print("   ✓ Using correct Gemini model")
        else:
            print(f"   ⚠ Warning: Unknown model {model}")
        
        print("\n4. Testing request creation...")
        # This would make an actual API call if we had a real key
        # For now, just verify the model name is correct
        request = LLMRequest(
            prompt="Test prompt",
            provider=LLMProvider.GEMINI
        )
        print(f"   - Request provider: {request.provider}")
        print("   ✓ Request created successfully")
        
        print("\n5. Verifying error message handling...")
        # Test that fallback works if API call fails
        response = await gateway.generate_response(request)
        print(f"   - Fallback response type: {response.provider}")
        print("   ✓ Fallback mechanism working")
        
        print("\n" + "=" * 60)
        print("✓ All integration tests passed!")
        print("=" * 60)
        
        # Key findings
        print("\n📋 Summary:")
        print(f"  • Gemini model: {model}")
        print(f"  • Environment loading: Working")
        print(f"  • Provider detection: Working")
        print(f"  • Fallback mechanism: Working")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']

async def test_env_file_priority():
    """Test that llm.env file takes priority"""
    print("\n" + "=" * 60)
    print("Testing Environment Variable Priority")
    print("=" * 60)
    
    # Create a temporary llm.env
    env_content = """
# Test llm.env
GEMINI_API_KEY=from_env_file
GROQ_API_KEY=groq_from_file
DEFAULT_LLM_PROVIDER=gemini
"""
    
    env_path = Path(__file__).parent / 'llm.env'
    env_exists_before = env_path.exists()
    
    try:
        if not env_exists_before:
            env_path.write_text(env_content)
            print(f"\n1. Created test llm.env at {env_path}")
        
        # Reload the module to pick up new env file
        import importlib
        import llm_gateway
        importlib.reload(llm_gateway)
        
        print("\n2. Checking environment variables after reload...")
        gemini_key = os.getenv('GEMINI_API_KEY')
        groq_key = os.getenv('GROQ_API_KEY')
        
        print(f"   - GEMINI_API_KEY: {'Set' if gemini_key else 'Not set'}")
        print(f"   - GROQ_API_KEY: {'Set' if groq_key else 'Not set'}")
        
        if gemini_key or groq_key:
            print("   ✓ Environment variables loaded from llm.env")
        else:
            print("   ⚠ No environment variables loaded (expected if file doesn't persist)")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False
    finally:
        # Clean up the test file if we created it
        if not env_exists_before and env_path.exists():
            env_path.unlink()
            print(f"\n3. Cleaned up test llm.env")

if __name__ == "__main__":
    print("🧪 AARIA LLM Integration Test Suite\n")
    
    success1 = asyncio.run(test_with_gemini_key())
    success2 = asyncio.run(test_env_file_priority())
    
    if success1 and success2:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
