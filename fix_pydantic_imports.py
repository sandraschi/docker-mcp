#!/usr/bin/env python3
"""
Fix Pydantic 2.x import compatibility for docker-mcp.

This script updates all ValidationInfo imports from the old Pydantic 1.x syntax
to the new Pydantic 2.x syntax.
"""

import os
import sys
from pathlib import Path

def fix_imports_in_file(filepath: Path) -> bool:
    """Fix ValidationInfo import in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix the import statement
        content = content.replace(
            'from pydantic.functional_validators import ValidationInfo',
            'from pydantic import ValidationInfo'
        )
        
        # Write back if changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Main function to fix all model files."""
    repo_root = Path(__file__).parent
    model_files = [
        "src/dockermcp/tools/containers/container_models.py",
        "src/dockermcp/tools/images/image_models.py", 
        "src/dockermcp/tools/networks/network_models.py",
        "src/dockermcp/tools/volumes/volume_models.py",
        "src/dockermcp/tools/system/system_models.py",
        "src/dockermcp/tools/compose/compose_models.py"
    ]
    
    fixed_files = []
    for file_path in model_files:
        full_path = repo_root / file_path
        if full_path.exists():
            if fix_imports_in_file(full_path):
                fixed_files.append(file_path)
                print(f"✅ Fixed: {file_path}")
            else:
                print(f"ℹ️  No changes needed: {file_path}")
        else:
            print(f"❌ File not found: {file_path}")
    
    if fixed_files:
        print(f"\n🎯 Successfully fixed {len(fixed_files)} files.")
        print("✅ Pydantic 2.x compatibility restored!")
    else:
        print("\n❌ No files were fixed. Check if imports already correct.")
    
    return 0 if fixed_files else 1

if __name__ == "__main__":
    sys.exit(main())
