"""
Test runner script that captures output to a file.

Usage:
    python -m tests.run_tests [test_module] [output_file]

Example:
    python -m tests.run_tests test_hello_world test_output.log
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime

def run_tests(test_module=None, output_file=None):
    """Run tests and capture output to a file.
    
    Args:
        test_module: Specific test module to run (e.g., 'test_hello_world')
        output_file: Path to output file (default: test_output_<timestamp>.log)
    """
    # Set default output file if not provided
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"test_output_{timestamp}.log"
    
    # Build the pytest command
    cmd = ["pytest", "-v"]
    if test_module:
        cmd.append(f"tests/{test_module}.py")
    else:
        cmd.append("tests/")
    
    print(f"Running tests with command: {' '.join(cmd)}")
    print(f"Output will be saved to: {output_file}")
    
    # Run the tests and capture output
    with open(output_file, 'w', encoding='utf-8') as f:
        # Run pytest with both stdout and stderr captured
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8'
        )
        
        # Write the output to file
        f.write(f"Command: {' '.join(cmd)}\n")
        f.write(f"Exit code: {result.returncode}\n")
        f.write("-" * 80 + "\n")
        f.write(result.stdout)
    
    print(f"Test execution complete. Output saved to {output_file}")
    print(f"Exit code: {result.returncode}")
    return result.returncode

if __name__ == "__main__":
    # Parse command line arguments
    test_module = sys.argv[1] if len(sys.argv) > 1 else None
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    sys.exit(run_tests(test_module, output_file))
