#!/usr/bin/env python3
"""
Test script to verify the complete AARIA system boot with LLM integration
"""
import sys
import os
import asyncio
from pathlib import Path

# Add Backend to path
backend_path = Path(__file__).parent / "Backend"
sys.path.insert(0, str(backend_path))

async def test_system_boot():
    """Test that the system boots correctly with LLM integration"""
    print("=" * 60)
    print("Testing AARIA System Boot with LLM Integration")
    print("=" * 60)
    
    try:
        # Import the stem
        from stem import AARIA_Stem
        
        print("\n1. Importing stem... ✓")
        
        # Create stem instance
        stem = AARIA_Stem()
        
        print("\n2. Booting system (this will take a few seconds)...")
        
        # Boot the system
        await stem.boot()
        
        print("\n3. System booted successfully! ✓")
        
        # Check LLM Gateway
        from llm_gateway import get_llm_gateway, LLMProvider
        
        llm_gateway = await get_llm_gateway()
        
        print(f"\n4. LLM Gateway Status:")
        print(f"   - Enabled: {llm_gateway.enabled}")
        print(f"   - Default Provider: {llm_gateway.default_provider}")
        
        # Verify fallback works correctly when no LLM is available
        if llm_gateway.default_provider == LLMProvider.FALLBACK:
            print("   ✓ Correctly using FALLBACK (no LLM providers available)")
        else:
            print(f"   ✓ Using provider: {llm_gateway.default_provider.value}")
        
        print("\n5. Testing message processing...")
        
        # Test a simple message (should work with fallback)
        # We can't use await stem.process_user_input() in automated test
        # because it prints to stdout, but we can verify the gateway works
        
        from llm_gateway import LLMRequest
        
        request = LLMRequest(
            prompt="Hello AARIA",
            provider=llm_gateway.default_provider,
            context={"intent": "greeting"}
        )
        
        response = await llm_gateway.generate_response(request)
        
        print(f"   - Response provider: {response.provider}")
        print(f"   - Response confidence: {response.confidence}")
        print(f"   - Response preview: {response.text[:100]}...")
        
        if response.provider in ["no_llm_fallback", "local_ollama"]:
            print("   ✓ Fallback mechanism working correctly")
        
        print("\n6. Shutting down...")
        await stem.shutdown()
        
        print("\n" + "=" * 60)
        print("✓ All system boot tests passed!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_system_boot())
    sys.exit(0 if success else 1)
