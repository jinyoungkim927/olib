from setuptools import setup, find_packages
import os

# Define all required dependencies directly
# Combine core requirements and the previous 'analytics' extras
install_requires = [
    # Original Core Dependencies
    'click>=8.0',       # Already included, ensuring version
    'requests',         # Add back
    'openai',           # Add back
    'shellingham',      # Add back (also used for completion extra before)
    'pyperclip',        # Add back
    'sentence-transformers', # For embeddings
    'torch',               # Dependency for sentence-transformers
    'scikit-learn',      # For cosine similarity calculation

    # Analytics Dependencies (previously in 'analytics' extra)
    'pandas>=1.0',
    'matplotlib>=3.0',
    'nbformat>=5.0',
    'plotext>=5.0',
    'GitPython>=3.0',
    'seaborn>=0.11',
]

# Optional: Keep dev dependencies separate if desired
# You might remove the 'completion' extra if shellingham is now core
extras_require = {
    'dev': [
        'pytest',
        'flake8',
        # Add other dev dependencies
    ]
    # 'completion': ['shellingham'] # No longer needed if shellingham is core
}
# Or remove extras_require completely if you only need 'dev' for local testing


setup(
    name="obsidian-librarian",
    version="0.1.1", # Or your current version
    author="Jinyoung Kim",
    author_email="jinyoungkimwork@gmail.com",
    description="A CLI tool for managing Obsidian vaults",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/jinyoungkim927/obsidian_librarian",

    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires, # Use the combined list
    extras_require=extras_require, # Update or remove as needed
    entry_points={
        'console_scripts': [
            'olib=obsidian_librarian.cli:main',
            # Keep other entry points if they are correct
            'olib-format=obsidian_librarian.commands.format:format_notes',
            'olib-check=obsidian_librarian.commands.check:check',
            'olib-search=obsidian_librarian.commands.search:search',
            'olib-notes=obsidian_librarian.commands.notes:notes',
            'olib-analytics=obsidian_librarian.commands.analytics:analytics',
            'olib-config=obsidian_librarian.commands.config:manage_config',
            'olib-history=obsidian_librarian.commands.history:history',
            'olib-undo=obsidian_librarian.commands.undo:undo',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8', # Keep updated requirement
)
