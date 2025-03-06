# Obsidian Librarian (olib) Development Guide

## Installation & Commands
- Install: `pip install -e .` (local development)
- Run: `olib [command] [options]` or `python -m obsidian_librarian.cli [command]`
- Setup: `olib config setup` (configure vault path)
- New commands: Add to `commands/`, register in `cli.py`, `setup.py`, `commands/__init__.py`

## Code Style
- Imports: Standard libraries first, then third-party, then local modules
- Naming: snake_case for functions/variables, PascalCase for classes
- CLI: Use Click library decorators for commands and options
- Docstrings: Use triple quotes with descriptive summaries for all functions
- Error handling: Use try/except with specific exceptions and helpful error messages
- Configuration: Access via get_config() from config.py

## Project Organization
- Commands: Each command in separate module under commands/
- Utils: Shared utility functions in utils/
- Config: User configuration stored in ~/.config/obsidian-librarian
- Prompts: Text templates for AI integrations in prompts/
- Modules: Follow pattern of creating command groups with subcommands

## Testing
- Manually test new commands with demo notes in obsidian_librarian/demo_notes/
- Verify commands work with both `olib` and direct module execution