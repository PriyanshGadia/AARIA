#!/usr/bin/env python3
"""
Test script to verify Gemini API endpoint fix
"""
import sys
import os
import asyncio
from pathlib import Path

# Add Backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

async def test_gemini_endpoint():
    """Test that Gemini uses the correct API endpoint"""
    print("=" * 60)
    print("Testing Gemini API Endpoint Fix")
    print("=" * 60)
    
    try:
        from llm_gateway import LLMGateway, LLMRequest, LLMProvider
        import aiohttp
        from unittest.mock import patch, AsyncMock, MagicMock
        
        print("\n1. Testing Gemini API endpoint URL...")
        
        # Create gateway instance
        gateway = LLMGateway()
        gateway.enabled = True
        gateway.default_provider = LLMProvider.GEMINI
        gateway.providers_config = {
            "gemini": {
                "model": "gemini-1.5-flash"
            }
        }
        
        # Mock the API key
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key'}):
            # Create a mock response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "candidates": [{
                    "content": {
                        "parts": [{"text": "Test response"}]
                    },
                    "finishReason": "STOP"
                }],
                "usageMetadata": {
                    "totalTokenCount": 10
                }
            })
            
            # Mock aiohttp.ClientSession
            mock_session = MagicMock()
            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.__aexit__ = AsyncMock(return_value=None)
            mock_session.post.return_value = mock_post
            
            mock_session_context = MagicMock()
            mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_context.__aexit__ = AsyncMock(return_value=None)
            
            with patch('aiohttp.ClientSession', return_value=mock_session_context):
                request = LLMRequest(
                    prompt="Test prompt",
                    provider=LLMProvider.GEMINI
                )
                
                response = await gateway._gemini_llm(request)
                
                # Check that the API was called with the correct URL
                mock_session.post.assert_called_once()
                call_args = mock_session.post.call_args
                
                # Extract URL more explicitly with proper error handling
                try:
                    url = call_args.args[0] if call_args.args else call_args.kwargs.get('url', '')
                except (AttributeError, IndexError):
                    url = str(call_args)
                
                print(f"   - API URL called: {url}")
                
                # Verify it uses v1 API (v1beta had model compatibility issues)
                if '/v1/models/' in url and '/v1beta/' not in url:
                    print("   ✓ Correct API version (v1) is used")
                else:
                    print(f"   ✗ WRONG API version! URL: {url}")
                    return False
                
                # Verify model name
                if 'gemini-1.5-flash' in url:
                    print("   ✓ Correct model name (gemini-1.5-flash)")
                else:
                    print(f"   ✗ WRONG model name in URL: {url}")
                    return False
                
                print(f"   - Response text: {response.text}")
                print(f"   - Provider: {response.provider}")
                
        print("\n2. Testing automatic Ollama fallback...")
        
        # Test that when Gemini fails, it tries Ollama
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key'}):
            # Mock failed Gemini response
            mock_response_fail = MagicMock()
            mock_response_fail.status = 404
            mock_response_fail.text = AsyncMock(return_value='{"error": "not found"}')
            
            mock_session = MagicMock()
            mock_post_fail = AsyncMock()
            mock_post_fail.__aenter__ = AsyncMock(return_value=mock_response_fail)
            mock_post_fail.__aexit__ = AsyncMock(return_value=None)
            mock_session.post.return_value = mock_post_fail
            mock_session.get = MagicMock()  # For Ollama check
            
            mock_session_context = MagicMock()
            mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_context.__aexit__ = AsyncMock(return_value=None)
            
            with patch('aiohttp.ClientSession', return_value=mock_session_context):
                request = LLMRequest(
                    prompt="Test prompt",
                    provider=LLMProvider.GEMINI
                )
                
                # This should try Gemini, fail, then try Ollama fallback
                response = await gateway._gemini_llm_with_fallback(request)
                
                # Should return fallback response (confidence 0.1)
                print(f"   - Fallback confidence: {response.confidence}")
                print(f"   - Fallback provider: {response.provider}")
                
                if response.confidence <= 0.2:
                    print("   ✓ Automatic fallback triggered correctly")
                else:
                    print("   ✗ Fallback not triggered!")
                    return False
        
        print("\n" + "=" * 60)
        print("✓ All Gemini fix tests passed!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_gemini_endpoint())
    sys.exit(0 if success else 1)
