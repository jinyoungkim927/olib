# Obsidian Librarian Commands

## Notes Commands

### `notes autolink` - Add Wiki-style Links

Automatically link words in notes to their corresponding pages.

```bash
# Link all terms in a single note
olib notes autolink "Note Title"

# Link all terms in all notes
olib notes autolink

# Show detailed information about changes
olib notes autolink --verbose

# Show what would be changed without making changes
olib notes autolink --dry-run
```

Features:
- Preserves existing links
- Handles case insensitivity
- Ignores LaTeX math expressions between $ or $$ delimiters
- Fixes broken link formatting like `[[[]][Topic]]` to `[[Topic]]`
- Prioritizes longer titles to prevent partial matches

### `notes check-garbage` - Find and Clean Up Problematic Files

Identify and manage problematic files in your vault.

```bash
# Check for empty or very small files (default)
olib notes check-garbage

# Run all checks
olib notes check-garbage --all

# Check for specific issues
olib notes check-garbage --empty-only
olib notes check-garbage --duplicate-titles
olib notes check-garbage --broken-links

# Set custom file size thresholds
olib notes check-garbage --min-size 20 --max-size 100000
```

⚠️ Important: Use `--all` with two dashes, not `all` as a positional argument.

Features:
- Identifies empty or very small files
- Finds excessively large files
- Detects case-insensitive duplicate titles
- Finds broken internal links
- Interactive cleanup process
- Clipboard support for saving reports
- Clear summary of issues found

### `notes ocr` - Convert Screenshots to Text

Convert screenshots embedded in notes to text using AI.

```bash
olib notes ocr "Note Title"
```

Features:
- Finds all image references in the `![[image]]` format
- Processes each image with OCR
- Adds the extracted text right after the image reference
- Includes timestamp for OCR processing