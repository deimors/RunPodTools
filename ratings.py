import json
import os
import threading
from typing import Dict, Optional

class RatingsManager:
    """Manages star ratings (0-3) for media files using a JSON file for persistence."""
    
    RATINGS_FILE = "ratings.json"
    MIN_RATING = 0  # 0 = unrated
    MAX_RATING = 3  # 1-3 stars
    
    def __init__(self, directory: str):
        """
        Initialize the RatingsManager for a specific directory.
        
        Args:
            directory: The directory where ratings.json will be stored
        """
        self.directory = os.path.abspath(directory)
        self.ratings_path = os.path.join(self.directory, self.RATINGS_FILE)
        self._ratings: Dict[str, int] = {}
        self._lock = threading.Lock()
        self.load_ratings()
    
    def load_ratings(self) -> Dict[str, int]:
        """Load ratings from the JSON file into memory."""
        with self._lock:
            if os.path.exists(self.ratings_path):
                try:
                    with open(self.ratings_path, 'r', encoding='utf-8') as f:
                        self._ratings = json.load(f)
                    # Validate loaded data
                    self._ratings = {
                        k: v for k, v in self._ratings.items()
                        if isinstance(v, int) and self.MIN_RATING <= v <= self.MAX_RATING
                    }
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error loading ratings from {self.ratings_path}: {e}")
                    self._ratings = {}
            else:
                self._ratings = {}
        return self._ratings.copy()
    
    def get_rating(self, filename: str) -> int:
        """
        Get the rating for a specific file.
        
        Args:
            filename: Relative path to the file from the directory root
            
        Returns:
            Rating value (0-3), where 0 means unrated
        """
        # Normalize path separators to forward slashes for consistency
        filename = filename.replace(os.sep, '/')
        with self._lock:
            return self._ratings.get(filename, 0)
    
    def set_rating(self, filename: str, rating: int) -> bool:
        """
        Set the rating for a specific file.
        
        Args:
            filename: Relative path to the file from the directory root
            rating: Rating value (0-3)
            
        Returns:
            True if successful, False otherwise
        """
        # Validate rating
        if not isinstance(rating, int) or not (self.MIN_RATING <= rating <= self.MAX_RATING):
            print(f"Invalid rating value: {rating}. Must be between {self.MIN_RATING} and {self.MAX_RATING}")
            return False
        
        # Normalize path separators to forward slashes for consistency
        filename = filename.replace(os.sep, '/')
        
        with self._lock:
            # Remove rating if set to 0 (unrated)
            if rating == 0:
                if filename in self._ratings:
                    del self._ratings[filename]
            else:
                self._ratings[filename] = rating
            
            # Save immediately
            return self._save_ratings_unsafe()
    
    def delete_rating(self, filename: str) -> bool:
        """
        Delete the rating for a specific file.
        
        Args:
            filename: Relative path to the file from the directory root
            
        Returns:
            True if a rating was deleted, False if no rating existed
        """
        # Normalize path separators to forward slashes for consistency
        filename = filename.replace(os.sep, '/')
        
        with self._lock:
            if filename in self._ratings:
                del self._ratings[filename]
                self._save_ratings_unsafe()
                return True
            return False
    
    def save_ratings(self) -> bool:
        """
        Save ratings to the JSON file.
        
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            return self._save_ratings_unsafe()
    
    def _save_ratings_unsafe(self) -> bool:
        """
        Internal method to save ratings without acquiring lock.
        Should only be called when lock is already held.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(self.directory, exist_ok=True)
            
            # Write to a temporary file first
            temp_path = self.ratings_path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self._ratings, f, indent=2, ensure_ascii=False)
            
            # Atomic rename (on most platforms)
            if os.path.exists(self.ratings_path):
                os.replace(temp_path, self.ratings_path)
            else:
                os.rename(temp_path, self.ratings_path)
            
            return True
        except IOError as e:
            print(f"Error saving ratings to {self.ratings_path}: {e}")
            return False
    
    def get_all_ratings(self) -> Dict[str, int]:
        """
        Get a copy of all ratings.
        
        Returns:
            Dictionary mapping filenames to ratings
        """
        with self._lock:
            return self._ratings.copy()
    
    def get_rated_count(self) -> int:
        """
        Get the count of rated files (rating > 0).
        
        Returns:
            Number of files with ratings
        """
        with self._lock:
            return len(self._ratings)
