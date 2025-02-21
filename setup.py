from setuptools import setup, find_packages

setup(
    name="obsidian-librarian",
    version="0.1.1",
    packages=find_packages(),
    install_requires=['click', 'requests'],
    entry_points={
        'console_scripts': [
            'olib=obsidian_librarian.cli:main',
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
)
