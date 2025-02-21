#!/usr/bin/env python
import subprocess
import sys
from obsidian_librarian.shell_setup import install_completions

def post_install():
    print("Running post-install setup...")
    try:
        # Run welcome animation
        subprocess.call([sys.executable, "-m", "obsidian_librarian.load_package"])
        # Install shell completions
        install_completions()
    except Exception as e:
        print(f"Error during post-install: {e}")

if __name__ == "__main__":
    post_install()
