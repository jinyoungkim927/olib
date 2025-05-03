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

def get_max_mtime_from_db(db_path: Optional[Path] = None) -> Optional[float]:
    """Gets the maximum modification time recorded in the database for 'current' files."""
    if db_path is None:
        db_path = DB_PATH

    max_mtime = None
    conn = None
    try:
        if not db_path.exists():
             logger.warning(f"Database file not found at {db_path}, cannot get max mtime.")
             return None

        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(mtime) FROM files WHERE status = 'current'")
        result = cursor.fetchone()
        if result and result[0] is not None:
            max_mtime = result[0]
        logger.debug(f"Max mtime from DB: {max_mtime}")
    except sqlite3.Error as e:
        logger.error(f"Database error querying max mtime from 'files' table: {e}")
        max_mtime = None # Return None on error
    finally:
        if conn:
            conn.close()
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

def get_all_files_from_db(db_path: Optional[Path] = None) -> List[Tuple[str, float, int]]:
    """Gets all 'current' files from the database."""
    if db_path is None:
        db_path = DB_PATH
    conn = None
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT path, mtime, size FROM files WHERE status = 'current'")
        files = [(row['path'], row['mtime'], row['size']) for row in cursor.fetchall()]
        return files
    except sqlite3.Error as e:
        logger.error(f"Database error getting all files: {e}")
        return []
    finally:
        if conn:
            conn.close()

# --- VaultStateManager Class ---

class VaultStateManager:
    """Manages the state of the Obsidian vault using an SQLite database."""

    def __init__(self, vault_path: str, db_path: Optional[Path] = None):
        """
        Initializes the VaultStateManager.

        Args:
            vault_path: The absolute path to the Obsidian vault.
            db_path: Optional path to the database file. Defaults to standard location.
        """
        self.vault_path = Path(vault_path)
        self.db_path = db_path if db_path else DB_PATH
        self.conn = None
        try:
            # Ensure DB is initialized before connecting
            initialize_database(self.db_path)
            self.conn = get_db_connection(self.db_path)
            logger.debug(f"VaultStateManager initialized for vault: {self.vault_path}, DB: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize VaultStateManager connection: {e}")
            # Should we raise here? Or allow creation but fail on methods?
            # For now, log and conn will be None, methods should check.
            self.conn = None

    def _scan_and_update(self, full_scan: bool, quiet: bool = False) -> Tuple[int, int, int]:
        """Internal method to perform the actual scan (full or incremental)."""
        if not self.conn:
            logger.error("Database connection not established. Cannot perform scan.")
            return 0, 0, 0 # Return zero counts

        changes_made = False
        added_count, modified_count, deleted_count = 0, 0, 0
        processed_during_scan = {} # Files found on disk during this scan
        scan_start_time = time.time()

        cursor = self.conn.cursor()

        try:
            # Get current state from DB
            cursor.execute("SELECT path, mtime, size FROM files WHERE status = 'current'")
            db_files = {row['path']: {'mtime': row['mtime'], 'size': row['size']} for row in cursor.fetchall()}
            db_paths_before_scan = set(db_files.keys())

            scan_since_mtime = 0.0
            if not full_scan:
                max_mtime_result = cursor.execute("SELECT MAX(mtime) FROM files WHERE status = 'current'").fetchone()
                if max_mtime_result and max_mtime_result[0] is not None:
                    scan_since_mtime = max_mtime_result[0]
                if not quiet:
                    last_scan_dt = datetime.fromtimestamp(scan_since_mtime).strftime('%Y-%m-%d %H:%M:%S') if scan_since_mtime > 0 else "beginning"
                    logger.info(f"Performing incremental scan for files modified since {last_scan_dt}...")
            elif not quiet:
                logger.info(f"Performing full scan of vault: {self.vault_path}...")

            if not self.vault_path.is_dir():
                 logger.error(f"Vault path '{self.vault_path}' not found during scan.")
                 return 0, 0, 0

            # --- Scan filesystem ---
            for item in self.vault_path.rglob('*.md'): # Only scan markdown files
                if item.is_file():
                    try:
                        stats = item.stat()
                        # Skip if incremental and not modified since last known max mtime
                        if not full_scan and stats.st_mtime <= scan_since_mtime:
                            continue
                        rel_path = item.relative_to(self.vault_path)
                        rel_path_str = str(rel_path)
                        processed_during_scan[rel_path_str] = {'mtime': stats.st_mtime, 'size': stats.st_size}
                    except Exception as e:
                         logger.warning(f"Could not process file {item}: {e}")

            # --- Process scanned files (Additions/Modifications) ---
            for rel_path_str, file_info in processed_during_scan.items():
                db_entry = db_files.get(rel_path_str)
                if db_entry is None:
                    # New file
                    logger.debug(f"Adding new file: {rel_path_str}")
                    cursor.execute(
                        "INSERT OR REPLACE INTO files (path, mtime, size, status) VALUES (?, ?, ?, ?)",
                        (rel_path_str, file_info['mtime'], file_info['size'], 'current')
                    )
                    added_count += 1
                    changes_made = True
                elif file_info['mtime'] > db_entry['mtime'] or file_info['size'] != db_entry['size']:
                    # Modified file
                    logger.debug(f"Updating modified file: {rel_path_str}")
                    cursor.execute(
                        "UPDATE files SET mtime = ?, size = ? WHERE path = ?",
                        (file_info['mtime'], file_info['size'], rel_path_str)
                    )
                    modified_count += 1
                    changes_made = True

            # --- Deletion Check ---
            # Determine paths potentially deleted based on scan type
            if full_scan:
                # In a full scan, any DB path not found on disk is deleted
                deleted_paths = db_paths_before_scan - set(processed_during_scan.keys())
            else:
                # In incremental, check existence only for files *not* processed (i.e., older than scan_since_mtime)
                # and not found in the current scan results (which handles modifications of older files)
                paths_to_check_existence = db_paths_before_scan - set(processed_during_scan.keys())
                deleted_paths = set()
                existence_check_start_time = time.time()
                for rel_path_str in paths_to_check_existence:
                    abs_path = self.vault_path / rel_path_str
                    if not abs_path.exists():
                        deleted_paths.add(rel_path_str)
                existence_check_duration = time.time() - existence_check_start_time
                logger.debug(f"Incremental deletion check duration: {existence_check_duration:.4f}s for {len(paths_to_check_existence)} files")

            # Mark deleted paths in DB
            for rel_path_str in deleted_paths:
                scan_type_log = "[Full Scan]" if full_scan else "[Incremental Scan]"
                logger.debug(f"{scan_type_log} Marking deleted file: {rel_path_str}")
                cursor.execute("UPDATE files SET status = 'deleted' WHERE path = ?", (rel_path_str,))
                deleted_count += 1
                changes_made = True

            # --- Commit and report ---
            if changes_made:
                self.conn.commit()
                if not quiet:
                    summary = []
                    if added_count: summary.append(f"{added_count} added")
                    if modified_count: summary.append(f"{modified_count} modified")
                    if deleted_count: summary.append(f"{deleted_count} deleted")
                    scan_type = "Full scan" if full_scan else "Incremental scan"
                    logger.info(f"{scan_type} complete. Changes: {', '.join(summary) if summary else 'None'}.")
            elif not quiet:
                scan_type = "Full scan" if full_scan else "Incremental scan"
                logger.info(f"{scan_type} complete. No changes detected.")

            scan_duration = time.time() - scan_start_time
            logger.debug(f"Vault scan duration ({'full' if full_scan else 'incremental'}): {scan_duration:.2f} seconds. Added: {added_count}, Modified: {modified_count}, Deleted: {deleted_count}")

            return added_count, modified_count, deleted_count

        except sqlite3.Error as e:
            logger.error(f"Database error during scan: {e}")
            # Optionally rollback changes if needed: self.conn.rollback()
            return 0, 0, 0 # Return zero counts on error

    def incremental_scan(self, quiet: bool = False) -> Tuple[int, int, int]:
        """Performs an incremental scan of the vault."""
        return self._scan_and_update(full_scan=False, quiet=quiet)

    def full_scan(self, quiet: bool = False) -> Tuple[int, int, int]:
        """Performs a full scan of the vault."""
        return self._scan_and_update(full_scan=True, quiet=quiet)

    def close(self):
        """Closes the database connection."""
        if self.conn:
            logger.debug("Closing VaultStateManager DB connection.")
            self.conn.close()
            self.conn = None

    def __enter__(self):
        """Enter context manager."""
        # Connection is already established in __init__ if successful
        if not self.conn:
             # Try to reconnect if initialization failed? Or just raise?
             raise ConnectionError("VaultStateManager database connection failed on initialization.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager, ensuring connection is closed."""
        self.close()

# --- End VaultStateManager Class ---

# Remove the old standalone update_vault_scan function if it exists
# (The logic is now inside the VaultStateManager class)

# Keep other standalone functions like record_access, get_recent_files etc. if needed
# Make sure they use get_db_connection() or accept an explicit connection/cursor.

# Example: Modify get_file_details to use the standard path getter
def get_file_details(relative_filepath: str, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
     """Gets all details for a file from the database."""
     if db_path is None:
         db_path = DB_PATH

     # Basic validation
     if not relative_filepath or relative_filepath.startswith('/') or '..' in relative_filepath:
         logger.warning(f"Invalid relative path provided to get_file_details: {relative_filepath}")
         return None

     conn = None
     try:
         conn = get_db_connection(db_path)
         cursor = conn.cursor()
         # Use path column name from CREATE TABLE statement
         cursor.execute("SELECT * FROM files WHERE path = ?", (relative_filepath,))
         row = cursor.fetchone()
         return row
     except sqlite3.Error as e:
         logger.error(f"Database error in get_file_details for {relative_filepath}: {e}")
         return None
     finally:
         if conn:
             conn.close()

# Remove or update other functions like get_file_history, get_recent_changes, undo_last_change
# as they were placeholders or need significant implementation.
# For example, history/undo would likely need a separate table or Git integration.
