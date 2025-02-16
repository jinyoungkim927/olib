from .config import setup_vault_path
import sys

def configure_dev():
    """First animation runs, then this prompts for the vault path (if interactive)."""
    print("Development Setup Mode")

    # Ensure it's interactive before prompting
    if sys.stdin.isatty():
        setup_vault_path()
    else:
        print("Non-interactive install detected. Run 'python -m obsidian_librarian.dev_setup' manually to configure.")

    print("Configuration complete!")

if __name__ == "__main__":
    configure_dev()
