"""
Test script to verify behavior when Docker Desktop GUI is not running.
"""


def test_docker_desktop_gui():
    """Test if Docker Desktop GUI is running."""
    try:
        import psutil

        # Check if Docker Desktop process is running
        for proc in psutil.process_iter(["name"]):
            if "Docker Desktop" in proc.info["name"]:
                return True, "✅ Docker Desktop GUI is running"

        return False, "❌ Docker Desktop GUI is not running (but Docker daemon might be)"

    except Exception as e:
        return False, f"❌ Error checking Docker Desktop GUI: {e!s}"


if __name__ == "__main__":
    print("Checking Docker Desktop GUI status...")
    success, message = test_docker_desktop_gui()
    print(message)

    if not success:
        print("\n✅ Test successful! The script correctly detected that Docker Desktop GUI is not running.")
        print("\nThis is the scenario we want to test - where the Docker daemon is running")
        print("but the Desktop GUI is not. Our application should handle this gracefully.")
