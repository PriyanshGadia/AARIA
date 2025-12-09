#!/usr/bin/env python3
"""
Debug script to check cleanup logic
"""
import sys
import asyncio
from pathlib import Path

# Add Backend to path
backend_path = Path(__file__).parent / "Backend"
sys.path.insert(0, str(backend_path))

async def debug_cleanup():
    """Debug cleanup logic"""
    print("=" * 70)
    print("Debug: Cleanup Logic")
    print("=" * 70)
    
    try:
        from stem import AARIA_Stem
        
        print("\n1. Booting AARIA and storing memories...")
        stem = AARIA_Stem()
        await stem.boot()
        
        await stem.hive_mind.store_interaction("Test", "Response")
        await asyncio.sleep(0.2)
        
        print("\n2. Searching for conversation memories...")
        result = await stem.memory.execute_command("search_memories", {
            "query": {"tags": ["conversation"]},
            "access_level": "owner_root",
            "max_results": 10
        })
        
        if result.get("success"):
            memories = result.get("results", [])
            print(f"   Found {len(memories)} memories\n")
            
            for mem in memories:
                metadata = mem.get("metadata", {})
                print(f"   Memory ID: {mem.get('memory_id')}")
                
                # Check tier
                tier_value = None
                if hasattr(metadata, 'tier'):
                    tier_value = str(metadata.tier)
                    print(f"   - tier (attr, str): '{tier_value}'")
                    print(f"   - tier (attr, raw): {metadata.tier}")
                elif isinstance(metadata, dict):
                    tier_value = str(metadata.get('tier', 'N/A'))
                    print(f"   - tier (dict): '{tier_value}'")
                
                # Check if it matches
                if tier_value:
                    tier_upper = tier_value.upper()
                    is_temporal = 'TEMPORAL' in tier_upper
                    print(f"   - tier_upper: '{tier_upper}'")
                    print(f"   - is_temporal: {is_temporal}")
                print()
        
        await stem.shutdown()
            
    except Exception as e:
        print(f"\n✗ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_cleanup())
