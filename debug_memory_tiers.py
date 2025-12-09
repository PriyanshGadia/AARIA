#!/usr/bin/env python3
"""
Debug script to check what tier is being used for memories
"""
import sys
import asyncio
from pathlib import Path

# Add Backend to path
backend_path = Path(__file__).parent / "Backend"
sys.path.insert(0, str(backend_path))

async def debug_memory_tiers():
    """Debug what tiers are being used"""
    print("=" * 70)
    print("Debug: Memory Tier Assignment")
    print("=" * 70)
    
    try:
        from stem import AARIA_Stem
        
        print("\n1. Booting AARIA...")
        stem = AARIA_Stem()
        await stem.boot()
        
        print("\n2. Storing test memories...")
        await stem.hive_mind.store_interaction("Test message", "Test response")
        
        await asyncio.sleep(0.2)
        
        print("\n3. Searching for conversation memories...")
        result = await stem.memory.execute_command("search_memories", {
            "query": {"tags": ["conversation"]},
            "access_level": "owner_root",
            "max_results": 10
        })
        
        if result.get("success"):
            memories = result.get("results", [])
            print(f"   Found {len(memories)} memories")
            
            for i, mem in enumerate(memories[:3], 1):
                metadata = mem.get("metadata", {})
                print(f"\n   Memory {i}:")
                print(f"   - memory_id: {mem.get('memory_id', 'N/A')}")
                
                # Try different ways to get tier
                if hasattr(metadata, 'tier'):
                    print(f"   - tier (attribute): {metadata.tier}")
                    print(f"   - tier (str): {str(metadata.tier)}")
                elif isinstance(metadata, dict):
                    print(f"   - tier (dict): {metadata.get('tier', 'N/A')}")
                
                # Check tags
                if hasattr(metadata, 'tags'):
                    print(f"   - tags: {metadata.tags}")
                elif isinstance(metadata, dict):
                    print(f"   - tags: {metadata.get('tags', [])}")
        
        await stem.shutdown()
            
    except Exception as e:
        print(f"\n✗ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_memory_tiers())
