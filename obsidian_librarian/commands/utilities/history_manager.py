import os
import json
from datetime import datetime

class HistoryManager:
    """Manage command history and backups for undo functionality"""
    
    def __init__(self):
        """Initialize the history manager"""
        self.history_file = os.path.join(
            os.path.expanduser('~'), 
            '.config', 
            'obsidian-librarian', 
            'format_history.json'
        )
        
        # Create history directory if it doesn't exist
        history_dir = os.path.dirname(self.history_file)
        os.makedirs(history_dir, exist_ok=True)
        
        # Storage for modified files in current operation
        self.modified_files = []
    
    def add_modified_file(self, file_path, backup_path=None):
        """Record a modified file"""
        self.modified_files.append({
            'path': file_path,
            'backup': backup_path,
            'timestamp': datetime.now().isoformat()
        })
    
    def save_history(self, command_name='format fix'):
        """Save the current operation to history"""
        if not self.modified_files:
            return
        
        # Read existing history
        history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            except Exception as e:
                print(f"Warning: Could not read history file: {e}")
        
        # Add new entry
        history.append({
            'command': command_name,
            'timestamp': datetime.now().isoformat(),
            'modified_files': self.modified_files
        })
        
        # Save updated history
        try:
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
            return True
        except Exception as e:
            print(f"Warning: Could not save history file: {e}")
            return False
