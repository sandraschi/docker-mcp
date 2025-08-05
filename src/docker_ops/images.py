"""
Image Manager - Docker Image Operations
Part of Sandra's Docker MCP Server - Austrian Efficiency Edition

THE MISSING FUNCTION that broke our current tool!
Handles all Docker image operations including:
- List images with size and usage information
- Pull images from registry
- Remove unused/zombie images
- Tag images for organization
- Sandra's insight: "weed out the year old zombies"
"""

import json
import subprocess
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union


class ImageManager:
    """
    Manages Docker image operations with Austrian efficiency.
    Focus on zombie detection, usage tracking, and cleanup recommendations.
    """
    
    def __init__(self):
        self.docker_cmd = ["docker"]
    
    def _run_docker_command(self, args: List[str], timeout: int = 30) -> Dict[str, Any]:
        """
        Execute Docker command with proper error handling.
        
        Args:
            args: Docker command arguments
            timeout: Command timeout in seconds
            
        Returns:
            Result dictionary with success/error information
        """
        try:
            cmd = self.docker_cmd + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
                "command": " ".join(cmd)
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "command": " ".join(cmd)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Command execution failed: {str(e)}",
                "command": " ".join(cmd)
            }
    
    def _parse_size(self, size_str: str) -> int:
        """
        Parse Docker size string to bytes.
        
        Args:
            size_str: Size string like "1.2GB", "345MB", "12.3kB"
            
        Returns:
            Size in bytes
        """
        if not size_str:
            return 0
        
        # Extract number and unit
        match = re.match(r'^([\d.]+)\s*([A-Za-z]*)', size_str.strip())
        if not match:
            return 0
        
        number = float(match.group(1))
        unit = match.group(2).upper()
        
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024**2,
            'GB': 1024**3,
            'TB': 1024**4
        }
        
        return int(number * multipliers.get(unit, 1))
    
    def _format_size(self, bytes_size: int) -> str:
        """
        Format bytes to human readable size.
        
        Args:
            bytes_size: Size in bytes
            
        Returns:
            Formatted size string
        """
        if bytes_size == 0:
            return "0B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(bytes_size)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)}{units[unit_index]}"
        else:
            return f"{size:.1f}{units[unit_index]}"
    
    def _get_container_images(self) -> Dict[str, List[str]]:
        """
        Get mapping of images to containers that use them.
        
        Returns:
            Dictionary mapping image IDs to container names
        """
        # Get all containers with their image info
        result = self._run_docker_command(["ps", "-a", "--format", "json"])
        
        image_usage = {}
        
        if result["success"] and result["stdout"]:
            for line in result["stdout"].split('\n'):
                if line.strip():
                    try:
                        container_data = json.loads(line)
                        image = container_data.get("Image", "")
                        name = container_data.get("Names", "")
                        
                        if image and name:
                            if image not in image_usage:
                                image_usage[image] = []
                            image_usage[image].append(name)
                    except json.JSONDecodeError:
                        continue
        
        return image_usage
    
    def list_images(self, include_unused: bool = True) -> Dict[str, Any]:
        """
        List all Docker images with size and usage information.
        THE MISSING FUNCTION that broke our current tool!
        
        Args:
            include_unused: Include images not used by any container
            
        Returns:
            Image list with size, age, and usage status
        """
        # Get images with detailed format
        result = self._run_docker_command([
            "images", 
            "--format", 
            "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}"
        ])
        
        if not result["success"]:
            return {
                "success": False,
                "error": result.get("error", result.get("stderr", "Unknown error")),
                "images": [],
                "summary": {"total": 0, "used": 0, "unused": 0, "total_size": 0}
            }
        
        # Get container usage information
        image_usage = self._get_container_images()
        
        images = []
        total_size = 0
        used_count = 0
        unused_count = 0
        
        lines = result["stdout"].split('\n')
        
        # Skip header line
        for line in lines[1:]:
            if not line.strip():
                continue
            
            parts = line.split('\t')
            if len(parts) >= 5:
                repository = parts[0]
                tag = parts[1]
                image_id = parts[2]
                created_at = parts[3]
                size_str = parts[4]
                
                # Parse size
                size_bytes = self._parse_size(size_str)
                total_size += size_bytes
                
                # Check if image is used
                full_image_name = f"{repository}:{tag}" if tag != "<none>" else repository
                is_used = (
                    full_image_name in image_usage or 
                    repository in image_usage or 
                    image_id[:12] in str(image_usage) or
                    any(image_id.startswith(img_id) for img_id in image_usage.keys())
                )
                
                if is_used:
                    used_count += 1
                    used_by = []
                    for img_key, containers in image_usage.items():
                        if (img_key == full_image_name or 
                            img_key == repository or 
                            image_id.startswith(img_key) or
                            img_key.startswith(image_id[:12])):
                            used_by.extend(containers)
                else:
                    unused_count += 1
                    used_by = []
                
                # Parse creation date for age calculation
                age_days = None
                try:
                    # Try to parse the creation date
                    # Docker format can vary, so we'll try multiple formats
                    created_time = None
                    for fmt in [
                        "%Y-%m-%d %H:%M:%S %z",
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S.%fZ",
                        "%Y-%m-%dT%H:%M:%SZ"
                    ]:
                        try:
                            created_time = datetime.strptime(created_at.split(' +')[0], fmt)
                            break
                        except ValueError:
                            continue
                    
                    if created_time:
                        if created_time.tzinfo is None:
                            created_time = created_time.replace(tzinfo=timezone.utc)
                        age_days = (datetime.now(timezone.utc) - created_time).days
                except:
                    age_days = None
                
                # Determine if it's a zombie (old and unused)
                is_zombie = not is_used and age_days is not None and age_days > 90
                
                image_info = {
                    "repository": repository,
                    "tag": tag,
                    "id": image_id,
                    "short_id": image_id[:12],
                    "created": created_at,
                    "age_days": age_days,
                    "size": size_str,
                    "size_bytes": size_bytes,
                    "size_formatted": self._format_size(size_bytes),
                    "is_used": is_used,
                    "used_by": used_by,
                    "is_zombie": is_zombie,
                    "full_name": full_image_name if tag != "<none>" else f"{repository}@{image_id[:12]}"
                }
                
                # Only include if we want unused images or if it's used
                if include_unused or is_used:
                    images.append(image_info)
        
        # Sort by creation date (newest first)
        images.sort(key=lambda x: x.get("age_days", 999999))
        
        return {
            "success": True,
            "images": images,
            "summary": {
                "total": len(images),
                "used": used_count,
                "unused": unused_count,
                "total_size_bytes": total_size,
                "total_size_formatted": self._format_size(total_size),
                "zombie_count": len([img for img in images if img.get("is_zombie", False)])
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_image_status(self, image_name: str) -> Dict[str, Any]:
        """
        Get detailed status of a specific image.
        Sandra's insight: "weed out the year old zombies"
        
        Args:
            image_name: Image name or ID
            
        Returns:
            Image details with age, size, usage, and cleanup recommendation
        """
        # First, get detailed inspect information
        result = self._run_docker_command(["inspect", image_name])
        
        if not result["success"]:
            return {
                "success": False,
                "error": f"Image '{image_name}' not found or inspect failed",
                "details": result.get("stderr", "")
            }
        
        try:
            inspect_data = json.loads(result["stdout"])
            if not inspect_data:
                return {
                    "success": False,
                    "error": f"No data returned for image '{image_name}'"
                }
            
            image_data = inspect_data[0]
            
            # Get basic image information
            image_id = image_data.get("Id", "")
            created = image_data.get("Created", "")
            size = image_data.get("Size", 0)
            repo_tags = image_data.get("RepoTags", [])
            repo_digests = image_data.get("RepoDigests", [])
            
            # Calculate age
            age_days = None
            try:
                created_time = datetime.fromisoformat(created.replace('Z', '+00:00'))
                age_days = (datetime.now(timezone.utc) - created_time).days
            except:
                age_days = None
            
            # Check usage
            image_usage = self._get_container_images()
            used_by = []
            
            # Check various ways the image might be referenced
            for img_key, containers in image_usage.items():
                if (image_name in img_key or 
                    img_key in image_name or
                    any(tag in img_key for tag in repo_tags) or
                    image_id.startswith(img_key) or
                    img_key.startswith(image_id[:12])):
                    used_by.extend(containers)
            
            is_used = len(used_by) > 0
            is_zombie = not is_used and age_days is not None and age_days > 90
            
            # Generate cleanup recommendation
            recommendation = "keep"
            reason = "Image is actively used"
            
            if not is_used:
                if age_days is not None and age_days > 365:
                    recommendation = "remove"
                    reason = "Zombie image - unused for over a year"
                elif age_days is not None and age_days > 90:
                    recommendation = "consider_removal"
                    reason = "Old unused image - consider removing"
                elif age_days is not None and age_days > 30:
                    recommendation = "monitor"
                    reason = "Unused for a month - monitor usage"
                else:
                    recommendation = "keep"
                    reason = "Recently created unused image"
            
            # Get layers information
            layers = image_data.get("RootFS", {}).get("Layers", [])
            
            return {
                "success": True,
                "id": image_id,
                "short_id": image_id[:12] if image_id else "",
                "repo_tags": repo_tags,
                "repo_digests": repo_digests,
                "created": created,
                "age_days": age_days,
                "size_bytes": size,
                "size_formatted": self._format_size(size),
                "is_used": is_used,
                "used_by": used_by,
                "is_zombie": is_zombie,
                "layer_count": len(layers),
                "recommendation": {
                    "action": recommendation,
                    "reason": reason,
                    "safe_to_remove": not is_used
                },
                "metadata": {
                    "architecture": image_data.get("Architecture", ""),
                    "os": image_data.get("Os", ""),
                    "docker_version": image_data.get("DockerVersion", ""),
                    "author": image_data.get("Author", ""),
                    "config": image_data.get("Config", {})
                }
            }
            
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Failed to parse image inspect data: {str(e)}"
            }
    
    def pull_image(self, image_name: str, tag: str = "latest") -> Dict[str, Any]:
        """
        Pull an image from Docker registry.
        
        Args:
            image_name: Image name (e.g., "nginx")
            tag: Image tag (default: "latest")
            
        Returns:
            Pull operation result with size and layers info
        """
        full_name = f"{image_name}:{tag}"
        
        # Use longer timeout for pulls
        result = self._run_docker_command(["pull", full_name], timeout=300)
        
        if result["success"]:
            # Get the pulled image info
            image_info_result = self.get_image_status(full_name)
            
            return {
                "success": True,
                "image": full_name,
                "message": f"Successfully pulled {full_name}",
                "image_info": image_info_result if image_info_result.get("success") else None
            }
        else:
            return {
                "success": False,
                "error": f"Failed to pull image '{full_name}'",
                "details": result.get("stderr", "Unknown error")
            }
    
    def remove_image(self, image_name: str, force: bool = False) -> Dict[str, Any]:
        """
        Remove a Docker image.
        
        Args:
            image_name: Image name or ID
            force: Force removal even if used by containers
            
        Returns:
            Remove operation result
        """
        args = ["rmi"]
        if force:
            args.append("--force")
        args.append(image_name)
        
        result = self._run_docker_command(args)
        
        if result["success"]:
            return {
                "success": True,
                "image": image_name,
                "message": f"Successfully removed image '{image_name}'"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to remove image '{image_name}'",
                "details": result.get("stderr", "Unknown error")
            }
    
    def tag_image(self, source_image: str, target_tag: str) -> Dict[str, Any]:
        """
        Tag an image with a new name/tag.
        
        Args:
            source_image: Source image name or ID
            target_tag: New tag (e.g., "myapp:v1.0")
            
        Returns:
            Tag operation result
        """
        result = self._run_docker_command(["tag", source_image, target_tag])
        
        if result["success"]:
            return {
                "success": True,
                "source": source_image,
                "target": target_tag,
                "message": f"Successfully tagged '{source_image}' as '{target_tag}'"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to tag image '{source_image}' as '{target_tag}'",
                "details": result.get("stderr", "Unknown error")
            }
    
    def find_zombie_images(self, age_threshold_days: int = 90) -> Dict[str, Any]:
        """
        Find old, unused images eating disk space.
        Sandra's insight: "weed out the year old zombies"
        
        Args:
            age_threshold_days: Age threshold for zombie detection
            
        Returns:
            Zombie image report with cleanup recommendations
        """
        # Get all images
        images_result = self.list_images(include_unused=True)
        
        if not images_result["success"]:
            return {
                "success": False,
                "error": "Failed to get image list",
                "details": images_result.get("error", "")
            }
        
        zombies = []
        total_zombie_size = 0
        
        for image in images_result["images"]:
            if (not image.get("is_used", True) and 
                image.get("age_days", 0) >= age_threshold_days):
                
                zombies.append({
                    "name": image.get("full_name", ""),
                    "id": image.get("short_id", ""),
                    "age_days": image.get("age_days", 0),
                    "size_formatted": image.get("size_formatted", ""),
                    "size_bytes": image.get("size_bytes", 0),
                    "repository": image.get("repository", ""),
                    "tag": image.get("tag", "")
                })
                total_zombie_size += image.get("size_bytes", 0)
        
        # Sort by size (largest first) for maximum cleanup impact
        zombies.sort(key=lambda x: x["size_bytes"], reverse=True)
        
        return {
            "success": True,
            "zombie_images": zombies,
            "summary": {
                "count": len(zombies),
                "total_size_bytes": total_zombie_size,
                "total_size_formatted": self._format_size(total_zombie_size),
                "age_threshold_days": age_threshold_days
            },
            "cleanup_impact": {
                "disk_space_recoverable": self._format_size(total_zombie_size),
                "safe_to_remove": True,
                "removal_commands": [f"docker rmi {zombie['id']}" for zombie in zombies[:10]]  # Top 10
            }
        }
