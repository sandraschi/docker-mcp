"""
Test runner script that saves output to the test_output directory.
Usage: python run_test_with_output.py [test_module]
"""
import sys
import os
import time
from pathlib import Path

def run_test(test_module=None):
    # Create test output directory
    test_output_dir = Path("test_output")
    test_output_dir.mkdir(exist_ok=True)
    
    # Create output filename with timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = test_output_dir / f"test_output_{timestamp}.log"
    
    # Build the test command
    cmd = [sys.executable, "-m", "pytest", "-v", "--log-cli-level=DEBUG"]
    if test_module:
        cmd.append(f"{test_module}.py")
    
    # Run the test and capture output
    print(f"Running test: {' '.join(cmd)}")
    print(f"Output will be saved to: {output_file}")
    
    try:
        import subprocess
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write command info
            f.write(f"# Test Run: {time.ctime()}\n")
            f.write(f"# Command: {' '.join(cmd)}\n\n")
            
            # Run the test
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )
            
            # Write output to file
            f.write(result.stdout)
            
        print(f"\nTest execution complete. Output saved to: {output_file}")
        print(f"Exit code: {result.returncode}")
        
        # Show last few lines of output
        print("\n=== Last 10 lines of output ===")
        with open(output_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(''.join(lines[-10:]))
            
    except Exception as e:
        print(f"Error running test: {str(e)}", file=sys.stderr)
        return 1
    
    return result.returncode

if __name__ == "__main__":
    test_module = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(run_test(test_module))
