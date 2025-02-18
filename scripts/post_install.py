#!/usr/bin/env python
import subprocess
import sys

def post_install():
    print("Running post-install welcome animation...")
    try:
        subprocess.call([sys.executable, "-m", "obsidian_librarian.load_package"])
    except Exception as e:
        print(f"Error running welcome animation: {e}")

if __name__ == "__main__":
    post_install()
