#\!/usr/bin/env python3
import os
import sys
import json
from obsidian_librarian.commands.utilities.history_manager import HistoryManager

# Create a history manager
history = HistoryManager()

# Add a test entry
history.add_modified_file('/tmp/file1.md', '/tmp/file1.md.bak')
history.add_modified_file('/tmp/file2.md', '/tmp/file2.md.bak')

# Save the history
result = history.save_history('test command')
print(f"History saved: {result}")

# Read the history file
history_file = os.path.join(os.path.expanduser('~'), '.config', 'obsidian-librarian', 'format_history.json')
if os.path.exists(history_file):
    print(f"History file exists at: {history_file}")
    try:
        with open(history_file, 'r') as f:
            data = json.load(f)
            print(f"History entries: {len(data)}")
            for i, entry in enumerate(data):
                print(f"  Entry {i}: {entry.get('command')} - {len(entry.get('modified_files', []))} files")
    except Exception as e:
        print(f"Error reading history: {e}")
else:
    print(f"History file does not exist: {history_file}")
