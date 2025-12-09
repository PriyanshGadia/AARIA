#!/usr/bin/env python3
"""
Test to verify that old session memories don't pollute new sessions
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
import time

# Add Backend to path
backend_path = Path(__file__).parent / "Backend"
sys.path.insert(0, str(backend_path))

async def test_session_isolation():
    """Test that old memories from previous sessions are filtered out"""
    print("=" * 70)
    print("Testing Session Isolation - Old Memories Filter")
    print("=" * 70)
    
    try:
        from stem import AARIA_Stem
        
        print("\n=== SIMULATING OLD SESSION ===")
        print("1. Creating old memories about 'Yash'...")
        stem_old = AARIA_Stem()
        await stem_old.boot()
        
        # Store memories that should be filtered out
        for i in range(3):
            await stem_old.memory.execute_command("store_memory", {
                "data": f"User: OLD SESSION - Yash is my friend (message {i+1})",
                "tier": "OWNER_CONFIDENTIAL",
                "tags": ["conversation", "user_input", "recent"],
                "priority": 0.6
            })
        
        print("   Stored 3 old session memories")
        old_session_time = stem_old.start_time
        print(f"   Old session started at: {old_session_time}")
        await stem_old.shutdown()
        
        # Wait a moment to ensure different session times
        print("\n2. Waiting 0.2 seconds to ensure different session times...")
        await asyncio.sleep(0.2)
        
        print("\n=== NEW SESSION (NOW) ===")
        print("3. Starting fresh AARIA instance...")
        stem_new = AARIA_Stem()
        await stem_new.boot()
        new_session_time = stem_new.start_time
        print(f"   New session started at: {new_session_time}")
        print(f"   Time difference: {(new_session_time - old_session_time).total_seconds():.2f} seconds")
        
        # Small delay to ensure everything is initialized
        await asyncio.sleep(0.1)
        
        print("\n4. Testing context retrieval for 'Hi there'...")
        context = await stem_new.hive_mind.retrieve_context("Hi there")
        
        print("\n5. Retrieved Context:")
        print("-" * 70)
        print(context if context else "(empty)")
        print("-" * 70)
        
        print("\n6. Validation:")
        if "Yash" in context or "OLD SESSION" in context:
            print("   ✗ FAILURE: Old session memories (Yash) are leaking into new session!")
            print("   This is the bug the user reported.")
            success = False
        else:
            print("   ✓ SUCCESS: Old session memories are properly filtered!")
            print("   New session starts clean without old context.")
            success = True
        
        # Now test that current session memories DO work
        print("\n7. Testing current session memory retention...")
        await stem_new.memory.execute_command("store_memory", {
            "data": "User: My name is Alice",
            "tier": "OWNER_CONFIDENTIAL",
            "tags": ["conversation", "user_input", "recent"],
            "priority": 0.6
        })
        
        await asyncio.sleep(0.1)
        
        context2 = await stem_new.hive_mind.retrieve_context("What's my name?")
        print("\n8. Retrieved Context for current session:")
        print("-" * 70)
        print(context2)
        print("-" * 70)
        
        if "Alice" in context2:
            print("\n   ✓ Current session memories work correctly!")
        else:
            print("\n   ✗ WARNING: Current session memories not appearing!")
            success = False
        
        # Also verify OLD SESSION is NOT in current context
        if "OLD SESSION" in context2 or "Yash" in context2:
            print("   ✗ FAILURE: Old session still leaking!")
            success = False
        
        await stem_new.shutdown()
        
        if success:
            print("\n" + "=" * 70)
            print("✓ SESSION ISOLATION TEST PASSED!")
            print("Old memories filtered, current memories retained.")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            print("✗ SESSION ISOLATION TEST FAILED!")
            print("=" * 70)
        
        return success
            
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_session_isolation())
    sys.exit(0 if result else 1)
