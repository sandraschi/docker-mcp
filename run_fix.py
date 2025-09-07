"""Run the FastMCP import fix script"""
import subprocess
import sys
import os

os.chdir(r"D:\Dev\repos\dockermcp")
result = subprocess.run([sys.executable, "fix_fastmcp_imports.py"], capture_output=True, text=True)
print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")
