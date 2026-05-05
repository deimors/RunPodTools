import json
import os
import threading
from typing import Dict, List


class TagsManager:
    """Manages tags for media files using a JSON file for persistence."""

    TAGS_FILE = "tags.json"

    def __init__(self, directory: str):
        self.directory = os.path.abspath(directory)
        self.tags_path = os.path.join(self.directory, self.TAGS_FILE)
        self._tags: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        with self._lock:
            if os.path.exists(self.tags_path):
                try:
                    with open(self.tags_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self._tags = {
                        k: [t for t in v if isinstance(t, str)]
                        for k, v in data.items()
                        if isinstance(v, list)
                    }
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error loading tags from {self.tags_path}: {e}")
                    self._tags = {}
            else:
                self._tags = {}

    def get_tags(self, filename: str) -> List[str]:
        filename = filename.replace(os.sep, '/')
        with self._lock:
            return list(self._tags.get(filename, []))

    def add_tag(self, filename: str, tag: str) -> bool:
        filename = filename.replace(os.sep, '/')
        with self._lock:
            tags = list(self._tags.get(filename, []))
            if tag not in tags:
                tags.append(tag)
                self._tags[filename] = tags
            return self._save_unsafe()

    def remove_tag(self, filename: str, tag: str) -> bool:
        filename = filename.replace(os.sep, '/')
        with self._lock:
            tags = self._tags.get(filename, [])
            if tag in tags:
                self._tags[filename] = [t for t in tags if t != tag]
                if not self._tags[filename]:
                    del self._tags[filename]
                return self._save_unsafe()
            return True

    def delete_file_tags(self, filename: str) -> bool:
        filename = filename.replace(os.sep, '/')
        with self._lock:
            if filename in self._tags:
                del self._tags[filename]
                return self._save_unsafe()
            return True

    def _save_unsafe(self) -> bool:
        try:
            os.makedirs(self.directory, exist_ok=True)
            temp_path = self.tags_path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self._tags, f, indent=2, ensure_ascii=False)
            if os.path.exists(self.tags_path):
                os.replace(temp_path, self.tags_path)
            else:
                os.rename(temp_path, self.tags_path)
            return True
        except IOError as e:
            print(f"Error saving tags to {self.tags_path}: {e}")
            return False
