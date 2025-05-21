# Obsidian Librarian (olib) Development Guide

## Installation & Commands

- Install: `pip install -e .` (local development)
- Run: `olib [command] [options]` or `python -m obsidian_librarian.cli [command]`
- Setup: `olib config setup` (configure vault path)
- New commands: Add to `commands/`, register in `cli.py`, `setup.py`, `commands/__init__.py`

## Code Style

- Imports: Standard libraries first, then third-party, then local modules
- RESPECT THE STRUCTURE OF THE DIRECTORY TREE. HERE IT IS CURRENTLY, FIT YOUR CODE TO THIS STRUCTURE.
.
├── CLAUDE.md
├── README.md
├── docs
│   └── commands.md
├── obsidian_librarian
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-311.pyc
│   │   ├── __init__.cpython-39.pyc
│   │   ├── cli.cpython-311.pyc
│   │   ├── cli.cpython-39.pyc
│   │   ├── config.cpython-311.pyc
│   │   ├── config.cpython-39.pyc
│   │   ├── initial_setup.cpython-39.pyc
│   │   ├── load_package.cpython-311.pyc
│   │   ├── load_package.cpython-39.pyc
│   │   ├── setup_command.cpython-311.pyc
│   │   ├── setup_command.cpython-39.pyc
│   │   ├── vault_state.cpython-311.pyc
│   │   └── vault_state.cpython-39.pyc
│   ├── cli.py
│   ├── commands
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-311.pyc
│   │   │   ├── __init__.cpython-39.pyc
│   │   │   ├── analytics.cpython-311.pyc
│   │   │   ├── analytics.cpython-39.pyc
│   │   │   ├── autolink.cpython-311.pyc
│   │   │   ├── autolink.cpython-39.pyc
│   │   │   ├── check.cpython-311.pyc
│   │   │   ├── check.cpython-39.pyc
│   │   │   ├── config.cpython-311.pyc
│   │   │   ├── config.cpython-39.pyc
│   │   │   ├── fixed_latex_linking.cpython-311.pyc
│   │   │   ├── fixed_latex_linking.cpython-39.pyc
│   │   │   ├── format.cpython-311.pyc
│   │   │   ├── format.cpython-39.pyc
│   │   │   ├── history.cpython-311.pyc
│   │   │   ├── history.cpython-39.pyc
│   │   │   ├── index.cpython-39.pyc
│   │   │   ├── latex_aware_linking.cpython-39.pyc
│   │   │   ├── notes.cpython-311.pyc
│   │   │   ├── notes.cpython-39.pyc
│   │   │   ├── search.cpython-311.pyc
│   │   │   ├── search.cpython-39.pyc
│   │   │   ├── undo.cpython-311.pyc
│   │   │   └── undo.cpython-39.pyc
│   │   ├── analytics.py
│   │   ├── check.py
│   │   ├── config.py
│   │   ├── fixed_latex_linking.py
│   │   ├── fixed_notes.py
│   │   ├── format.py
│   │   ├── history.py
│   │   ├── index.py
│   │   ├── latex_aware_linking.py
│   │   ├── notes.py
│   │   ├── ocr.py
│   │   ├── search.py
│   │   ├── undo.py
│   │   └── utilities
│   │       ├── __init__.py
│   │       ├── __pycache__
│   │       │   ├── __init__.cpython-311.pyc
│   │       │   ├── __init__.cpython-39.pyc
│   │       │   ├── format_fixer.cpython-311.pyc
│   │       │   ├── format_fixer.cpython-39.pyc
│   │       │   └── history_manager.cpython-39.pyc
│   │       ├── format_fixer.py
│   │       └── history_manager.py
│   ├── config.py
│   ├── dev_setup.py
│   ├── initial_setup.py
│   ├── list_directory.py
│   ├── load_package.py
│   ├── prompts
│   │   ├── check_understanding.txt
│   │   ├── default.txt
│   │   ├── ocr_prompt.txt
│   │   └── technical_content_imprecise_summary.txt
│   ├── shell_setup.py
│   ├── utils
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-311.pyc
│   │   │   ├── __init__.cpython-39.pyc
│   │   │   ├── ai.cpython-311.pyc
│   │   │   ├── ai.cpython-39.pyc
│   │   │   ├── file_operations.cpython-311.pyc
│   │   │   ├── file_operations.cpython-39.pyc
│   │   │   ├── formatting.cpython-39.pyc
│   │   │   ├── indexing.cpython-311.pyc
│   │   │   ├── indexing.cpython-39.pyc
│   │   │   ├── post_process_formatting.cpython-311.pyc
│   │   │   └── post_process_formatting.cpython-39.pyc
│   │   ├── ai.py
│   │   ├── file_operations.py
│   │   ├── formatting.py
│   │   ├── indexing.py
│   │   └── post_process_formatting.py
│   └── vault_state.py
├── obsidian_librarian.egg-info
│   ├── PKG-INFO
│   ├── SOURCES.txt
│   ├── dependency_links.txt
│   ├── entry_points.txt
│   ├── requires.txt
│   └── top_level.txt
├── readme_assets
│   └── librarians.webp
├── scripts
│   ├── debug_cli.py
│   ├── direct_fix.py
│   ├── direct_format.py
│   ├── fix_notes.py
│   ├── format_and_undo.py
│   ├── post_install.py
│   ├── simple_debug.py
│   └── standalone_formatter.py
├── setup.cfg
├── setup.py
└── tests
    ├── __pycache__
    │   ├── conftest.cpython-39-pytest-7.1.1.pyc
    │   ├── debug_test.cpython-39-pytest-7.1.1.pyc
    │   ├── run_cli_test.cpython-39-pytest-7.1.1.pyc
    │   ├── test_cli_integration.cpython-39-pytest-7.1.1.pyc
    │   ├── test_config.cpython-39-pytest-7.1.1.pyc
    │   ├── test_file_operations.cpython-39-pytest-7.1.1.pyc
    │   ├── test_fix.cpython-39-pytest-7.1.1.pyc
    │   ├── test_fixer_method.cpython-39-pytest-7.1.1.pyc
    │   ├── test_format.cpython-39-pytest-7.1.1.pyc
    │   ├── test_format_command.cpython-39-pytest-7.1.1.pyc
    │   ├── test_format_fix.cpython-39-pytest-7.1.1.pyc
    │   ├── test_format_fixer.cpython-39-pytest-7.1.1.pyc
    │   ├── test_formatter.cpython-39-pytest-7.1.1.pyc
    │   ├── test_indexing.cpython-39-pytest-7.1.1.pyc
    │   └── test_undo_command.cpython-39-pytest-7.1.1.pyc
    ├── conftest.py
    ├── debug_test.py
    ├── formatting
    │   ├── ex_0_format_fix
    │   │   ├── after.md
    │   │   ├── before.md
    │   │   └── ideal.md
    │   ├── ex_0_ocr
    │   │   ├── after.md
    │   │   ├── before.md
    │   │   └── output.txt
    │   └── ex_1_format_fix
    │       ├── after.md
    │       ├── before.md
    │       └── ideal.md
    ├── run_cli_test.py
    ├── test_cli_integration.py
    ├── test_config.py
    ├── test_file_operations.py
    ├── test_fix.py
    ├── test_fixer_method.py
    ├── test_format.py
    ├── test_format_command.py
    ├── test_format_fix.py
    ├── test_format_fixer.py
    ├── test_formatter.py
    ├── test_indexing.py
    ├── test_undo_command.py
    └── utils
        ├── __pycache__
        │   └── test_indexing.cpython-39-pytest-7.1.1.pyc
        └── test_indexing.py

22 directories, 150 files

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
- Specifically to test formatting (both with format fix command and for ocr command), use the `format` command with the `before.md` and `after.md` files in the tests/formatting/ directory, where there are specific note example directories. Inside each, you will see three files: `before.md`, `after.md` and `ideal.md` your code should be able to take the `before.md` file and format it to the `ideal.md` file. You can use the `ideal.md` file as a reference for the formatting you want to achieve. You can see the 'after.md' file to see what the currently buggy code outputs. Sometimes you'll see output.txt which is the terminal output as well.
- Verify commands work with both `olib` and direct module execution
