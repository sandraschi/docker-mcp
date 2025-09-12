import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing basic import...")
try:
    from dockermcp.tools import containers
    print("✅ containers import successful")
except Exception as e:
    print(f"❌ containers import failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from dockermcp.tools import images  
    print("✅ images import successful")
except Exception as e:
    print(f"❌ images import failed: {e}")
    import traceback
    traceback.print_exc()
