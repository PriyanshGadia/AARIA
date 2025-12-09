#!/usr/bin/env python3
"""
Memory Reset Utility for AARIA
Safely deletes all persisted memories and resets the system to a clean state.

Usage:
    python reset_memory.py [--confirm]
    
Options:
    --confirm    Skip confirmation prompt and reset immediately
"""

import os
import sys
from pathlib import Path

# Memory storage files to delete
MEMORY_FILES = [
    "Backend/.aaria_config.db",
    "Backend/memory_store.enc",
    "Backend/.aaria_salts.json"
]

def reset_memory(confirm=False):
    """Reset all AARIA memory storage by deleting persistent files."""
    
    print("=" * 60)
    print("AARIA Memory Reset Utility")
    print("=" * 60)
    
    # Get script directory (repository root)
    repo_root = Path(__file__).parent
    
    # Find files that exist
    existing_files = []
    for file_path in MEMORY_FILES:
        full_path = repo_root / file_path
        if full_path.exists():
            existing_files.append(full_path)
    
    if not existing_files:
        print("\n✅ No memory files found. System is already clean.")
        return 0
    
    print(f"\nFound {len(existing_files)} memory file(s) to delete:")
    for file_path in existing_files:
        size = file_path.stat().st_size
        print(f"  - {file_path.relative_to(repo_root)} ({size} bytes)")
    
    # Confirm deletion
    if not confirm:
        print("\n⚠️  WARNING: This will permanently delete all memories!")
        print("   - All conversation history will be lost")
        print("   - All stored facts will be lost")
        print("   - AARIA will start fresh on next boot")
        
        response = input("\nAre you sure you want to continue? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("\n❌ Reset cancelled.")
            return 1
    
    # Delete files
    print("\n🗑️  Deleting memory files...")
    deleted_count = 0
    for file_path in existing_files:
        try:
            file_path.unlink()
            print(f"  ✓ Deleted: {file_path.relative_to(repo_root)}")
            deleted_count += 1
        except Exception as e:
            print(f"  ✗ Failed to delete {file_path.relative_to(repo_root)}: {e}")
    
    print(f"\n✅ Memory reset complete! Deleted {deleted_count} file(s).")
    print("\nNext steps:")
    print("  1. Start AARIA normally")
    print("  2. New conversations will use TEMPORAL_CACHE (ephemeral)")
    print("  3. Old memories will be cleaned up automatically on each boot")
    
    return 0

def main():
    """Main entry point."""
    confirm = "--confirm" in sys.argv
    sys.exit(reset_memory(confirm))

if __name__ == "__main__":
    main()
