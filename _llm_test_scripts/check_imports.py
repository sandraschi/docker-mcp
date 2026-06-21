#!/usr/bin/env python3

"""
Quick verification script to check all imports that container_management.py expects.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def check_import(module_path, import_name):
    """Check if a specific import exists in a module."""
    try:
        module = __import__(module_path, fromlist=[import_name])
        if hasattr(module, import_name):
            print(f"✅ {module_path}.{import_name} - EXISTS")
            return True
        else:
            print(f"❌ {module_path}.{import_name} - MISSING")
            return False
    except ImportError as e:
        print(f"❌ {module_path}.{import_name} - IMPORT ERROR: {e}")
        return False


def main():
    """Check all the imports that container_management.py expects."""
    print("🔍 Checking dockermcp container management imports...")
    print()

    # Expected imports from container_management.py
    expected_imports = [
        ("dockermcp.tools.containers.list_containers", "list_containers"),
        ("dockermcp.tools.containers.container_lifecycle", "manage_container_lifecycle"),
        ("dockermcp.tools.containers.container_inspect", "inspect_container"),
        ("dockermcp.tools.containers.container_logs", "get_container_logs"),
        ("dockermcp.tools.containers.container_exec", "execute_in_container"),
        ("dockermcp.tools.containers.container_stats", "get_container_stats"),
        ("dockermcp.tools.containers.container_files", "list_container_directory"),
        ("dockermcp.tools.containers.container_files", "read_container_file"),
        ("dockermcp.tools.containers.container_files", "write_container_file"),
        ("dockermcp.tools.containers.container_network", "list_networks"),
        ("dockermcp.tools.containers.container_resources", "get_container_resources"),
        ("dockermcp.tools.containers.container_resources", "reset_container_resources"),
        ("dockermcp.tools.containers.container_volumes", "list_volumes"),
        ("dockermcp.tools.containers.container_volumes", "create_volume"),
        ("dockermcp.tools.containers.container_volumes", "inspect_volume"),
        ("dockermcp.tools.containers.container_images", "list_images"),
        ("dockermcp.tools.containers.container_images", "pull_image"),
        ("dockermcp.tools.containers.container_images", "build_image"),
    ]

    # Expected parameter classes
    expected_params = [
        ("dockermcp.tools.containers.container_lifecycle", "ContainerLifecycleParams"),
        ("dockermcp.tools.containers.container_inspect", "ContainerInspectParams"),
        ("dockermcp.tools.containers.container_logs", "ContainerLogsParams"),
        ("dockermcp.tools.containers.container_exec", "ExecuteInContainerParams"),
        ("dockermcp.tools.containers.container_stats", "ContainerStatsParams"),
        ("dockermcp.tools.containers.container_files", "ListDirectoryParams"),
        ("dockermcp.tools.containers.container_files", "ReadFileParams"),
        ("dockermcp.tools.containers.container_files", "WriteFileParams"),
        ("dockermcp.tools.containers.container_network", "ListNetworksParams"),
        ("dockermcp.tools.containers.container_resources", "GetContainerResourcesParams"),
        ("dockermcp.tools.containers.container_resources", "ResetContainerResourcesParams"),
        ("dockermcp.tools.containers.container_volumes", "ListVolumesParams"),
        ("dockermcp.tools.containers.container_volumes", "CreateVolumeParams"),
        ("dockermcp.tools.containers.container_volumes", "InspectVolumeParams"),
        ("dockermcp.tools.containers.container_images", "ListImagesParams"),
        ("dockermcp.tools.containers.container_images", "PullImageParams"),
        ("dockermcp.tools.containers.container_images", "BuildImageParams"),
    ]

    print("📋 Checking function imports...")
    missing_functions = 0
    for module_path, function_name in expected_imports:
        if not check_import(module_path, function_name):
            missing_functions += 1

    print()
    print("📋 Checking parameter class imports...")
    missing_params = 0
    for module_path, param_name in expected_params:
        if not check_import(module_path, param_name):
            missing_params += 1

    print()
    print("📊 Summary:")
    print(f"   Functions missing: {missing_functions}")
    print(f"   Parameters missing: {missing_params}")

    if missing_functions == 0 and missing_params == 0:
        print("🎉 All imports are available!")
        return True
    else:
        print("❌ Some imports are missing and need to be fixed.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
