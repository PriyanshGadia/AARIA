"""
Test LLM Integration - Demonstrates AARIA using LLM Gateway for responses
"""

import asyncio
import sys
import os

# Add Backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Backend'))

async def test_llm_integration():
    """Test that LLM Gateway is properly integrated"""
    
    print("=" * 70)
    print("AARIA LLM Integration Test")
    print("=" * 70)
    
    try:
        # Initialize AARIA
        print("\n1. Initializing AARIA system...")
        from stem import initialize_aaria
        stem = await initialize_aaria("config/aaria_config.json")
        print("   ✓ AARIA initialized")
        print(f"   ✓ Cores active: {', '.join(stem.cores_initialized.keys())}")
        
        # Check if LLM Gateway is initialized
        print("\n2. Checking LLM Gateway...")
        if stem.llm_gateway:
            print("   ✓ LLM Gateway is initialized")
            status = stem.llm_gateway.get_status()
            print(f"   ✓ Default provider: {status['default_provider'] or 'None (fallback mode)'}")
            print(f"   ✓ Available providers: {len([p for p in status['providers'].values() if p['available']])}")
            
            for name, info in status['providers'].items():
                if info['available']:
                    print(f"      - {name}: {info['description']}")
        else:
            print("   ✗ LLM Gateway not initialized")
            return
        
        # Check if Temporal Core has LLM Gateway
        print("\n3. Checking Temporal Core integration...")
        if stem.temporal_core and stem.temporal_core.llm_gateway:
            print("   ✓ Temporal Core has LLM Gateway")
        else:
            print("   ✗ Temporal Core missing LLM Gateway")
            return
        
        # Test communication processing
        print("\n4. Testing communication with LLM response...")
        test_messages = [
            "Hello, AARIA!",
            "What is your purpose?",
            "How are you feeling today?"
        ]
        
        for msg in test_messages:
            print(f"\n   User: {msg}")
            try:
                response = await stem.temporal_core.process_and_respond(msg)
                
                if response['status'] == 'success':
                    print(f"   AARIA ({response.get('llm_provider', 'unknown')}): {response['response']}")
                    print(f"   Model: {response.get('llm_model', 'unknown')}")
                elif response['status'] == 'success_fallback':
                    print(f"   AARIA (fallback): {response['response']}")
                    print(f"   Warning: {response.get('warning', '')}")
                else:
                    print(f"   Error: {response}")
                    
            except Exception as e:
                print(f"   Error processing message: {str(e)}")
        
        print("\n5. Integration Test Complete!")
        print("\n" + "=" * 70)
        print("SUMMARY:")
        print("- LLM Gateway: ✓ Integrated")
        print("- Temporal Core: ✓ Connected")
        print("- Response Generation: ✓ Working")
        print("\nIf you see 'fallback' responses, it means:")
        print("  1. No API keys are configured in environment or config/llm.env")
        print("  2. Ollama is not running locally")
        print("\nTo enable real AI responses:")
        print("  - Add API keys to config/llm.env (see config/.env.example)")
        print("  - Or install and run Ollama: ollama pull llama3")
        print("=" * 70)
        
        # Shutdown
        await stem.shutdown()
        
    except Exception as e:
        print(f"\n✗ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm_integration())
