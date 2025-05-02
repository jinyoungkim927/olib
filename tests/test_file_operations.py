import pytest
import os
from pathlib import Path
from obsidian_librarian.utils.file_operations import read_note_content, find_note_in_vault

# --- Tests for read_note_content ---

def test_read_note_content_simple_utf8(tmp_path):
    """Test reading a basic UTF-8 encoded file."""
    file_path = tmp_path / "test_utf8.md"
    expected_content = "This is a simple test.\nWith multiple lines."
    file_path.write_text(expected_content, encoding='utf-8')

    content = read_note_content(file_path)
    assert content == expected_content

def test_read_note_content_extended_utf8(tmp_path):
    """Test reading UTF-8 with non-ASCII characters."""
    file_path = tmp_path / "test_extended_utf8.md"
    expected_content = "Test with special characters: éàçüñ €"
    file_path.write_text(expected_content, encoding='utf-8')

    content = read_note_content(file_path)
    assert content == expected_content

def test_read_note_content_latin1_fallback(tmp_path):
    """Test reading a file encoded in latin-1 (simulating bad UTF-8)."""
    file_path = tmp_path / "test_latin1.md"
    # Simulate latin-1 content that would break UTF-8 decoding
    # Example: byte 0xA9 (copyright symbol in latin-1)
    expected_content = "Copyright © symbol"
    file_path.write_bytes(expected_content.encode('latin-1'))

    content = read_note_content(file_path)
    assert content == expected_content # Should fall back and read correctly

def test_read_note_content_non_existent_file(tmp_path):
    """Test reading a file that does not exist."""
    file_path = tmp_path / "non_existent.md"
    content = read_note_content(file_path)
    assert content is None

def test_read_note_content_directory(tmp_path):
    """Test attempting to read a directory."""
    dir_path = tmp_path / "a_directory"
    dir_path.mkdir()
    content = read_note_content(dir_path)
    assert content is None

# --- Tests for find_note_in_vault ---

@pytest.fixture
def mock_vault(tmp_path):
    """Creates a mock vault structure for testing find_note_in_vault."""
    vault_dir = tmp_path / "TestVault"
    vault_dir.mkdir()

    # Create some notes
    (vault_dir / "Root Note.md").write_text("Content of root note.")
    (vault_dir / "Another Root.md").write_text("More root content.")

    folder1 = vault_dir / "Folder A"
    folder1.mkdir()
    (folder1 / "Note In A.md").write_text("Content A.")

    subfolder = folder1 / "Subfolder B"
    subfolder.mkdir()
    (subfolder / "Deep Note.md").write_text("Deep content.")
    (subfolder / "DEEP NOTE.md").write_text("Case variant.") # Test case insensitivity later

    # Create an ambiguous note name
    folder2 = vault_dir / "Folder C"
    folder2.mkdir()
    (folder2 / "Ambiguous Note.md").write_text("Ambiguous C.")
    (vault_dir / "Ambiguous Note.md").write_text("Ambiguous Root.")

    # Create a non-markdown file
    (vault_dir / "config.txt").write_text("some config")

    return vault_dir

def test_find_note_by_base_name(mock_vault):
    """Find a unique note by its base name."""
    result = find_note_in_vault(str(mock_vault), "Root Note")
    assert result is not None
    assert result.name == "Root Note.md"
    assert result.parent == mock_vault

def test_find_note_by_name_with_extension(mock_vault):
    """Find a unique note by its full name."""
    result = find_note_in_vault(str(mock_vault), "Root Note.md")
    assert result is not None
    assert result.name == "Root Note.md"

def test_find_note_by_relative_path(mock_vault):
    """Find a note using its relative path without extension."""
    result = find_note_in_vault(str(mock_vault), "Folder A/Note In A")
    assert result is not None
    assert result.name == "Note In A.md"
    assert result.parent.name == "Folder A"

def test_find_note_by_relative_path_with_extension(mock_vault):
    """Find a note using its relative path with extension."""
    result = find_note_in_vault(str(mock_vault), "Folder A/Note In A.md")
    assert result is not None
    assert result.name == "Note In A.md"

def test_find_note_deep_relative_path(mock_vault):
    """Find a note deep within the folder structure."""
    result = find_note_in_vault(str(mock_vault), "Folder A/Subfolder B/Deep Note")
    assert result is not None
    assert result.name == "Deep Note.md"

def test_find_note_case_insensitive_name(mock_vault):
    """Find a note using a case-insensitive base name."""
    # Note: The current implementation finds based on stem.lower(),
    # so it might find either "Deep Note.md" or "DEEP NOTE.md".
    # Let's test finding "root note"
    result = find_note_in_vault(str(mock_vault), "root note")
    assert result is not None
    assert result.name == "Root Note.md"

def test_find_note_ambiguous_name(mock_vault):
    """Test finding a note when the name exists in multiple locations."""
    result = find_note_in_vault(str(mock_vault), "Ambiguous Note")
    assert result is None # Should return None for ambiguous matches

def test_find_note_non_existent(mock_vault):
    """Test finding a note that does not exist."""
    result = find_note_in_vault(str(mock_vault), "Non Existent Note")
    assert result is None

def test_find_note_matches_folder_name(mock_vault):
    """Test identifier matching a folder name (should not match)."""
    result = find_note_in_vault(str(mock_vault), "Folder A")
    assert result is None # Should only find files

def test_find_note_invalid_vault_path(tmp_path):
    """Test finding a note with an invalid vault path."""
    invalid_path = str(tmp_path / "NotAVault")
    result = find_note_in_vault(invalid_path, "Any Note")
    assert result is None

def test_find_note_non_markdown_ignored(mock_vault):
    """Ensure non-markdown files are ignored."""
    result = find_note_in_vault(str(mock_vault), "config")
    assert result is None
    result = find_note_in_vault(str(mock_vault), "config.txt")
    assert result is None 