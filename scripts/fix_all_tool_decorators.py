#!/usr/bin/env python3
"""
Comprehensive fix for FastMCP Tool decorator compatibility - Remove all 'returns' parameters
"""
import os
import re
import glob
from pathlib import Path

def remove_returns_from_tool_decorator(content):
    """Remove 'returns' parameter from @Tool decorators"""
    
    # Pattern to match @Tool decorator with parameters (multiline)
    pattern = r'(@Tool\s*\(\s*)((?:[^()]*|\([^)]*\))*)\s*\)'
    
    def fix_decorator(match):
        prefix = match.group(1)  # "@Tool("
        params_content = match.group(2)  # Everything between the parentheses
        
        # Find and remove the returns parameter (including nested objects)
        # This regex handles nested braces and multiline content
        returns_pattern = r',?\s*returns\s*=\s*\{(?:[^{}]|{[^{}]*})*\}(?:\s*,?)'
        
        # Remove returns parameter
        cleaned_params = re.sub(returns_pattern, '', params_content, flags=re.DOTALL)
        
        # Clean up any resulting formatting issues
        cleaned_params = re.sub(r',\s*,', ',', cleaned_params)  # Double commas
        cleaned_params = re.sub(r'^\s*,', '', cleaned_params)    # Leading comma
        cleaned_params = re.sub(r',\s*$', '', cleaned_params)    # Trailing comma
        
        return f"{prefix}{cleaned_params})"
    
    # Apply the fix
    result = re.sub(pattern, fix_decorator, content, flags=re.DOTALL)
    return result

def fix_file(file_path):
    """Fix a single file"""
    print(f"Processing: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Check if file contains @Tool decorators with returns
        if 'returns=' not in original_content:
            print(f"  No 'returns=' found, skipping")
            return False
            
        fixed_content = remove_returns_from_tool_decorator(original_content)
        
        if fixed_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"  ✅ Fixed Tool decorators")
            return True
        else:
            print(f"  No changes needed")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    """Main function"""
    print("🔧 Fixing FastMCP Tool decorator compatibility...")
    print("📋 Removing 'returns' parameters from all @Tool decorators\n")
    
    # Find all Python files in tools directories
    src_dir = Path("src")
    if not src_dir.exists():
        print("❌ Error: src directory not found")
        return
    
    # Find tool files
    tool_files = list(src_dir.rglob("*_tools.py"))
    
    if not tool_files:
        print("❌ No tool files found")
        return
    
    print(f"📁 Found {len(tool_files)} tool files to process:")
    for f in tool_files:
        print(f"   - {f}")
    print()
    
    fixed_count = 0
    
    # Process each file
    for tool_file in tool_files:
        if fix_file(tool_file):
            fixed_count += 1
    
    print(f"\n🎯 Summary:")
    print(f"   📂 Processed: {len(tool_files)} files")
    print(f"   ✅ Fixed: {fixed_count} files")
    print(f"   📝 No changes: {len(tool_files) - fixed_count} files")
    
    if fixed_count > 0:
        print(f"\n🚀 Next steps:")
        print(f"   1. Test docker-mcp startup: python -m dockermcp.server")
        print(f"   2. Check for any remaining compatibility issues")
        print(f"   3. Run integration tests if available")

if __name__ == "__main__":
    main()
