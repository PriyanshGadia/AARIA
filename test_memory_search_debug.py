#!/usr/bin/env python3
"""
Debug test to check if memory search is working properly
"""
import sys
import asyncio
from pathlib import Path

# Add Backend to path
backend_path = Path(__file__).parent / "Backend"
sys.path.insert(0, str(backend_path))

async def test_memory_search_debug():
    """Debug memory search functionality"""
    print("=" * 70)
    print("Debug: Memory Search Test")
    print("=" * 70)
    
    try:
        from stem import AARIA_Stem
        
        print("\n1. Creating AARIA Stem instance...")
        stem = AARIA_Stem()
        
        print("\n2. Booting system...")
        await stem.boot()
        print("   ✓ System booted")
        
        print("\n3. Storing test memories with 'recent' tag...")
        
        # Store 3 memories
        await stem.memory.execute_command("store_memory", {
            "data": "User: Yash is my friend",
            "tier": "OWNER_CONFIDENTIAL",
            "tags": ["conversation", "user_input", "recent"],
            "priority": 0.6
        })
        print("   - Stored memory 1")
        
        await stem.memory.execute_command("store_memory", {
            "data": "AARIA: That's great!",
            "tier": "OWNER_CONFIDENTIAL",
            "tags": ["conversation", "ai_response", "recent"],
            "priority": 0.5
        })
        print("   - Stored memory 2")
        
        await stem.memory.execute_command("store_memory", {
            "data": "User: His birthday is in 4 days",
            "tier": "OWNER_CONFIDENTIAL",
            "tags": ["conversation", "user_input", "recent"],
            "priority": 0.6
        })
        print("   - Stored memory 3")
        
        await asyncio.sleep(0.5)
        
        print("\n4. Testing direct memory search with tags=['conversation', 'recent']...")
        search_result = await stem.memory.execute_command("search_memories", {
            "query": {"tags": ["conversation", "recent"]},
            "access_level": "owner_root",
            "max_results": 20
        })
        
        print(f"   Search result success: {search_result.get('success')}")
        print(f"   Total results: {search_result.get('total_results', 0)}")
        
        if search_result.get("success"):
            results = search_result.get("results", [])
            print(f"   Found {len(results)} memories:")
            for i, mem in enumerate(results, 1):
                print(f"     {i}. {mem.get('data', 'N/A')[:50]}...")
        else:
            print(f"   Error: {search_result.get('error')}")
        
        print("\n5. Testing retrieve_context method...")
        context = await stem.hive_mind.retrieve_context("Do you remember Yash?")
        print("   Retrieved context:")
        print("-" * 70)
        print(context)
        print("-" * 70)
        
        print("\n6. Shutting down...")
        await stem.shutdown()
        
        print("\n" + "=" * 70)
        print("Debug test complete")
        print("=" * 70)
            
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_memory_search_debug())
