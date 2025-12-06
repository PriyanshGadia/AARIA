import asyncio
from llm_gateway import get_llm_gateway, LLMRequest, LLMProvider

async def test():
    gateway = await get_llm_gateway()
    
    # Test fallback
    request = LLMRequest(prompt="Hello!", provider=LLMProvider.FALLBACK)
    response = await gateway.generate_response(request)
    print(f"Fallback: {response.text}")
    
    # Test local (if Ollama running)
    request = LLMRequest(prompt="What is AI?", provider=LLMProvider.LOCAL)
    response = await gateway.generate_response(request)
    print(f"Local: {response.text}")

asyncio.run(test())