"""
Manages saving and loading notes from persistent storage.
"""
import json
from pathlib import Path
from typing import Optional
import config


class NotesManager:
    """Handles note persistence using JSON storage."""
    
    def __init__(self):
        self.notes_file = config.NOTES_FILE
        self._notes = ""
        self._load_notes()
    
    def _load_notes(self) -> None:
        """Load notes from file if it exists."""
        try:
            if self.notes_file.exists():
                with open(self.notes_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._notes = data.get('content', '')
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading notes: {e}")
            self._notes = ""
    
    def save_notes(self, content: str) -> bool:
        """Save notes to file."""
        try:
            self._notes = content
            data = {'content': content}
            with open(self.notes_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            print(f"Error saving notes: {e}")
            return False
    
    def get_notes(self) -> str:
        """Get current notes content."""
        return self._notes
    
    def clear_notes(self) -> bool:
        """Clear all notes."""
        return self.save_notes("")

