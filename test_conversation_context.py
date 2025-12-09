#!/usr/bin/env python3
"""
Test to verify conversation context retention fix
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# Add Backend to path
backend_path = Path(__file__).parent / "Backend"
sys.path.insert(0, str(backend_path))

async def test_conversation_context():
    """Test that recent conversation history is properly retrieved"""
    print("=" * 70)
    print("Testing Conversation Context Retention")
    print("=" * 70)
    
    try:
        from stem import AARIA_Stem
        
        print("\n1. Creating AARIA Stem instance...")
        stem = AARIA_Stem()
        
        print("\n2. Booting system...")
        await stem.boot()
        print("   ✓ System booted")
        
        print("\n3. Simulating conversation turns...")
        
        # Calculate dynamic date for birthday (4 days from now)
        future_date = datetime.now() + timedelta(days=4)
        birthday_date_str = future_date.strftime("%B %d, %Y")
        
        # Store some conversation memories
        print("   - Storing: User says 'Yash is my friend'")
        await stem.memory.execute_command("store_memory", {
            "data": "User: Yash is my friend",
            "tier": "OWNER_CONFIDENTIAL",
            "tags": ["conversation", "user_input", "recent"],
            "priority": 0.6
        })
        
        print("   - Storing: AARIA acknowledges")
        await stem.memory.execute_command("store_memory", {
            "data": "AARIA: That's great to hear! Friends are important.",
            "tier": "OWNER_CONFIDENTIAL",
            "tags": ["conversation", "ai_response", "recent"],
            "priority": 0.5
        })
        
        print("   - Storing: User says 'His birthday is in 4 days'")
        await stem.memory.execute_command("store_memory", {
            "data": "User: His birthday is coming in 4 days",
            "tier": "OWNER_CONFIDENTIAL",
            "tags": ["conversation", "user_input", "recent"],
            "priority": 0.6
        })
        
        print(f"   - Storing: AARIA calculates date ({birthday_date_str})")
        await stem.memory.execute_command("store_memory", {
            "data": f"AARIA: Based on today, that would be {birthday_date_str}. Would you like me to set a reminder?",
            "tier": "OWNER_CONFIDENTIAL",
            "tags": ["conversation", "ai_response", "recent"],
            "priority": 0.5
        })
        
        # Short delay to ensure memories are stored
        await asyncio.sleep(0.5)
        
        print("\n4. Testing context retrieval with ambiguous input...")
        # Simulate user saying "Yes" (ambiguous without context)
        context = await stem.hive_mind.retrieve_context("Yes")
        
        print("\n5. Retrieved Context:")
        print("-" * 70)
        print(context)
        print("-" * 70)
        
        print("\n6. Validating context quality...")
        checks = {
            "Contains recent conversation": "RECENT CONVERSATION:" in context,
            "Mentions Yash": "yash" in context.lower(),
            "Includes birthday reference": "birthday" in context.lower(),
            "Shows conversation flow": context.count("User:") >= 1 and context.count("AARIA:") >= 1,
        }
        
        all_passed = True
        for check_name, result in checks.items():
            status = "✓" if result else "✗"
            print(f"   {status} {check_name}")
            if not result:
                all_passed = False
        
        print("\n7. Shutting down system...")
        await stem.shutdown()
        
        if all_passed:
            print("\n" + "=" * 70)
            print("✓ CONVERSATION CONTEXT TEST PASSED!")
            print("Recent conversation history is being properly retrieved.")
            print("=" * 70)
            return True
        else:
            print("\n" + "=" * 70)
            print("✗ SOME CHECKS FAILED")
            print("=" * 70)
            return False
            
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_conversation_context())
    sys.exit(0 if result else 1)
