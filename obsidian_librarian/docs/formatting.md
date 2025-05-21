# Formatting Module

This document explains the simplified formatting functionality in Obsidian Librarian.

## Overview

The formatting module handles:
1. LaTeX math formatting in Markdown
2. OCR text processing for screenshots
3. General Markdown formatting (bullet points, wiki links, etc.)

## Architecture

The formatting module has been simplified and reorganized into these components:

### Core LaTeX Utilities
`obsidian_librarian/utils/latex_formatting.py`

This module contains essential functions for LaTeX formatting:
- Protecting code blocks during formatting
- Extracting and processing math blocks
- Fixing math content (underscores, spacing, etc.)
- Formatting display and inline math

### Formatter
`obsidian_librarian/commands/utilities/simplified_format_fixer.py`

The `FormatFixer` class handles:
- Markdown file formatting
- File/directory/vault traversal
- Backup and history tracking
- Test file handling

### Post-Processing
`obsidian_librarian/utils/simplified_post_process.py`

This module focuses on cleaning OCR and LLM-generated text:
- LaTeX command fixes
- Math delimiter normalization
- Spacing and layout improvements

### CLI Commands
`obsidian_librarian/commands/simplified_format.py`

The command-line interface for:
- Formatting notes (`fix` command)
- OCR processing of images (`ocr` command)

## Key Improvements

1. **Separation of concerns**
   - LaTeX formatting utilities are now in a dedicated module
   - Test handling logic is cleanly separated from main functionality

2. **Simplified processing flow**
   - Clearer sequence of formatting operations
   - Better handling of code blocks and LaTeX math

3. **More robust math processing**
   - Improved handling of LaTeX underscores and other special characters
   - Better preservation of math formatting

4. **Consolidated OCR processing**
   - More focused OCR-specific formatting
   - Cleaner integration with GPT-4 Vision

## Usage

### Command Line

```bash
# Format a specific note
olib format fix my-note

# Format the entire vault
olib format fix

# Process images in a note
olib format ocr my-note
```

### Python API

```python
from obsidian_librarian.commands.utilities.simplified_format_fixer import FormatFixer

# Create a formatter
formatter = FormatFixer(verbose=True)

# Format a file
formatter.format_file("path/to/file.md")

# Format a directory
formatter.format_directory("path/to/directory")
```

## Testing

The formatter includes comprehensive tests:
- Unit tests for individual formatting functions
- Integration tests for the entire formatting pipeline
- Specific tests for OCR post-processing