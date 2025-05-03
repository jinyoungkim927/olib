import sqlite3
import os
import hashlib
import time
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import sys
from datetime import datetime

# Import config functions
from .config import get_config_dir, get_vault_path_from_config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(name)s:%(filename)s:%(lineno)d %(message)s')
logger = logging.getLogger(__name__)

# Default path for the database relative to the config directory
# (Assuming config directory is determined elsewhere, e.g., in config.py)
# Let's get the config dir path dynamically if possible, or define a default
try:
    # Attempt to get path from config module if it's safe to import here
    from .config import CONFIG_DIR
    DB_PATH = CONFIG_DIR / "vault_state.db"
except ImportError:
    # Fallback if config can't be imported easily (e.g., circular dependency risk)
    # This might need adjustment based on your project structure
    DB_PATH = Path(os.path.expanduser("~/.config/obsidian-librarian/vault_state.db"))

def get_db_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Establishes a connection to the SQLite database."""
    # Ensure the directory exists before connecting
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
    return conn

def initialize_database(db_path=DB_PATH):
    """Initializes the SQLite database and creates the necessary tables if they don't exist."""
    try:
        # Ensure the directory for the database exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        # print(f"DEBUG: Initializing database at {db_path}") # Optional debug
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # --- FIX: Ensure table creation is robust and committed ---
        # Use IF NOT EXISTS to avoid errors if table already exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                mtime REAL NOT NULL,
                size INTEGER NOT NULL,
                status TEXT DEFAULT 'current' -- e.g., 'current', 'deleted'
            )
        ''')
        # Add other tables if needed (e.g., embeddings, links)

        conn.commit() # Commit the table creation immediately
        # print("DEBUG: 'files' table created or already exists.") # Optional debug
        # --- End Fix ---

        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Database error during initialization at {db_path}: {e}")
        # Decide how to handle this - raise, exit, etc.
        raise # Re-raise the error for tests to catch

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

def update_vault_scan(vault_path: Path, db_path: Path = DB_PATH, quiet: bool = False, full_scan: bool = True) -> Tuple[bool, int, int]:
    """
    Scans the vault, updates the database.

    Args:
        vault_path: Path to the Obsidian vault.
        db_path: Path to the SQLite database file.
        quiet: If True, suppress console output.
        full_scan: If True, performs a full scan detecting additions, modifications,
                   and deletions. If False, performs an incremental scan checking only
                   for files modified since the last known max modification time in the DB,
                   plus an efficient deletion check.

    Returns:
        Tuple[bool, int, int]: (success, added_count, modified_count)
                               Counts reflect changes detected *during this specific scan*.
                               Deletion counts are logged but not returned directly here.
    """
    conn = None
    changes_made = False
    # Reset counts for this specific scan run
    added_count, modified_count, deleted_count = 0, 0, 0
    processed_during_scan = {}
    scan_start_time = time.time()

    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT path, mtime, size FROM files WHERE status = 'current'")
        db_files = {row['path']: {'mtime': row['mtime'], 'size': row['size']} for row in cursor.fetchall()}
        db_paths_before_scan = set(db_files.keys())

        scan_since_mtime = 0.0
        if not full_scan:
            max_mtime_result = cursor.execute("SELECT MAX(mtime) FROM files WHERE status = 'current'").fetchone()
            if max_mtime_result and max_mtime_result[0] is not None:
                scan_since_mtime = max_mtime_result[0]
            # Output message only if not quiet
            if not quiet:
                 last_scan_dt = datetime.fromtimestamp(scan_since_mtime).strftime('%Y-%m-%d %H:%M:%S') if scan_since_mtime > 0 else "beginning"
                 print(f"Performing incremental scan for files modified since {last_scan_dt}...")
        elif not quiet:
            print(f"Performing full scan of vault: {vault_path}...")

        if not vault_path.is_dir():
             if not quiet: print(f"Error: Vault path '{vault_path}' not found during scan.")
             # Return failure and zero counts
             return False, 0, 0

        # --- Scan filesystem ---
        for item in vault_path.rglob('*'):
            if item.is_file() and item.suffix.lower() == '.md':
                try:
                    stats = item.stat()
                    if not full_scan and stats.st_mtime <= scan_since_mtime:
                        continue
                    rel_path = item.relative_to(vault_path)
                    rel_path_str = str(rel_path)
                    processed_during_scan[rel_path_str] = {'mtime': stats.st_mtime, 'size': stats.st_size}
                except Exception as e:
                     if not quiet: print(f"Warning: Could not process file {item}: {e}")


        # --- Process scanned files (Additions/Modifications) ---
        for rel_path_str, file_info in processed_during_scan.items():
            db_entry = db_files.get(rel_path_str)
            if db_entry is None:
                # New file - Increment added_count
                if not quiet: logger.debug(f"Adding new file: {rel_path_str}")
                cursor.execute(
                    "INSERT OR REPLACE INTO files (path, mtime, size, status) VALUES (?, ?, ?, ?)",
                    (rel_path_str, file_info['mtime'], file_info['size'], 'current')
                )
                added_count += 1 # <-- Count added file
                changes_made = True
            elif file_info['mtime'] > db_entry['mtime'] or file_info['size'] != db_entry['size']:
                # Modified file - Increment modified_count
                if not quiet: logger.debug(f"Updating modified file: {rel_path_str}")
                cursor.execute(
                    "UPDATE files SET mtime = ?, size = ? WHERE path = ?",
                    (file_info['mtime'], file_info['size'], rel_path_str)
                )
                modified_count += 1 # <-- Count modified file
                changes_made = True

        # --- Deletion Check ---
        if full_scan:
            files_found_in_full_scan = set(processed_during_scan.keys())
            deleted_paths = db_paths_before_scan - files_found_in_full_scan
            for rel_path_str in deleted_paths:
                if not quiet: logger.debug(f"[Full Scan] Marking deleted file: {rel_path_str}")
                cursor.execute("UPDATE files SET status = 'deleted' WHERE path = ?", (rel_path_str,))
                deleted_count += 1
                changes_made = True
        else:
            # Incremental scan deletion check
            paths_to_check_existence = db_paths_before_scan - set(processed_during_scan.keys())
            existence_check_start_time = time.time() # Perf timing
            for rel_path_str in paths_to_check_existence:
                abs_path = vault_path / rel_path_str
                if not abs_path.exists():
                    if not quiet: logger.debug(f"[Incremental Scan] Marking deleted file: {rel_path_str}")
                    cursor.execute("UPDATE files SET status = 'deleted' WHERE path = ?", (rel_path_str,))
                    deleted_count += 1
                    changes_made = True
            existence_check_duration = time.time() - existence_check_start_time
            logger.debug(f"Incremental deletion check duration: {existence_check_duration:.4f} seconds for {len(paths_to_check_existence)} files")


        # --- Commit and report ---
        if changes_made:
            conn.commit()
            # Report includes deleted_count, but it's not returned directly
            if not quiet:
                 summary = []
                 if added_count: summary.append(f"{added_count} added")
                 if modified_count: summary.append(f"{modified_count} modified")
                 if deleted_count: summary.append(f"{deleted_count} deleted")
                 scan_type = "Full scan" if full_scan else "Incremental scan"
                 print(f"{scan_type} complete. Changes: {', '.join(summary) if summary else 'None'}.")
        elif not quiet:
            scan_type = "Full scan" if full_scan else "Incremental scan"
            print(f"{scan_type} complete. No changes detected.")

        scan_duration = time.time() - scan_start_time
        logger.debug(f"Vault scan duration ({'full' if full_scan else 'incremental'}): {scan_duration:.2f} seconds. Added: {added_count}, Modified: {modified_count}, Deleted: {deleted_count}")

        # Return success and the counts of added/modified files
        return True, added_count, modified_count

    except sqlite3.Error as e:
        logger.error(f"Database error during scan: {e}")
        print(f"Database error during scan: {e}", file=sys.stderr)
        # Return failure and zero counts
        return False, 0, 0
    finally:
        if conn:
            conn.close()

def record_access(relative_filepath: str, db_path: Path = DB_PATH):
    """Records an access timestamp for a given file."""
    # Check if relative_filepath is valid (e.g., not starting with / or ..)
    if not relative_filepath or relative_filepath.startswith('/') or '..' in relative_filepath:
         print(f"Warning: Invalid relative path provided to record_access: {relative_filepath}")
         return

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    current_time = time.time()

    cursor.execute("SELECT access_timestamps FROM files WHERE filepath = ?", (relative_filepath,))
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

        cursor.execute("UPDATE files SET access_timestamps = ? WHERE filepath = ?",
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
        FROM files
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
     cursor.execute("SELECT * FROM files WHERE filepath = ?", (relative_filepath,))
     row = cursor.fetchone()
     conn.close()
     return row 

def get_max_mtime_from_db(db_path=DB_PATH) -> Optional[float]: # Return Optional[float]
    """Gets the maximum modification time recorded in the database for 'current' files."""
    max_mtime = None
    try:
        # Ensure DB exists before connecting, or handle error gracefully
        if not Path(db_path).exists():
             logger.warning(f"Database file not found at {db_path}, cannot get max mtime.")
             return None

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(mtime) FROM files WHERE status = 'current'")
        result = cursor.fetchone()
        if result and result[0] is not None:
            max_mtime = result[0]
        conn.close()
        # logger.debug(f"Max mtime from DB: {max_mtime}") # Optional debug
    except sqlite3.Error as e:
        logger.error(f"Database error querying max mtime from 'files' table: {e}")
        max_mtime = None # Return None on error
    return max_mtime

def get_last_scan_time(db_path: str) -> float:
    # ... (function remains the same) ...
    # Ensure this function has an indented body or 'pass'
    pass # Placeholder if body is missing

def get_file_history(db_path: str, filename: str) -> List[Tuple]:
    # --- FIX: Add indentation here ---
    """
    Retrieves the recorded history for a specific file (placeholder implementation).
    Actual implementation would query a history table if you add one.
    For now, it might just return the current details or be empty.
    """
    conn = get_db_connection(Path(db_path))
    cursor = conn.cursor()
    # Assuming you want history based on filename, adjust query if needed
    # This example just gets the current record, not a real history
    cursor.execute("SELECT filepath, last_modified, content_hash FROM files WHERE filename = ?", (filename,))
    rows = cursor.fetchall()
    conn.close()
    # Convert rows to tuples if needed, depending on desired output format
    return [tuple(row) for row in rows]
    # --- End of fix ---

def get_recent_changes(db_path: str, limit: int = 10) -> List[Tuple]:
    # ... (function remains the same) ...
    # Ensure this function has an indented body or 'pass'
    conn = get_db_connection(Path(db_path))
    cursor = conn.cursor()
    cursor.execute("""
        SELECT filepath, last_modified, content_hash
        FROM files
        ORDER BY last_scanned DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [tuple(row) for row in rows]

def undo_last_change(db_path: str) -> Optional[str]:
    # ... (function remains the same) ...
    # Ensure this function has an indented body or 'pass'
    # This function likely needs significant implementation involving file backups
    # or version control integration, which is beyond simple DB state.
    logging.warning("Undo functionality is not fully implemented.")
    return None # Placeholder return

def get_all_files_from_db(db_path: Path = DB_PATH) -> List[Tuple[str, float, int]]:
    """Gets all 'current' files from the database."""
    # ... (implementation) ...
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT path, mtime, size FROM files WHERE status = 'current'") # <-- Use 'files'
        files = [(row['path'], row['mtime'], row['size']) for row in cursor.fetchall()]
        conn.close()
        return files
    except sqlite3.Error as e:
        logger.error(f"Database error getting all files: {e}")
        return []
