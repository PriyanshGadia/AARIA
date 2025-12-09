#!/usr/bin/env python3
"""
Test to verify temporal cache cleanup fixes the "hardcoded" information issue
"""
import sys
import asyncio
from pathlib import Path

# Add Backend to path
backend_path = Path(__file__).parent / "Backend"
sys.path.insert(0, str(backend_path))

async def test_temporal_cache_cleanup():
    """Test that temporal cache memories are cleaned up on boot"""
    print("=" * 70)
    print("Testing Temporal Cache Cleanup - No Hardcoded Information")
    print("=" * 70)
    
    try:
        from stem import AARIA_Stem
        
        print("\n=== SESSION 1: Create conversation memories ===")
        print("1. Booting AARIA and creating conversation...")
        stem1 = AARIA_Stem()
        await stem1.boot()
        
        # Check memory count
        mem_status = await stem1.memory.get_core_status()
        initial_count = mem_status.get('storage_summary', {}).get('total_memories', 0)
        print(f"   Initial memories: {initial_count}")
        
        # Store some conversation memories (will be TEMPORAL_CACHE)
        await stem1.hive_mind.store_interaction("Yash is my friend", "That's great!")
        await stem1.hive_mind.store_interaction("His birthday is in 4 days", "I'll note that")
        
        await asyncio.sleep(0.2)
        
        # Check memory count after storing
        mem_status = await stem1.memory.get_core_status()
        after_conversation = mem_status.get('storage_summary', {}).get('total_memories', 0)
        added = after_conversation - initial_count
        print(f"   After conversation: {after_conversation} (+{added} memories)")
        
        await stem1.shutdown()
        
        print("\n=== SESSION 2: Boot and check cleanup ===")
        print("2. Booting new AARIA instance (should clean up temporal cache)...")
        stem2 = AARIA_Stem()
        await stem2.boot()
        
        # Check memory count after cleanup
        mem_status2 = await stem2.memory.get_core_status()
        after_cleanup = mem_status2.get('storage_summary', {}).get('total_memories', 0)
        print(f"   After cleanup: {after_cleanup}")
        
        # Verify cleanup worked
        if after_cleanup <= initial_count:
            print(f"\n   ✓ SUCCESS: Temporal cache cleaned up!")
            print(f"   Old conversation memories removed")
            success = True
        else:
            print(f"\n   ✗ FAILURE: Memories still present ({after_cleanup} > {initial_count})")
            print(f"   Temporal cache NOT cleaned properly")
            success = False
        
        # Test that context is clean
        print("\n3. Testing context retrieval...")
        context = await stem2.hive_mind.retrieve_context("Hi there")
        
        if "Yash" in context or "yash" in context.lower():
            print("   ✗ FAILURE: 'Yash' still appears in context (HARDCODED)")
            success = False
        else:
            print("   ✓ SUCCESS: No hardcoded information in context")
        
        await stem2.shutdown()
        
        if success:
            print("\n" + "=" * 70)
            print("✓ TEMPORAL CACHE CLEANUP TEST PASSED!")
            print("No hardcoded information - each session starts fresh.")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            print("✗ TEMPORAL CACHE CLEANUP TEST FAILED!")
            print("=" * 70)
        
        return success
            
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_temporal_cache_cleanup())
    sys.exit(0 if result else 1)
