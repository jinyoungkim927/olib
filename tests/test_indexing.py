import pytest
import os
import numpy as np
import pickle
from unittest.mock import patch, MagicMock, ANY # Import ANY
from pathlib import Path
import time
import json
import tempfile

from obsidian_librarian.utils import indexing
from obsidian_librarian.commands import index as index_commands
from obsidian_librarian import config, vault_state

# Mock SentenceTransformer before it's imported by the module under test
@pytest.fixture(autouse=True)
def mock_sentence_transformer():
    """Automatically mock SentenceTransformer where it's imported and used."""
    mock_model_instance = MagicMock()
    # Configure the mock 'encode' method
    def mock_encode(contents, show_progress_bar=False):
         print(f"Mock encode called with {len(contents)} items. show_progress_bar={show_progress_bar}")
         # Use a realistic dimension like 384 for MiniLM
         return np.random.rand(len(contents), 384)

    mock_model_instance.encode.side_effect = mock_encode

    # Mock the SentenceTransformer class constructor to return our mock instance
    mock_transformer_class = MagicMock(return_value=mock_model_instance)

    # --- FIX: Patch the class where it is imported in utils.indexing ---
    # Patch 'SentenceTransformer' within the 'obsidian_librarian.utils.indexing' module
    with patch('obsidian_librarian.utils.indexing.SentenceTransformer', mock_transformer_class) as mock_class:
    # --- End Fix ---
        yield mock_class # Yield the mock class itself

def test_index_vault_normal(temp_vault):
    """Test indexing a vault with a few files."""
    db_path = temp_vault / "test_vault_state.db"
    embeddings_file = temp_vault / "semantic_index.npy"
    map_file = temp_vault / "semantic_index.pkl"
    model_name = "mock-model"

    # Create some dummy files
    (temp_vault / "note1.md").write_text("Content of note 1.")
    (temp_vault / "note2.md").write_text("Content of note 2.")
    (temp_vault / "subdir").mkdir(exist_ok=True)
    (temp_vault / "subdir" / "note3.md").write_text("Content of note 3 in subdir.")

    # Initialize DB and scan
    vault_state.initialize_database(db_path)
    vault_state.update_vault_scan(temp_vault, db_path, quiet=True)

    # Call index_vault - the mock will be used automatically
    indexing.index_vault(
        db_path=db_path,
        vault_path=temp_vault,
        embeddings_path=embeddings_file,
        file_map_path=map_file,
        model_name=model_name
    )

    # Assertions
    assert embeddings_file.exists()
    assert map_file.exists()

    # Load the map and check basic structure (assuming pickle format)
    with open(map_file, 'rb') as f:
        filepath_map = pickle.load(f) # Use pickle.load
    assert isinstance(filepath_map, dict) # Should be a dict mapping index to path
    assert len(filepath_map) == 3 # Should match number of .md files
    # Check that the values are the expected relative paths
    assert "note1.md" in filepath_map.values()
    assert os.path.join("subdir", "note3.md") in filepath_map.values()

    # Load embeddings and check shape
    embeddings = np.load(embeddings_file)
    assert embeddings.shape[0] == 3 # Number of files
    assert embeddings.shape[1] == 384 # Embedding dimension from mock

def test_index_vault_empty(temp_vault):
    """Test indexing an empty vault (no files found in DB)."""
    db_path = temp_vault / "test_vault_state.db"
    embeddings_file = temp_vault / "semantic_index.npy"
    map_file = temp_vault / "semantic_index.pkl"
    model_name = "mock-model"

    # Initialize DB but DO NOT scan the vault
    vault_state.initialize_database(db_path)

    # Call index_vault - it should find 0 files in the DB
    indexing.index_vault(
        db_path=db_path,
        vault_path=temp_vault,
        embeddings_path=embeddings_file,
        file_map_path=map_file,
        model_name=model_name
    )

    # Assertions
    assert embeddings_file.exists()
    assert map_file.exists()

    # Load the map and check it's empty
    with open(map_file, 'rb') as f:
        filepath_map = pickle.load(f)
    assert isinstance(filepath_map, dict)
    assert len(filepath_map) == 0 # Should now be empty

    # Load embeddings and check they are empty
    embeddings = np.load(embeddings_file)
    assert embeddings.shape == (0,) or embeddings.shape == (0, 0) # Check for empty array

def test_load_index_data(temp_vault):
    """Test loading existing and non-existing index data."""
    embeddings_path = str(temp_vault / "test_emb.npy")
    map_path = str(temp_vault / "test_map.pkl")

    # 1. Test loading non-existent files
    emb, fmap = indexing.load_index_data(embeddings_path, map_path)
    assert emb is None
    assert fmap is None

    # 2. Create dummy files and test loading
    dummy_emb = np.array([[1, 2], [3, 4]])
    dummy_map = {0: "file1.md", 1: "file2.md"}
    np.save(embeddings_path, dummy_emb)
    with open(map_path, 'wb') as f:
        pickle.dump(dummy_map, f)

    emb, fmap = indexing.load_index_data(embeddings_path, map_path)
    assert np.array_equal(emb, dummy_emb)
    assert fmap == dummy_map 

@pytest.mark.usefixtures("temp_config_dir")
def test_index_vault_basic(temp_vault, temp_config_dir, mock_sentence_transformer):
    """Test indexing a vault with a few files after scanning."""
    mock_st_class = mock_sentence_transformer

    db_path = temp_config_dir / "vault_state.db"
    embeddings_file = temp_config_dir / "semantic_index.npy"
    map_file = temp_config_dir / "semantic_index.pkl"
    model_name = "mock-model"

    # Initialize DB and scan the temp_vault
    vault_state.initialize_database(db_path)
    # Run scan quietly as it's part of setup
    scan_success = vault_state.update_vault_scan(temp_vault, db_path, quiet=True)
    assert scan_success is True
    # Verify files are in DB after scan
    files_in_db = vault_state.get_all_files_from_db(db_path)
    assert len(files_in_db) == 3 # Expecting note1, note2, subdir/note3

    # Run the indexing function
    indexing.index_vault(
        db_path=db_path,
        vault_path=temp_vault,
        embeddings_path=embeddings_file,
        file_map_path=map_file,
        model_name=model_name
    )

    # Assertions
    assert embeddings_file.exists()
    assert map_file.exists()

    # Check that the mocked SentenceTransformer was initialized
    mock_st_class.assert_called_once_with(model_name)

    # Check that encode was called once
    mock_st_class.return_value.encode.assert_called_once()
    call_args, call_kwargs = mock_st_class.return_value.encode.call_args
    assert len(call_args[0]) == 3 # Should have encoded 3 documents found in DB
    assert call_kwargs.get('show_progress_bar') is True # Check progress bar arg

    # Verify content of saved files (optional but good)
    embeddings = np.load(embeddings_file)
    assert embeddings.shape[0] == 3 # 3 embeddings

    with open(map_file, 'rb') as f:
        file_map = pickle.load(f)
    assert len(file_map) == 3
    assert file_map[0] == "note1.md" # Check relative paths
    assert file_map[1] == "note2.md"
    assert file_map[2] == "subdir/note3.md"

@pytest.mark.usefixtures("temp_config_dir")
def test_index_vault_no_files_in_db(temp_config_dir, mock_sentence_transformer):
    """Test indexing when the DB scan finds no files."""
    mock_st_class = mock_sentence_transformer

    db_path = temp_config_dir / "vault_state.db"
    embeddings_file = temp_config_dir / "semantic_index.npy"
    map_file = temp_config_dir / "semantic_index.pkl"
    model_name = "mock-model"
    # Create an empty temp vault just for path reference, don't scan it
    with tempfile.TemporaryDirectory() as empty_vault_dir:
        empty_vault_path = Path(empty_vault_dir)

        # Initialize DB, but DO NOT scan a vault with files
        vault_state.initialize_database(db_path)
        # Ensure DB is empty
        files_in_db = vault_state.get_all_files_from_db(db_path)
        assert len(files_in_db) == 0

        # Run indexing
        indexing.index_vault(
            db_path=db_path,
            vault_path=empty_vault_path,
            embeddings_path=embeddings_file,
            file_map_path=map_file,
            model_name=model_name
        )

        # Assertions
        assert embeddings_file.exists() # Files should still be created (empty)
        assert map_file.exists()
        # Check that the mocked SentenceTransformer was NOT initialized
        mock_st_class.assert_not_called()
        # Check that encode was NOT called
        mock_st_class.return_value.encode.assert_not_called()

        # Check files are empty
        embeddings = np.load(embeddings_file)
        assert embeddings.shape == (0,) or embeddings.shape == (0,0) # Allow for different empty shapes

        with open(map_file, 'rb') as f:
            file_map = pickle.load(f)
        assert file_map == {} 
