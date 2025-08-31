import os
import re
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).parent / 'src' / 'dockermcp'

# Files to update with their import patterns
FILES_TO_UPDATE = {
    'tools/workflow/workflow_tools.py': [
        (r'from \.\.core\.', 'from dockermcp.core.'),
        (r'from \.workflow_models', 'from dockermcp.tools.workflow.workflow_models')
    ],
    'tools/volumes/volume_tools.py': [
        (r'from \.\.core\.', 'from dockermcp.core.'),
        (r'from \.volume_models', 'from dockermcp.tools.volumes.volume_models')
    ],
    'tools/system/system_tools.py': [
        (r'from \.\.core\.', 'from dockermcp.core.'),
        (r'from \.\.utils\.', 'from dockermcp.utils.'),
        (r'from \.system_models', 'from dockermcp.tools.system.system_models')
    ],
    'tools/networks/network_tools.py': [
        (r'from \.\.core\.', 'from dockermcp.core.'),
        (r'from \.network_models', 'from dockermcp.tools.networks.network_models')
    ],
    'tools/images/image_tools.py': [
        (r'from \.\.core\.', 'from dockermcp.core.'),
        (r'from \.image_models', 'from dockermcp.tools.images.image_models')
    ],
    'tools/containers/container_tools.py': [
        (r'from \.\.core\.', 'from dockermcp.core.'),
        (r'from \.container_models', 'from dockermcp.tools.containers.container_models')
    ],
    'tools/compose/compose_tools.py': [
        (r'from \.\.core\.', 'from dockermcp.core.'),
        (r'from \.compose_models', 'from dockermcp.tools.compose.compose_models'),
        (r'from \.\.\.utils\.', 'from dockermcp.utils.')
    ],
    'tools/examples/stateful_example.py': [
        (r'from \.\.state', 'from dockermcp.state')
    ]
}

def update_file_imports(file_path, patterns):
    """Update imports in a file based on the given patterns."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modified = False
        for pattern, replacement in patterns:
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                modified = True
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {file_path}")
        else:
            print(f"No changes needed: {file_path}")
            
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")

def main():
    """Update imports in all specified files."""
    for rel_path, patterns in FILES_TO_UPDATE.items():
        file_path = BASE_DIR / rel_path
        if file_path.exists():
            update_file_imports(file_path, patterns)
        else:
            print(f"File not found: {file_path}")

if __name__ == "__main__":
    main()
