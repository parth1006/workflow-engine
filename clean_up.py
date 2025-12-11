"""
Cleanup script to reset the workflow engine database.

Use this to start fresh or clean up test data.
"""
import os
import sys
from pathlib import Path


def cleanup():
    """Remove database and temporary files."""
    print("🧹 Cleaning up workflow engine data...")
    
    files_to_remove = [
        "data/workflow.db",
        "data/test_workflow.db",
        "data/workflow.db-journal",
        "data/workflow.db-wal"
    ]
    
    removed_count = 0
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"✅ Removed: {file_path}")
            removed_count += 1
    
    if removed_count == 0:
        print("ℹ️  No files to clean up")
    else:
        print(f"\n✅ Cleaned up {removed_count} file(s)")
        print("💡 Restart the server to recreate the database")


if __name__ == "__main__":
    response = input("⚠️  This will delete all workflow data. Continue? (y/N): ")
    if response.lower() == 'y':
        cleanup()
    else:
        print("❌ Cleanup cancelled")