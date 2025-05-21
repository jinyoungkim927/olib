# Formatter Update

This document explains how to update your codebase to use the new simplified formatting system.

## What Changed?

The formatting functionality has been refactored to be more modular, efficient and maintainable:

1. Core LaTeX utilities are now in `latex_formatting.py`
2. The main formatter is in `simplified_format_fixer.py`
3. Post-processing utilities are in `simplified_post_process.py`
4. CLI commands are in `simplified_format.py`

This organization improves code clarity, reduces duplication, and simplifies testing.

## How to Update

### Option 1: Use the Migration Script

We've provided a migration script that automatically updates import statements and function calls:

```bash
# Run in dry-run mode first to see what would change
python scripts/migrate_to_simplified_formatter.py --dry-run

# Apply the changes
python scripts/migrate_to_simplified_formatter.py
```

### Option 2: Manual Update

If you prefer to update manually or have custom integrations, here are the key changes:

#### Import Changes

```python
# Old imports
from obsidian_librarian.commands.utilities.format_fixer import FormatFixer
from obsidian_librarian.utils.post_process_formatting import clean_raw_llm_output, post_process_ocr_output

# New imports
from obsidian_librarian.commands.utilities.simplified_format_fixer import FormatFixer
from obsidian_librarian.utils.simplified_post_process import clean_llm_output, process_ocr_output
```

#### Function Name Changes

- `clean_raw_llm_output()` → `clean_llm_output()`
- `post_process_ocr_output()` → `process_ocr_output()`

#### Command Changes

The CLI commands (`olib format fix` and `olib format ocr`) remain the same, but their implementation has changed.

## Testing the Update

After updating, run the tests to ensure everything works correctly:

```bash
# Run tests for the new formatter
pytest obsidian_librarian/tests/test_simplified_formatter.py

# Run all tests
pytest
```

## Benefits of the New System

1. **Simpler Code**: Reduced redundancy and more focused functions
2. **Better LaTeX Support**: Improved handling of mathematical notation
3. **More Reliable OCR**: Enhanced processing of OCR output
4. **Easier Maintenance**: Clearer separation of concerns
5. **Better Performance**: More efficient processing of large files

## Need Help?

If you encounter any issues during the migration, please:

1. Check the documentation in `obsidian_librarian/docs/formatting.md`
2. Run the tests to identify any specific problems
3. Report issues through the regular channels

## Backward Compatibility

While we recommend using the new formatter, the old implementation remains available for now. However, we plan to remove it in a future release.