import sqlite3
import os
import hashlib
import time
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# Import config functions
from .config import get_config_dir, get_vault_path_from_config

# Define the database path within the config directory
DB_PATH = get_config_dir() / "vault_state.db"

def get_db_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Establishes a connection to the SQLite database."""
    # Ensure the directory exists before connecting
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
    return conn

def initialize_database(db_path: Path = DB_PATH):
    """Creates the necessary table if it doesn't exist."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vault_files (
            filepath TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            first_seen REAL NOT NULL,
            last_modified REAL NOT NULL,
            last_scanned REAL NOT NULL,
            content_hash TEXT NOT NULL,
            access_timestamps TEXT NOT NULL -- Store as JSON list
        );
    """)
    # Add index for faster lookups by filename if needed later
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_filename ON vault_files (filename);")
    conn.commit()
    conn.close()
    # Don't print here, let the command handle output
    # print(f"Database initialized at: {db_path}")

def _calculate_hash(filepath: Path) -> str:
    """Calculates the SHA-256 hash of a file's content."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as file:
            while chunk := file.read(8192): # Read in chunks
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        return "" # Or handle more gracefully
    except Exception as e:
        print(f"Error hashing file {filepath}: {e}")
        return ""

def update_vault_scan(vault_path: Optional[Path] = None, db_path: Path = DB_PATH):
    """Scans the vault, updates the database with new/modified files.
       Reads vault_path from config if not provided.
    """
    if vault_path is None:
        vault_path = get_vault_path_from_config()
        if not vault_path:
            # Raise an error or return early if vault path isn't configured
            raise ValueError("Vault path is not configured. Run 'olib config setup' first.")

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    current_time = time.time()
    found_files = set()

    print(f"Scanning vault: {vault_path}...")
    for root, _, files in os.walk(vault_path):
        for filename in files:
            if filename.lower().endswith(".md"):
                filepath = Path(root) / filename
                # Ensure relative_path_str calculation is robust
                try:
                    relative_path_str = str(filepath.relative_to(vault_path))
                except ValueError:
                    print(f"Warning: File {filepath} seems outside the vault path {vault_path}. Skipping.")
                    continue # Skip files outside the vault root

                found_files.add(relative_path_str)

                try:
                    mtime = os.path.getmtime(filepath)
                except FileNotFoundError:
                    continue # File might have been deleted during scan

                cursor.execute("SELECT last_modified, content_hash FROM vault_files WHERE filepath = ?", (relative_path_str,))
                row = cursor.fetchone()

                needs_update = False
                current_hash = "" # Initialize current_hash

                if row:
                    # File exists in DB, check if modified
                    if mtime > row['last_modified']:
                        # Check hash only if mtime changed, optimization
                        current_hash = _calculate_hash(filepath)
                        if current_hash and current_hash != row['content_hash']:
                            needs_update = True
                            print(f"Updating modified file: {relative_path_str}")
                        elif not current_hash: # Handle hash calculation error
                             print(f"Warning: Could not calculate hash for modified file {relative_path_str}. Skipping update.")
                        else: # Hash is the same, just update timestamps
                             cursor.execute("UPDATE vault_files SET last_modified = ?, last_scanned = ? WHERE filepath = ?",
                                           (mtime, current_time, relative_path_str))
                             current_hash = row['content_hash'] # Keep old hash
                    else:
                        # Even if mtime is same, update last_scanned time
                        cursor.execute("UPDATE vault_files SET last_scanned = ? WHERE filepath = ?",
                                       (current_time, relative_path_str))
                        # No hash calculation needed if mtime hasn't changed
                        current_hash = row['content_hash'] # Use existing hash
                else:
                    # New file
                    current_hash = _calculate_hash(filepath)
                    if current_hash:
                        needs_update = True
                        print(f"Adding new file: {relative_path_str}")
                    else: # Handle hash calculation error
                        print(f"Warning: Could not calculate hash for new file {relative_path_str}. Skipping add.")


                if needs_update and current_hash:
                    # access_timestamps should be handled separately by record_access
                    # Only set initial timestamps when inserting a new record
                    if row: # Update existing record (only modified, scanned, hash)
                        cursor.execute("""
                            UPDATE vault_files
                            SET last_modified = ?, last_scanned = ?, content_hash = ?
                            WHERE filepath = ?
                        """, (mtime, current_time, current_hash, relative_path_str))
                    else: # Insert new record
                        # Initialize access_timestamps for new files
                        initial_access = json.dumps([]) # Start with empty list
                        cursor.execute("""
                            INSERT INTO vault_files (filepath, filename, first_seen, last_modified, last_scanned, content_hash, access_timestamps)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (relative_path_str, filename, current_time, mtime, current_time, current_hash, initial_access))

    # Remove files from DB that are no longer in the vault
    cursor.execute("SELECT filepath FROM vault_files")
    db_files = {row['filepath'] for row in cursor.fetchall()}
    deleted_files = db_files - found_files
    if deleted_files:
        print(f"Removing {len(deleted_files)} deleted files from index...")
        cursor.executemany("DELETE FROM vault_files WHERE filepath = ?", [(f,) for f in deleted_files])


    conn.commit()
    conn.close()
    print("Vault scan complete.")


def record_access(relative_filepath: str, db_path: Path = DB_PATH):
    """Records an access timestamp for a given file."""
    # Check if relative_filepath is valid (e.g., not starting with / or ..)
    if not relative_filepath or relative_filepath.startswith('/') or '..' in relative_filepath:
         print(f"Warning: Invalid relative path provided to record_access: {relative_filepath}")
         return

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    current_time = time.time()

    cursor.execute("SELECT access_timestamps FROM vault_files WHERE filepath = ?", (relative_filepath,))
    row = cursor.fetchone()

    if row:
        try:
            timestamps = json.loads(row['access_timestamps'])
            if not isinstance(timestamps, list): # Ensure it's a list
                 raise TypeError("Stored timestamps are not a list.")
            timestamps.append(current_time)
            # Optional: Limit the number of stored timestamps if needed
            # max_timestamps = 100
            # timestamps = timestamps[-max_timestamps:]
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Warning: Resetting access timestamps for {relative_filepath} due to error: {e}")
            timestamps = [current_time] # Reset if data is corrupt or not a list

        cursor.execute("UPDATE vault_files SET access_timestamps = ? WHERE filepath = ?",
                       (json.dumps(timestamps), relative_filepath))
        conn.commit()
    else:
        # File not in DB, maybe log this? It should be added by update_vault_scan first.
        print(f"Warning: Attempted to record access for non-indexed file: {relative_filepath}")


    conn.close()


def get_recent_files(hours: int, vault_path: Optional[Path] = None, db_path: Path = DB_PATH) -> List[Tuple[Path, float]]:
    """Gets files modified within the last N hours.
       Reads vault_path from config if not provided.
       Returns list of absolute Paths.
    """
    if vault_path is None:
        vault_path = get_vault_path_from_config()
        if not vault_path:
            raise ValueError("Vault path is not configured. Run 'olib config setup' first.")

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cutoff_time = time.time() - (hours * 3600)

    cursor.execute("""
        SELECT filepath, last_modified
        FROM vault_files
        WHERE last_modified >= ?
        ORDER BY last_modified DESC
    """, (cutoff_time,))

    # Return absolute Paths
    recent_files = [(vault_path / row['filepath'], row['last_modified']) for row in cursor.fetchall()]
    conn.close()
    return recent_files

# --- Add other query functions as needed ---
# Example: Get file details
def get_file_details(relative_filepath: str, db_path: Path = DB_PATH) -> Optional[sqlite3.Row]:
     """Gets all details for a file from the database."""
     # Basic validation
     if not relative_filepath or relative_filepath.startswith('/') or '..' in relative_filepath:
         print(f"Warning: Invalid relative path provided to get_file_details: {relative_filepath}")
         return None

     conn = get_db_connection(db_path)
     cursor = conn.cursor()
     cursor.execute("SELECT * FROM vault_files WHERE filepath = ?", (relative_filepath,))
     row = cursor.fetchone()
     conn.close()
     return row 
