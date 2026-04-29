from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import os
from datetime import datetime
from webp import extract_webp_animation_metadata
from images import get_image_metadata
from mp4 import extract_mp4_metadata
from ratings import RatingsManager
from ratings import RatingsManager

class GallerySource(ABC):
    """Abstract base class for gallery sources."""
    
    @abstractmethod
    def list_files(self) -> List[str]:
        """List all files in the source."""
        pass
    
    @abstractmethod
    def get_file_path(self, filename: str) -> str:
        """Get the full path to a file."""
        pass
    
    @abstractmethod
    def file_exists(self, filename: str) -> bool:
        """Check if a file exists."""
        pass
    
    @abstractmethod
    def get_file_metadata(self, filename: str) -> Dict:
        """Get metadata for a file."""
        pass
    
    @abstractmethod
    def save_file(self, filename: str, file_data) -> bool:
        """Save a file to the source."""
        pass
    
    @abstractmethod
    def delete_file(self, filename: str) -> bool:
        """Delete a file from the source."""
        pass
    
    @abstractmethod
    def get_file_size(self, filename: str) -> int:
        """Get the size of a file in bytes."""
        pass
    
    @abstractmethod
    def get_file_mtime(self, filename: str) -> float:
        """Get the modification time of a file."""
        pass

class FilesystemGallerySource(GallerySource):
    """Filesystem-based gallery source implementation."""
    
    ALLOWED_EXTENSIONS = {'webp', 'jpg', 'jpeg', 'png', 'mp4'}
    
    def __init__(self, directory: str, allowed_extensions: Optional[set] = None):
        self.directory = os.path.abspath(directory)
        self.allowed_extensions = allowed_extensions or self.ALLOWED_EXTENSIONS
        
        # Validate directory
        if not os.path.isdir(self.directory):
            raise ValueError(f"'{self.directory}' is not a valid directory")
        
        # Initialize ratings manager (skip for archive directories)
        if allowed_extensions and 'zip' in allowed_extensions:
            self.ratings_manager = None  # Archives don't need ratings
        else:
            self.ratings_manager = RatingsManager(self.directory)
        
        # Initialize ratings manager (skip for archive directories)
        if allowed_extensions and 'zip' in allowed_extensions:
            self.ratings_manager = None  # Archives don't need ratings
        else:
            self.ratings_manager = RatingsManager(self.directory)
    
    def list_files(self) -> List[str]:
        """List all files in the source, recursively."""
        result = []
        for dirpath, _, filenames in os.walk(self.directory):
            for f in filenames:
                if any(f.lower().endswith(ext) for ext in self.allowed_extensions):
                    rel = os.path.relpath(os.path.join(dirpath, f), self.directory)
                    result.append(rel)
        return result
    
    def get_file_path(self, filename: str) -> str:
        """Get the full path to a file."""
        return os.path.join(self.directory, filename)
    
    def file_exists(self, filename: str) -> bool:
        """Check if a file exists."""
        file_path = self.get_file_path(filename)
        return os.path.isfile(file_path)
    
    def get_file_metadata(self, filename: str) -> Dict:
        """Get metadata for a file."""
        file_path = self.get_file_path(filename)
        last_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
        
        if filename.lower().endswith(".webp"):
            metadata = extract_webp_animation_metadata(file_path)
            if isinstance(metadata, dict):
                result = {
                    "name": filename,
                    "size_bytes": metadata["file_size"],
                    "resolution": f"{metadata['width']}x{metadata['height']}",
                    "frames": metadata["frame_count"],
                    "duration_seconds": metadata["total_duration_ms"] / 1000,
                    "frame_rate": metadata["frame_rate"],
                    "last_modified": last_modified
                }
                if self.ratings_manager:
                    result["rating"] = self.ratings_manager.get_rating(filename)
                return result
            else:
                result = {"name": filename, "error": metadata, "last_modified": last_modified}
                if self.ratings_manager:
                    result["rating"] = self.ratings_manager.get_rating(filename)
                return result
        elif filename.lower().endswith((".png", ".jpg", ".jpeg")):
            metadata = get_image_metadata(file_path)
            if isinstance(metadata, dict):
                result = {
                    "name": filename,
                    "size_bytes": metadata["file_size"],
                    "resolution": f"{metadata['width']}x{metadata['height']}",
                    "last_modified": last_modified
                }
                if self.ratings_manager:
                    result["rating"] = self.ratings_manager.get_rating(filename)
                return result
            else:
                result = {"name": filename, "error": metadata, "last_modified": last_modified}
                if self.ratings_manager:
                    result["rating"] = self.ratings_manager.get_rating(filename)
                return result
        elif filename.lower().endswith(".mp4"):
            metadata = extract_mp4_metadata(file_path)
            if isinstance(metadata, dict):
                result = {
                    "name": filename,
                    "size_bytes": metadata["file_size"],
                    "resolution": f"{metadata['width']}x{metadata['height']}",
                    "duration_seconds": metadata["duration_ms"] / 1000,
                    "frame_rate": metadata["frame_rate"],
                    "last_modified": last_modified
                }
                if self.ratings_manager:
                    result["rating"] = self.ratings_manager.get_rating(filename)
                return result
            else:
                result = {"name": filename, "error": metadata, "last_modified": last_modified}
                if self.ratings_manager:
                    result["rating"] = self.ratings_manager.get_rating(filename)
                return result
        else:
            result = {"name": filename, "last_modified": last_modified}
            if self.ratings_manager:
                result["rating"] = self.ratings_manager.get_rating(filename)
            return result
    
    def get_file_size(self, filename: str) -> int:
        """Get the size of a file in bytes."""
        file_path = self.get_file_path(filename)
        return os.path.getsize(file_path)
    
    def get_file_mtime(self, filename: str) -> float:
        """Get the modification time of a file."""
        file_path = self.get_file_path(filename)
        return os.path.getmtime(file_path)
    
    def save_file(self, filename: str, file_data, subdir: str = "") -> bool:
        """Save a file to the source, optionally into a subdirectory."""
        target_dir = self._resolve_subpath(subdir)
        if target_dir is None:
            return False
        try:
            os.makedirs(target_dir, exist_ok=True)
            file_path = os.path.join(target_dir, filename)
            file_data.save(file_path)
            return True
        except Exception as e:
            print(f"Error saving file {filename}: {e}")
            return False
    
    def delete_file(self, filename: str) -> bool:
        """Delete a file from the source."""
        try:
            file_path = self.get_file_path(filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                # Clean up rating when file is deleted
                if self.ratings_manager:
                    self.ratings_manager.delete_rating(filename)
                return True
            return False
        except Exception as e:
            print(f"Error deleting file {filename}: {e}")
            return False

    def create_subdir(self, parent_subpath: str, name: str) -> bool:
        """Create a new subdirectory named `name` inside parent_subpath."""
        parent = self._resolve_subpath(parent_subpath)
        if parent is None:
            return False
        try:
            new_dir = os.path.join(parent, name)
            # Verify the new path is exactly one level inside parent
            if os.path.normpath(os.path.dirname(new_dir)) != os.path.normpath(parent):
                return False
            os.makedirs(new_dir, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating directory {name}: {e}")
            return False

    def _resolve_subpath(self, subpath: str) -> Optional[str]:
        """Resolve subpath within directory, returning None if path traversal is detected."""
        if not subpath:
            return self.directory
        target = os.path.normpath(os.path.join(self.directory, subpath))
        if not (target == self.directory or target.startswith(self.directory + os.sep)):
            return None
        return target

    def list_subdirs(self, subpath: str = "") -> List[str]:
        """List immediate subdirectory names at base_dir/subpath."""
        target = self._resolve_subpath(subpath)
        if target is None or not os.path.isdir(target):
            return []
        result = []
        try:
            for entry in os.scandir(target):
                if entry.is_dir():
                    result.append(entry.name)
        except PermissionError:
            pass
        return sorted(result)

    def list_dir_tree(self, subpath: str = "") -> List[Dict]:
        """Return full recursive directory tree as nested list of {name, path, children}."""
        target = self._resolve_subpath(subpath)
        if target is None or not os.path.isdir(target):
            return []
        result = []
        try:
            for entry in sorted(os.scandir(target), key=lambda e: e.name.lower()):
                if entry.is_dir():
                    child_subpath = os.path.relpath(entry.path, self.directory).replace(os.sep, '/')
                    result.append({
                        "name": entry.name,
                        "path": child_subpath,
                        "children": self.list_dir_tree(child_subpath)
                    })
        except PermissionError:
            pass
        return result

    def list_files_in_dir(self, subpath: str = "") -> List[str]:
        """List files (non-recursively) in base_dir/subpath matching allowed extensions."""
        target = self._resolve_subpath(subpath)
        if target is None or not os.path.isdir(target):
            return []
        result = []
        try:
            for entry in os.scandir(target):
                if entry.is_file():
                    if any(entry.name.lower().endswith('.' + ext) for ext in self.allowed_extensions):
                        rel = os.path.relpath(entry.path, self.directory)
                        result.append(rel)
        except PermissionError:
            pass
        return result
