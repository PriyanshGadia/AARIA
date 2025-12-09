#!/usr/bin/env python3
"""
Test to simulate the user's exact scenario
"""
import sys
import asyncio
from pathlib import Path

# Add Backend to path
backend_path = Path(__file__).parent / "Backend"
sys.path.insert(0, str(backend_path))

async def test_user_scenario():
    """Simulate the exact user scenario"""
    print("=" * 70)
    print("Simulating User Scenario")
    print("=" * 70)
    
    try:
        from stem import AARIA_Stem
        
        print("\n=== SESSION 1 ===")
        print("1. Creating AARIA Stem instance...")
        stem = AARIA_Stem()
        
        print("2. Booting system...")
        await stem.boot()
        
        print("\n3. User: Yash is my friend")
        await stem.memory.execute_command("store_memory", {
            "data": "User: Yash is my friend",
            "tier": "OWNER_CONFIDENTIAL",
            "tags": ["conversation", "user_input", "recent"],
            "priority": 0.6
        })
        await stem.memory.execute_command("store_memory", {
            "data": "AARIA: Thank you for letting me know!",
            "tier": "OWNER_CONFIDENTIAL",
            "tags": ["conversation", "ai_response", "recent"],
            "priority": 0.5
        })
        
        print("4. User: His birthday is coming up in 4 days")
        await stem.memory.execute_command("store_memory", {
            "data": "User: His birthday is coming up in 4 days",
            "tier": "OWNER_CONFIDENTIAL",
            "tags": ["conversation", "user_input", "recent"],
            "priority": 0.6
        })
        await stem.memory.execute_command("store_memory", {
            "data": "AARIA: That's great to hear!",
            "tier": "OWNER_CONFIDENTIAL",
            "tags": ["conversation", "ai_response", "recent"],
            "priority": 0.5
        })
        
        await asyncio.sleep(0.5)
        
        print("\n5. Testing context retrieval for 'Set a reminder and suggest gift ideas'")
        context = await stem.hive_mind.retrieve_context("Set a reminder and suggest gift ideas")
        print("Context:")
        print("-" * 70)
        print(context)
        print("-" * 70)
        
        print("\n6. Shutting down session 1...")
        await stem.shutdown()
        
        print("\n\n=== SESSION 2 (Simulating restart) ===")
        print("1. Creating new AARIA Stem instance...")
        stem2 = AARIA_Stem()
        
        print("2. Booting system (should load persisted memories)...")
        await stem2.boot()
        
        # Check how many memories loaded
        mem_status = await stem2.memory.get_core_status()
        total_mems = mem_status.get('storage_summary', {}).get('total_memories', 0)
        print(f"   Loaded {total_mems} memories from previous session")
        
        await asyncio.sleep(0.5)
        
        print("\n3. Testing context retrieval for 'Do you remember yash?'")
        context2 = await stem2.hive_mind.retrieve_context("Do you remember yash?")
        print("Context:")
        print("-" * 70)
        print(context2)
        print("-" * 70)
        
        # Check if Yash is mentioned
        if "yash" in context2.lower():
            print("\n✓ SUCCESS: Yash is mentioned in context!")
        else:
            print("\n✗ FAILURE: Yash is NOT mentioned in context!")
            print("   This is the bug the user is experiencing.")
        
        print("\n4. Shutting down session 2...")
        await stem2.shutdown()
        
        print("\n" + "=" * 70)
        print("Test complete")
        print("=" * 70)
            
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_user_scenario())
