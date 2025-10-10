from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import os
from datetime import datetime
from webp import extract_webp_animation_metadata
from images import get_image_metadata

class GallerySource(ABC):
    """Abstract base class for gallery sources."""
    
    @abstractmethod
    def list_files(self, directory_type: str = "webp") -> List[str]:
        """List all files in the specified directory."""
        pass
    
    @abstractmethod
    def get_file_path(self, filename: str, directory_type: str = "webp") -> str:
        """Get the full path to a file."""
        pass
    
    @abstractmethod
    def file_exists(self, filename: str, directory_type: str = "webp") -> bool:
        """Check if a file exists."""
        pass
    
    @abstractmethod
    def get_file_metadata(self, filename: str, directory_type: str = "webp") -> Dict:
        """Get metadata for a file."""
        pass
    
    @abstractmethod
    def save_file(self, filename: str, file_data, directory_type: str = "uploads") -> bool:
        """Save a file to the source."""
        pass
    
    @abstractmethod
    def delete_file(self, filename: str, directory_type: str = "webp") -> bool:
        """Delete a file from the source."""
        pass

class FilesystemGallerySource(GallerySource):
    """Filesystem-based gallery source implementation."""
    
    ALLOWED_EXTENSIONS = {'webp', 'jpg', 'jpeg', 'png'}
    
    def __init__(self, webp_dir: str, upload_dir: str, archive_dir: str):
        self.webp_dir = os.path.abspath(webp_dir)
        self.upload_dir = os.path.abspath(upload_dir)
        self.archive_dir = os.path.abspath(archive_dir)
        
        # Validate directories
        for directory in [self.webp_dir, self.upload_dir, self.archive_dir]:
            if not os.path.isdir(directory):
                raise ValueError(f"'{directory}' is not a valid directory")
    
    def _get_directory(self, directory_type: str) -> str:
        """Get the directory path based on type."""
        if directory_type == "webp":
            return self.webp_dir
        elif directory_type == "uploads":
            return self.upload_dir
        elif directory_type == "archive":
            return self.archive_dir
        else:
            raise ValueError(f"Invalid directory type: {directory_type}")
    
    def list_files(self, directory_type: str = "webp") -> List[str]:
        """List all files in the specified directory."""
        target_dir = self._get_directory(directory_type)
        return [f for f in os.listdir(target_dir) 
                if any(f.lower().endswith(ext) for ext in self.ALLOWED_EXTENSIONS)]
    
    def get_file_path(self, filename: str, directory_type: str = "webp") -> str:
        """Get the full path to a file."""
        target_dir = self._get_directory(directory_type)
        return os.path.join(target_dir, filename)
    
    def file_exists(self, filename: str, directory_type: str = "webp") -> bool:
        """Check if a file exists."""
        file_path = self.get_file_path(filename, directory_type)
        return os.path.isfile(file_path)
    
    def get_file_metadata(self, filename: str, directory_type: str = "webp") -> Dict:
        """Get metadata for a file."""
        file_path = self.get_file_path(filename, directory_type)
        last_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
        
        if filename.lower().endswith(".webp"):
            metadata = extract_webp_animation_metadata(file_path)
            if isinstance(metadata, dict):
                return {
                    "name": filename,
                    "size_bytes": metadata["file_size"],
                    "resolution": f"{metadata['width']}x{metadata['height']}",
                    "frames": metadata["frame_count"],
                    "duration_seconds": metadata["total_duration_ms"] / 1000,
                    "frame_rate": metadata["frame_rate"],
                    "last_modified": last_modified
                }
            else:
                return {"name": filename, "error": metadata, "last_modified": last_modified}
        elif filename.lower().endswith((".png", ".jpg", ".jpeg")):
            metadata = get_image_metadata(file_path)
            if isinstance(metadata, dict):
                return {
                    "name": filename,
                    "size_bytes": metadata["file_size"],
                    "resolution": f"{metadata['width']}x{metadata['height']}",
                    "last_modified": last_modified
                }
            else:
                return {"name": filename, "error": metadata, "last_modified": last_modified}
        else:
            return {"name": filename, "last_modified": last_modified}
    
    def get_file_size(self, filename: str, directory_type: str = "webp") -> int:
        """Get the size of a file in bytes."""
        file_path = self.get_file_path(filename, directory_type)
        return os.path.getsize(file_path)
    
    def get_file_mtime(self, filename: str, directory_type: str = "webp") -> float:
        """Get the modification time of a file."""
        file_path = self.get_file_path(filename, directory_type)
        return os.path.getmtime(file_path)
    
    def save_file(self, filename: str, file_data, directory_type: str = "uploads") -> bool:
        """Save a file to the source."""
        try:
            file_path = self.get_file_path(filename, directory_type)
            file_data.save(file_path)
            return True
        except Exception as e:
            print(f"Error saving file {filename}: {e}")
            return False
    
    def delete_file(self, filename: str, directory_type: str = "webp") -> bool:
        """Delete a file from the source."""
        try:
            file_path = self.get_file_path(filename, directory_type)
            if os.path.isfile(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting file {filename}: {e}")
            return False
