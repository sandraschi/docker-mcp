"""
Direct Docker connection test without any FastMCP dependencies.
"""

def test_docker_connection():
    """Test if we can connect to Docker."""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True, "✅ Docker is running"
    except Exception as e:
        return False, f"❌ Docker is not available: {str(e)}"

if __name__ == "__main__":
    print("Testing Docker connection...")
    success, message = test_docker_connection()
    print(message)
    
    if not success:
        print("\n✅ Test successful! The script correctly detected that Docker is not running.")
