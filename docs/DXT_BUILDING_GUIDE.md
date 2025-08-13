# DXT Extension Building - Complete Guide for All MCP Servers

**Version:** 1.0  
**Date:** 2025-08-13  
**Applies to:** ALL MCP server repositories  
**AI Tools:** Windsurf, Cursor, Claude Code  

## 🎯 CRITICAL RULES - READ FIRST

### ❌ NEVER DO
1. **NO `dxt init`** - Primitive 1980s CLI prompting
2. **NO manual manifest editing** - Use AI to generate comprehensive configs
3. **NO custom build scripts** - Use official `dxt pack` only
4. **NO hardcoded external paths** - Use `user_config` for all dependencies
5. **NO shell variable substitution** - Claude Desktop doesn't resolve `${VAR}` literals

### ✅ ALWAYS DO
1. **AI-generate manifest.json** - Comprehensive, professional configurations
2. **Use `user_config`** - For ALL external dependencies (executables, directories, API keys)
3. **Template literals** - `${user_config.key}` for runtime substitution
4. **Official DXT toolchain** - `dxt validate`, `dxt pack`, `dxt sign`
5. **GitHub Actions automation** - Tag-based releases with CI/CD

## 📋 DXT MANIFEST.JSON SPECIFICATION

### Required Fields
```json
{
  "dxt_version": "0.1",
  "name": "your-mcp-server",
  "version": "1.0.0",
  "description": "Brief description for extension store",
  "author": {
    "name": "Your Name",
    "email": "you@example.com"
  },
  "server": {
    "type": "python",
    "entry_point": "your_mcp/server.py",
    "mcp_config": {
      "command": "python",
      "args": ["-m", "your_mcp.server"],
      "env": {
        "EXTERNAL_TOOL": "${user_config.external_tool}",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### User Config Patterns

#### External Executable
```json
"user_config": {
  "external_tool": {
    "type": "file",
    "title": "External Tool Executable",
    "description": "Select your tool installation (tool.exe on Windows, tool on macOS/Linux)",
    "required": true,
    "default": "C:\\Program Files\\Tool\\tool.exe",
    "filter": [".exe"],
    "validation": {
      "must_exist": true,
      "executable": true
    }
  }
}
```

#### Directory Selection
```json
"workspace_directory": {
  "type": "directory", 
  "title": "Workspace Directory",
  "description": "Directory for project files and outputs",
  "required": true,
  "default": "${HOME}/Documents/Workspace"
}
```

#### API Key/Secret
```json
"api_key": {
  "type": "string",
  "title": "API Key",
  "description": "Your service API key",
  "sensitive": true,
  "required": true
}
```

#### Boolean Flag
```json
"debug_mode": {
  "type": "boolean",
  "title": "Debug Mode", 
  "description": "Enable detailed logging for troubleshooting",
  "required": false,
  "default": false
}
```

#### Multiple Selection
```json
"allowed_directories": {
  "type": "directory",
  "title": "Allowed Directories",
  "description": "Directories this extension can access",
  "multiple": true,
  "required": true,
  "default": ["${HOME}/Documents", "${HOME}/Projects"]
}
```

### Template Literals

#### Supported Variables
- `${__dirname}` - Extension installation directory
- `${user_config.key}` - User-provided configuration value
- `${HOME}` - User home directory
- `${PROGRAM_FILES}` - Windows Program Files (platform-specific)

#### Usage in mcp_config
```json
"mcp_config": {
  "command": "python",
  "args": ["-m", "your_mcp.server"],
  "env": {
    "TOOL_EXECUTABLE": "${user_config.tool_executable}",
    "WORKSPACE_DIR": "${user_config.workspace_directory}",
    "API_KEY": "${user_config.api_key}",
    "DEBUG": "${user_config.debug_mode}",
    "EXTENSION_DIR": "${__dirname}"
  }
}
```

### Complete Manifest Example
```json
{
  "dxt_version": "0.1",
  "name": "example-mcp",
  "version": "1.0.0",
  "description": "Example MCP server with external tool integration",
  "long_description": "Comprehensive MCP server that demonstrates proper external dependency handling, user configuration, and professional tool integration patterns.",
  "author": {
    "name": "Sandra Schi",
    "email": "sandra@sandraschi.dev",
    "url": "https://github.com/sandraschi"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/sandraschi/example-mcp"
  },
  "homepage": "https://github.com/sandraschi/example-mcp",
  "documentation": "https://github.com/sandraschi/example-mcp/blob/main/README.md",
  "support": "https://github.com/sandraschi/example-mcp/issues",
  "license": "MIT",
  "keywords": ["mcp", "example", "external-tools", "automation"],
  "icon": "assets/icon.png",
  "screenshots": [
    "assets/screenshots/main-interface.png",
    "assets/screenshots/configuration.png"
  ],
  "server": {
    "type": "python",
    "entry_point": "example_mcp/server.py",
    "mcp_config": {
      "command": "python", 
      "args": ["-m", "example_mcp.server"],
      "env": {
        "TOOL_EXECUTABLE": "${user_config.tool_executable}",
        "WORKSPACE_DIR": "${user_config.workspace_directory}",
        "API_KEY": "${user_config.api_key}",
        "DEBUG_MODE": "${user_config.debug_mode}",
        "PYTHONUNBUFFERED": "1"
      }
    }
  },
  "user_config": {
    "tool_executable": {
      "type": "file",
      "title": "External Tool Executable",
      "description": "Select your external tool executable",
      "required": true,
      "default": "C:\\Program Files\\Tool\\tool.exe",
      "filter": [".exe"]
    },
    "workspace_directory": {
      "type": "directory",
      "title": "Workspace Directory",
      "description": "Directory for project files and outputs",
      "required": true,
      "default": "${HOME}/Documents/ExampleMCP"
    },
    "api_key": {
      "type": "string",
      "title": "API Key",
      "description": "Your service API key (stored securely)",
      "sensitive": true,
      "required": false
    },
    "debug_mode": {
      "type": "boolean",
      "title": "Debug Mode",
      "description": "Enable detailed logging",
      "required": false,
      "default": false
    }
  },
  "tools": [
    {
      "name": "process_file",
      "description": "Process files using external tool integration"
    },
    {
      "name": "analyze_data", 
      "description": "Analyze data with AI-powered insights"
    },
    {
      "name": "generate_report",
      "description": "Generate comprehensive reports"
    }
  ],
  "prompts": [
    {
      "name": "analyze_project",
      "description": "Analyze project structure and provide insights",
      "arguments": ["project_type", "analysis_depth"],
      "text": "Analyze the ${arguments.project_type} project with ${arguments.analysis_depth} level analysis. Provide comprehensive insights and recommendations."
    }
  ],
  "tools_generated": true,
  "prompts_generated": false,
  "compatibility": {
    "platforms": ["windows", "macos", "linux"],
    "python_version": ">=3.8"
  },
  "permissions": {
    "filesystem": {
      "read": true,
      "write": true,
      "directories": ["${user_config.workspace_directory}"]
    },
    "network": {
      "allowed": true,
      "domains": ["api.example.com"]
    },
    "system": {
      "execute_external": true,
      "processes": ["${user_config.tool_executable}"]
    }
  },
  "dependencies": [
    "fastmcp>=2.10.1",
    "pydantic>=2.0.0",
    "httpx>=0.25.0",
    "loguru>=0.7.0"
  ]
}
```

## 🚀 BUILD PROCESS

### Prerequisites
```bash
# Install DXT CLI (official toolchain)
npm install -g @anthropic-ai/dxt

# Install Python dependencies
pip install -r requirements.txt
```

### Repository Structure
```
your-mcp-server/
├── .github/
│   └── workflows/
│       └── build-dxt.yml          # GitHub Actions
├── dxt/
│   ├── manifest.json              # AI-generated manifest
│   └── assets/                    # Icons, screenshots
├── src/
│   └── your_mcp/                  # Python MCP server
│       ├── __init__.py
│       ├── server.py              # Main server entry point
│       └── handlers/              # Tool handlers
├── docs/
│   └── DXT_BUILDING_GUIDE.md      # This file
├── requirements.txt               # Python dependencies
├── build_github.py               # CI/CD build script
└── README.md
```

### Local Development
```bash
# 1. AI-generate manifest.json (place in dxt/manifest.json)

# 2. Validate manifest
cd dxt
dxt validate manifest.json

# 3. Build DXT package
dxt pack . ../dist/your-mcp-server-1.0.0.dxt

# 4. Test installation
# Drag dist/*.dxt to Claude Desktop
```

## 🚀 GITHUB CI/CD AUTOMATION

### Complete GitHub Actions Workflow
Create `.github/workflows/build-dxt.yml`:

```yaml
name: Build and Release DXT Extension

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to build (e.g., 1.0.0)'
        required: true
        default: '1.0.0'

jobs:
  build-dxt:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        
    - name: Install DXT CLI
      run: npm install -g @anthropic-ai/dxt
      
    - name: Install Python dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        
    - name: Create dist directory
      run: mkdir -p dist
        
    - name: Validate manifest.json
      run: dxt validate dxt/manifest.json
      
    - name: Build DXT extension
      run: |
        cd dxt
        dxt pack . ../dist/${{ github.event.repository.name }}-${{ github.event.inputs.version || github.ref_name }}.dxt
        
    - name: Sign DXT extension (optional)
      if: ${{ secrets.DXT_SIGNING_KEY }}
      run: |
        echo "${{ secrets.DXT_SIGNING_KEY }}" > signing.key
        dxt sign dist/*.dxt --key signing.key
        rm signing.key
        
    - name: Upload DXT artifact
      uses: actions/upload-artifact@v3
      with:
        name: dxt-extension
        path: dist/*.dxt
        retention-days: 30
        
    - name: Create GitHub Release
      if: startsWith(github.ref, 'refs/tags/')
      uses: softprops/action-gh-release@v1
      with:
        files: dist/*.dxt
        generate_release_notes: true
        draft: false
        prerelease: false
        body: |
          ## DXT Extension Release
          
          Download the `.dxt` file below and drag it to Claude Desktop for one-click installation.
          
          ### Installation
          1. Download the `.dxt` file from the assets below
          2. Drag the file to Claude Desktop
          3. Follow the configuration prompts
          4. Restart Claude Desktop
          
          ### What's New
          See the auto-generated release notes below.
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### GitHub Actions Features

#### **Trigger Methods**
1. **Tag-based releases (Production):**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
   - Automatically builds and creates GitHub release
   - Attaches .dxt file for public download
   - Generates release notes from commits

2. **Manual workflow dispatch (Testing):**
   - Go to GitHub Actions → "Build and Release DXT Extension"
   - Click "Run workflow"
   - Specify version number
   - Downloads .dxt file as artifact for testing

#### **Build Process**
1. **Environment Setup:**
   - Ubuntu latest runner
   - Python 3.11 + Node.js 18
   - Official DXT CLI installation

2. **Validation:**
   - `dxt validate dxt/manifest.json`
   - Ensures manifest syntax and completeness
   - Validates template literals and user_config

3. **Building:**
   - `dxt pack . ../dist/extension-name-version.dxt`
   - Uses official DXT toolchain
   - Creates distributable .dxt package

4. **Optional Signing:**
   - Signs with DXT_SIGNING_KEY secret if provided
   - Uses self-signed certificate for testing
   - Production should use proper certificates

5. **Distribution:**
   - Uploads as GitHub Actions artifact (testing)
   - Creates GitHub release with .dxt attachment (production)
   - Auto-generates installation instructions

### Build Script for Local Development
Create `build_github.py`:

```python
#!/usr/bin/env python3
"""Build script for GitHub Actions and local development"""

import os
import subprocess
import sys
import shutil
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run command and return success status"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Command failed: {cmd}")
            print(f"Error: {result.stderr}")
            return False
        print(f"✅ {cmd}")
        return True
    except Exception as e:
        print(f"❌ Exception running {cmd}: {e}")
        return False

def build_dxt():
    """Build DXT extension using official toolchain"""
    repo_root = Path(__file__).parent
    dxt_dir = repo_root / "dxt"
    dist_dir = repo_root / "dist"
    
    # Create dist directory
    dist_dir.mkdir(exist_ok=True)
    
    # Validate manifest
    print("🔍 Validating manifest.json...")
    if not run_command("dxt validate manifest.json", cwd=dxt_dir):
        return False
    
    # Get version from manifest or environment
    version = os.environ.get('VERSION', '1.0.0')
    repo_name = repo_root.name
    output_file = dist_dir / f"{repo_name}-{version}.dxt"
    
    # Build DXT package
    print(f"📦 Building DXT package: {output_file}")
    if not run_command(f"dxt pack . {output_file}", cwd=dxt_dir):
        return False
    
    # Optional signing
    signing_key = os.environ.get('DXT_SIGNING_KEY')
    if signing_key:
        print("🔐 Signing DXT package...")
        key_file = repo_root / "temp_signing.key"
        try:
            with open(key_file, 'w') as f:
                f.write(signing_key)
            if not run_command(f"dxt sign {output_file} --key {key_file}"):
                print("⚠️ Signing failed, continuing with unsigned package")
        finally:
            if key_file.exists():
                key_file.unlink()
    
    print(f"🎉 DXT package built successfully: {output_file}")
    return True

if __name__ == "__main__":
    if build_dxt():
        print("✅ Build completed successfully")
        sys.exit(0)
    else:
        print("❌ Build failed")
        sys.exit(1)
```

### Complete Release Workflow

#### **Development Cycle**
```bash
# 1. AI-generate updated manifest.json
# Place AI output in dxt/manifest.json

# 2. Test locally
python build_github.py

# 3. Test installation
# Drag dist/*.dxt to Claude Desktop
# Verify user config prompts work
# Test extension functionality

# 4. Commit changes
git add dxt/manifest.json
git commit -m "feat: updated manifest with new tools"
git push
```

#### **Release Cycle**
```bash
# 1. Update version in manifest.json
# Edit dxt/manifest.json version field: "1.1.0"

# 2. Commit version bump
git add dxt/manifest.json
git commit -m "chore: bump version to 1.1.0"
git push

# 3. Create and push release tag
git tag v1.1.0
git push origin v1.1.0

# 4. GitHub Actions automatically:
#    - Validates manifest
#    - Builds DXT package
#    - Creates GitHub release
#    - Attaches .dxt file for download
#    - Generates installation instructions
```

#### **Manual Testing Release**
```bash
# For testing without creating public release
# Go to GitHub Actions → "Build and Release DXT Extension"
# Click "Run workflow"
# Enter version: "1.1.0-test"
# Download artifact from workflow run
```

### GitHub Repository Setup

#### **Required Files Structure**
```
your-mcp-server/
├── .github/
│   └── workflows/
│       └── build-dxt.yml          # GitHub Actions workflow
├── dxt/
│   ├── manifest.json              # AI-generated DXT manifest
│   ├── assets/
│   │   ├── icon.png               # Extension icon
│   │   └── screenshots/           # Extension screenshots
│   └── README.md                  # Extension-specific docs
├── src/
│   └── your_mcp/                  # Python MCP server code
│       ├── __init__.py
│       ├── server.py              # Main server entry point
│       ├── handlers/              # Tool handlers
│       └── utils/                 # Utility modules
├── docs/
│   ├── DXT_BUILDING_GUIDE.md      # This guide (copy to all repos)
│   └── README.md                  # Project documentation
├── requirements.txt               # Python dependencies
├── build_github.py               # Local build script
├── .gitignore                    # Git ignore rules
└── README.md                     # Main project README
```

#### **GitHub Secrets (Optional)**
- `DXT_SIGNING_KEY`: Private key for signing extensions
- `DXT_CERTIFICATE`: Certificate for production signing
- `GITHUB_TOKEN`: Automatically provided by GitHub

#### **Branch Protection (Recommended)**
```yaml
# .github/branch-protection.yml
rules:
  - pattern: "main"
    required_reviews: 1
    dismiss_stale_reviews: true
    require_code_owner_reviews: true
    required_status_checks:
      - "build-dxt"
```

### Distribution and Updates

#### **GitHub Releases Distribution**
- **Primary distribution method** for DXT extensions
- **Direct .dxt downloads** from release assets
- **Auto-generated release notes** from commit messages
- **Version-tagged releases** with semantic versioning

#### **User Installation Process**
1. **Download:** User downloads .dxt file from GitHub release
2. **Install:** User drags .dxt file to Claude Desktop
3. **Configure:** Claude Desktop prompts for user_config values
4. **Activate:** Extension becomes available after configuration

#### **Automatic Updates (Future)**
- Extensions can check GitHub releases for updates
- Semantic versioning enables update notifications
- Users can enable auto-update for trusted extensions

#### **Analytics and Metrics**
- **Download counts** via GitHub release statistics
- **Issue tracking** via GitHub Issues
- **User feedback** via GitHub Discussions
- **Version adoption** via release download patterns

## 🔧 VALIDATION RULES

### Manifest Validation
```bash
# Always validate before building
dxt validate dxt/manifest.json

# Common issues:
# - Missing required fields
# - Invalid template literal syntax
# - Incorrect user_config types
# - Missing dependencies
```

### User Config Validation
- **File type:** Must include file extension filters
- **Directory type:** Should provide sensible defaults
- **String type:** Use `sensitive: true` for secrets
- **Boolean type:** Always provide default values
- **Required fields:** Must have defaults or clear descriptions

### Template Literal Rules
- **Variables:** Only use supported template variables
- **Escaping:** Properly escape backslashes in JSON strings
- **Platform-specific:** Use platform overrides when needed
- **Validation:** Test on different operating systems

## 🎯 COMMON PATTERNS BY MCP TYPE

### Tool Integration MCP (Blender, Docker, Git)
```json
"user_config": {
  "tool_executable": {
    "type": "file",
    "title": "Tool Executable",
    "description": "Select your tool installation",
    "required": true,
    "default": "C:\\Program Files\\Tool\\tool.exe"
  }
}
```

### API Service MCP (OpenAI, Anthropic, etc.)
```json
"user_config": {
  "api_key": {
    "type": "string", 
    "title": "API Key",
    "description": "Your service API key",
    "sensitive": true,
    "required": true
  },
  "api_endpoint": {
    "type": "string",
    "title": "API Endpoint",
    "description": "Service API endpoint URL",
    "required": false,
    "default": "https://api.service.com/v1"
  }
}
```

### File Processing MCP (Document, Media, etc.)
```json
"user_config": {
  "input_directory": {
    "type": "directory",
    "title": "Input Directory",
    "description": "Directory containing files to process",
    "required": true,
    "default": "${HOME}/Documents/Input"
  },
  "output_directory": {
    "type": "directory", 
    "title": "Output Directory",
    "description": "Directory for processed files",
    "required": true,
    "default": "${HOME}/Documents/Output"
  }
}
```

### Database MCP (PostgreSQL, MongoDB, etc.)
```json
"user_config": {
  "connection_string": {
    "type": "string",
    "title": "Database Connection",
    "description": "Database connection string",
    "sensitive": true,
    "required": true
  },
  "default_database": {
    "type": "string",
    "title": "Default Database",
    "description": "Default database name",
    "required": false,
    "default": "main"
  }
}
```

## 🚨 TROUBLESHOOTING

### Build Failures
```bash
# Manifest validation failed
dxt validate dxt/manifest.json
# Fix JSON syntax, required fields, template literals

# Missing dependencies
pip install -r requirements.txt
# Ensure all Python packages installed

# DXT CLI not found
npm install -g @anthropic-ai/dxt
# Install official DXT toolchain
```

### Installation Issues
```bash
# Extension won't install
# Check manifest.json syntax
# Verify all required fields present
# Test with minimal manifest first

# User config not working
# Verify template literal syntax: ${user_config.key}
# Check field types (file, directory, string, boolean)
# Test on different operating systems
```

### Runtime Problems
```bash
# External tool not found
# Check user_config setup
# Verify template literal resolution
# Add runtime detection fallback in Python code

# Permissions denied
# Update permissions section in manifest
# Check filesystem/network/system permissions
# Verify user has necessary access
```

## 📝 CHECKLIST FOR NEW MCP SERVERS

### Pre-Development
- [ ] Identify ALL external dependencies (tools, APIs, directories)
- [ ] Plan user_config structure for each dependency
- [ ] Choose appropriate types (file, directory, string, boolean)
- [ ] Design sensible defaults for common platforms

### Development
- [ ] Create comprehensive manifest.json with AI
- [ ] Implement runtime detection fallbacks in Python
- [ ] Add proper error handling for missing dependencies
- [ ] Test user_config flow in Claude Desktop

### Building
- [ ] Validate manifest: `dxt validate dxt/manifest.json`
- [ ] Build package: `dxt pack . ../dist/package.dxt`
- [ ] Test installation on clean Claude Desktop
- [ ] Verify user configuration prompts work correctly

### Release
- [ ] Setup GitHub Actions workflow
- [ ] Create release tag: `git tag v1.0.0`
- [ ] Verify automatic build and release
- [ ] Test downloaded .dxt package installation

### Post-Release
- [ ] Monitor installation success rates
- [ ] Track user configuration completion
- [ ] Address issues and feature requests
- [ ] Plan updates and improvements

## 🎪 EXAMPLES

### Blender MCP
- External tool: Blender executable
- User config: File picker for blender.exe
- Runtime detection: Common installation paths
- Tools: 3D modeling, rendering, animation

### Docker MCP
- External tool: Docker executable  
- User config: Docker installation path
- Runtime detection: Docker Desktop vs CLI
- Tools: Container management, image building

### Git MCP
- External tool: Git executable
- User config: Git path + repositories directory
- Runtime detection: System PATH detection
- Tools: Repository operations, commit management

### Database MCP
- External service: Database connection
- User config: Connection string + credentials
- Runtime detection: Connection validation
- Tools: Query execution, schema management

This guide provides everything needed to build professional DXT extensions that work reliably across all platforms and installations. Follow these patterns for consistent, high-quality MCP server packaging.
