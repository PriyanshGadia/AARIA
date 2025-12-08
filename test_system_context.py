#!/usr/bin/env python3
"""
Test script to verify system context awareness fix
"""
import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime

# Add Backend to path
backend_path = Path(__file__).parent / "Backend"
sys.path.insert(0, str(backend_path))

async def test_system_context():
    """Test that the parietal core provides system context correctly"""
    print("=" * 60)
    print("Testing System Context Awareness Fix")
    print("=" * 60)
    
    try:
        # Import required modules
        from parietal_core import ParietalCore
        
        print("\n1. Creating Parietal Core instance...")
        parietal = ParietalCore()
        
        print("\n2. Starting Parietal Core...")
        await parietal.start()
        
        print("\n3. Testing get_system_context() method...")
        context = await parietal.get_system_context()
        
        print("\n4. System Context Retrieved:")
        print("-" * 60)
        print(context)
        print("-" * 60)
        
        # Verify the context contains expected information
        print("\n5. Validating context content...")
        
        checks = {
            "Contains CURRENT DATE": "CURRENT DATE:" in context,
            "Contains CURRENT TIME": "CURRENT TIME:" in context,
            "Contains DEVICE": "DEVICE:" in context,
            "Date format is valid": any(month in context for month in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]),
        }
        
        all_passed = True
        for check_name, result in checks.items():
            status = "✓" if result else "✗"
            print(f"   {status} {check_name}")
            if not result:
                all_passed = False
        
        print("\n6. Stopping Parietal Core...")
        await parietal.stop()
        
        if all_passed:
            print("\n" + "=" * 60)
            print("✓ ALL TESTS PASSED - System Context is working correctly!")
            print("=" * 60)
            return True
        else:
            print("\n" + "=" * 60)
            print("✗ SOME TESTS FAILED")
            print("=" * 60)
            return False
            
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_system_context())
    sys.exit(0 if result else 1)
