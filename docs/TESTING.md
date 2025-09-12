# DockerMCP Testing Guide

## Table of Contents
- [Running Tests](#running-tests)
- [Test Output](#test-output)
- [Test Structure](#test-structure)
- [Writing New Tests](#writing-new-tests)
- [Troubleshooting](#troubleshooting)

## Running Tests

### Prerequisites
- Python 3.8+
- Docker Desktop (for container-related tests)
- Required Python packages (install with `pip install -r requirements-dev.txt`)

### MCP Server Requirements

For tests that interact with the MCP server:

1. **Required Setup**
   - A running MCP server is required for testing
   - The test suite is designed to test against a real server by default
   - Ensure the MCP server is running and accessible before running tests

2. **Server Configuration**
   - The test suite expects the MCP server to be running on `http://localhost:8000` by default
   - To change the server URL, set the `MCP_SERVER_URL` environment variable:
     ```powershell
     $env:MCP_SERVER_URL="http://your-server:port"
     ```

3. **Running Tests**
   - Start the MCP server before running tests:
     ```powershell
     # Start the MCP server (adjust command as needed)
     python -m dockermcp.main
     ```
   - In a separate terminal, run the tests:
     ```powershell
     python -m pytest tests/ -v
     ```

4. **Mocked Testing (Development Only)**
   - For development purposes only, you can use mocked responses
   - Set `MOCK_MODE=1` to enable mocked testing
   - Note: This should only be used for testing error handling and edge cases
   - Never rely solely on mocked tests for production validation

### Running All Tests

```powershell
# From the project root directory
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$outputFile = "tests/test_output/test_battery_${timestamp}.log"
python -m pytest tests/ -v > $outputFile 2>&1
Write-Output "Test output saved to: $outputFile"
```

### Running a Single Test File

```powershell
# Example: Running just the hello_world test
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$outputFile = "tests/test_output/test_hello_world_${timestamp}.log"
python -m pytest tests/test_hello_world.py -v > $outputFile 2>&1
Write-Output "Test output saved to: $outputFile"
```

### Running a Specific Test Function

```powershell
# Example: Running a specific test function
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$outputFile = "tests/test_output/specific_test_${timestamp}.log"
python -m pytest tests/test_module.py::test_function_name -v > $outputFile 2>&1
Write-Output "Test output saved to: $outputFile"
```

## Mock Testing

### When to Use Mock Testing

1. **Unit Testing**
   - Isolate components for testing
   - Test error conditions that are hard to reproduce
   - Speed up test execution

2. **Integration Testing**
   - Simulate external services
   - Test error handling and edge cases
   - Avoid dependencies on external systems

3. **CI/CD Pipelines**
   - Ensure consistent test environments
   - Reduce flaky tests
   - Speed up pipeline execution

### Mock Server Implementation

#### For MCP Repositories

1. **Basic Structure**
   ```python
   # tests/mocks/mock_mcp_server.py
   from http.server import HTTPServer, BaseHTTPRequestHandler
   import json
   import threading
   
   class MockMCPHandler(BaseHTTPRequestHandler):
       def do_GET(self):
           if self.path == '/health':
               self._send_json(200, {"status": "ok"})
           
       def _send_json(self, status, data):
           self.send_response(status)
           self.send_header('Content-type', 'application/json')
           self.end_headers()
           self.wfile.write(json.dumps(data).encode())
   
   class MockMCPServer:
       def __init__(self, port=8000):
           self.port = port
           self.server = HTTPServer(('localhost', port), MockMCPHandler)
           self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
       
       def start(self):
           self.thread.start()
       
       def stop(self):
           self.server.shutdown()
   ```

2. **Best Practices**
   - Keep mock server implementation in `tests/mocks/`
   - Support both sync and async testing
   - Include realistic response payloads
   - Implement error scenarios
   - Add logging for debugging

#### For AI/ML Projects (like MyAI)

1. **Mocking AI Services**
   ```python
   # tests/mocks/mock_ai_service.py
   from unittest.mock import Mock
   
   class MockAIService:
       def __init__(self):
           self.generate = Mock(return_value="Mocked AI response")
           self.embed = Mock(return_value=[0.1] * 1536)
   ```

2. **Key Considerations**
   - Mock API rate limits
   - Simulate response times
   - Include error cases (timeouts, rate limits)
   - Support different model behaviors

### Using the Mock Server in Tests

1. **Basic Usage**
   ```python
   def test_with_mock_server():
       with MockMCPServer(port=8001) as server:
           # Test code that interacts with the mock server
           response = requests.get("http://localhost:8001/health")
           assert response.status_code == 200
   ```

2. **Pytest Fixture**
   ```python
   # conftest.py
   import pytest
   from tests.mocks.mock_mcp_server import MockMCPServer
   
   @pytest.fixture(scope="module")
   def mock_server():
       server = MockMCPServer(port=8001)
       server.start()
       yield server
       server.stop()
   
   def test_with_fixture(mock_server):
       response = requests.get("http://localhost:8001/health")
       assert response.json()["status"] == "ok"
   ```

### Advanced Mocking Techniques

1. **Stateful Mocks**
   - Maintain state between requests
   - Support CRUD operations
   - Handle resource IDs and relationships

2. **Request Validation**
   - Verify request headers
   - Validate request bodies
   - Check authentication/authorization

3. **Performance Testing**
   - Simulate latency
   - Test with large datasets
   - Measure throughput

## Test Output

## Pytest in MCP Projects

### Key Pytest Features

1. **Test Discovery**
   - Files named `test_*.py` or `*_test.py` are automatically discovered
   - Functions prefixed with `test_` are recognized as test cases
   - Classes prefixed with `Test` (with no `__init__` method) group related tests

2. **Assertions**
   ```python
   # Basic assertions
   assert something == expected_value
   assert "substring" in full_string
   assert result is not None
   
   # Exception testing
   with pytest.raises(ExpectedException):
       function_that_raises()
   ```

### Fixtures

1. **Basic Fixture**
   ```python
   # conftest.py or test file
   import pytest
   
   @pytest.fixture
def sample_data():
    return {"key": "value"}

def test_example(sample_data):
    assert sample_data["key"] == "value"
   ```

2. **Fixture Scopes**
   - `function`: (default) Run once per test function
   - `class`: Run once per test class
   - `module`: Run once per module
   - `package`: Run once per package
   - `session`: Run once per test session

   ```python
   @pytest.fixture(scope="module")
   def db_connection():
       conn = create_db_connection()
       yield conn
       conn.close()
   ```

3. **Autouse Fixtures**
   ```python
   @pytest.fixture(autouse=True)
   def setup_environment():
       setup()
       yield
       teardown()
   ```

### Markers

1. **Built-in Markers**
   ```python
   @pytest.mark.skip(reason="Not implemented yet")
   def test_something():
       pass
   
   @pytest.mark.xfail(run=False)
   def test_experimental():
       assert False
   ```

2. **Custom Markers**
   ```python
   # Register in pytest.ini or conftest.py
   # pytest.ini:
   # [pytest]
   # markers =
   #     slow: marks tests as slow (deselect with '-m "not slow"')
   
   @pytest.mark.slow
def test_slow_integration():
    # This test will be skipped with -m "not slow"
    pass
   ```

### Parameterized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("3+5", 8),
    ("2+4", 6),
    ("6*9", 42, marks=pytest.mark.xfail),
])
def test_eval(input, expected):
    assert eval(input) == expected
```

### Mocking

1. **Using unittest.mock**
   ```python
   from unittest.mock import patch, MagicMock
   
   def test_mocking():
       with patch('module.function') as mock_func:
           mock_func.return_value = 42
           assert module.function() == 42
   ```

2. **Pytest-mock (recommended)**
   ```python
   def test_with_mocker(mocker):
       mock_func = mocker.patch('module.function')
       mock_func.return_value = 42
       assert module.function() == 42
   ```

### Test Organization

1. **Directory Structure**
   ```
   tests/
   ├── unit/
   │   ├── __init__.py
   │   └── test_module.py
   ├── integration/
   │   ├── __init__.py
   │   └── test_integration.py
   ├── conftest.py
   └── test_*.py
   ```

2. **Conftest.py**
   - Fixtures defined here are available to all tests in the same directory and subdirectories
   - Can have multiple conftest.py files in different directories

### Running Tests

```bash
# Run all tests
python -m pytest

# Run tests in parallel
python -m pytest -n auto

# Run tests with coverage
python -m pytest --cov=src --cov-report=term-missing

# Run specific tests
python -m pytest tests/unit/test_module.py::test_function

# Run tests matching a pattern
python -m pytest -k "test_create or test_update"

# Run only failed tests
python -m pytest --last-failed
```

### Best Practices

1. **Test Isolation**
   - Each test should be independent
   - Use fixtures to set up required state
   - Clean up after tests

2. **Naming Conventions**
   - Test files: `test_*.py` or `*_test.py`
   - Test functions: `test_*`
   - Test classes: `Test*`
   - Fixtures: descriptive names in snake_case

3. **Performance**
   - Use `--durations=N` to find slow tests
   - Mark slow tests with `@pytest.mark.slow`
   - Use `pytest-xdist` for parallel test execution

4. **Debugging**
   ```bash
   # Drop to PDB on failure
   python -m pytest --pdb
   
   # Print detailed traceback
   python -m pytest -v
   
   # Show all print statements
   python -m pytest -s
   ```

5. **Configuration**
   - Use `pytest.ini` for project-wide settings
   - Configure logging in `conftest.py`
   - Use `pytest.ini` to register custom markers

### Integration with MCP

1. **Testing MCP Tools**
   ```python
   from fastmcp.tools import Tool
   from fastmcp.exceptions import ToolException
   
   def test_tool_registration():
       @Tool(name="test_tool", description="A test tool")
       def test_tool():
           return {"status": "success"}
       
       assert test_tool() == {"status": "success"}
   ```

2. **Testing with Mocks**
   ```python
   def test_tool_with_mock(mocker):
       # Mock external dependencies
       mock_client = mocker.patch('module.Client')
       mock_client.return_value.get.return_value = {"data": "test"}
       
       # Test tool that uses the client
       result = my_tool()
       assert result == {"status": "success", "data": "test"}
   ```

### Continuous Integration

Example `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt
    - name: Run tests
      run: |
        python -m pytest --cov=src --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

### Common Issues and Solutions

1. **Test Dependencies**
   - Use `pytest-dependency` for test dependencies
   - Mark tests with `@pytest.mark.dependency()`

2. **Slow Tests**
   - Use `pytest-xdist` for parallel execution
   - Mark slow tests and skip them with `-m "not slow"`

3. **Flaky Tests**
   - Use `pytest-rerunfailures` to automatically retry failed tests
   - Add `--reruns 3` to retry failed tests 3 times

4. **Test Data**
   - Use `pytest-datadir` for test data files
   - Keep test data in `tests/data/`

### Advanced Topics

1. **Custom Markers**
   ```python
   # pytest.ini
   [pytest]
   markers =
       integration: marks tests as integration tests
       slow: marks tests as slow running
   ```

2. **Custom Fixtures**
   ```python
   @pytest.fixture
def mock_ai_service():
    class MockAIService:
        def generate(self, prompt):
            return f"Mock response to: {prompt}"
    return MockAIService()
   ```

3. **Pytest Plugins**
   - `pytest-cov`: Coverage reporting
   - `pytest-mock`: Better mocking support
   - `pytest-asyncio`: Async test support
   - `pytest-benchmark`: Performance testing

4. **Custom Hooks**
   ```python
   # conftest.py
def pytest_configure(config):
    # Add custom markers
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )
   ```

## Test Output

Test output is saved to the `tests/test_output/` directory with timestamps in the filenames for easy tracking.

### Output File Naming Convention
- `test_battery_<timestamp>.log` - Full test suite runs
- `test_<module>_<timestamp>.log` - Individual test module runs
- `specific_test_<timestamp>.log` - Specific test function runs

### Analyzing Test Output

1. **Check the exit code**:
   - `0` means all tests passed
   - `1` means one or more tests failed
   - `2` means test execution was interrupted
   - `3` means internal error
   - `4` means pytest was misused

2. **Common output sections**:
   - `ERROR` - Critical issues preventing test execution
   - `FAIL` - Test assertions that did not pass
   - `WARN` - Non-critical issues
   - `PASS` - Successfully passed tests
   - `SKIPPED` - Tests that were skipped
   - `XFAIL` - Expected failures
   - `XPASS` - Unexpectedly passing tests

## Test Structure

Tests are organized in the `tests/` directory following the project's package structure:

```
tests/
├── test_output/            # Test output files
├── test_hello_world.py     # Basic test example
├── test_container_*.py     # Container-related tests
└── test_*.py              # Other test modules
```

## Writing New Tests

1. **Test Naming**:
   - Test files should start with `test_`
   - Test functions should start with `test_`
   - Use descriptive names that explain what's being tested

2. **Basic Test Example**:

```python
"""Test module for example functionality."""
import pytest

def test_example():
    """Basic test example."""
    result = 1 + 1
    assert result == 2, "1 + 1 should equal 2"
```

3. **Using Fixtures**:

```python
import pytest
from dockermcp.some_module import SomeClass

@pytest.fixture
def test_client():
    """Create a test client."""
    client = SomeClass()
    yield client
    # Cleanup code here

def test_with_fixture(test_client):
    """Test using a fixture."""
    result = test_client.some_method()
    assert result is not None
```

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   - Ensure all test dependencies are installed
   - Run `pip install -r requirements-dev.txt`

2. **Test Discovery Fails**
   - Make sure test files are named `test_*.py`
   - Ensure test functions start with `test_`

3. **Output Not Captured**
   - Always use `> file.log 2>&1` to capture both stdout and stderr
   - Check file permissions in the output directory

4. **Docker-Related Issues**
   - Ensure Docker Desktop is running
   - Check that you have necessary permissions to access Docker

### Debugging Tests

To debug a failing test, you can run it with the `-s` flag to see output directly in the console:

```powershell
python -m pytest tests/test_hello_world.py -v -s
```

### Viewing Test Coverage

To generate a coverage report:

```powershell
coverage run -m pytest
coverage report -m
coverage html  # Generates HTML report in htmlcov/
```

## Continuous Integration

Tests are automatically run on pull requests and merges to the main branch. Check the CI/CD configuration in `.github/workflows/` for details.
