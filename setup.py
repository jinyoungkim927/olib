from setuptools import setup, find_packages

setup(
    name="obsidian-librarian",
    version="0.1.1",
    author="Jinyoung Kim",
    author_email="jinyoungkimwork@gmail.com",
    description="A CLI tool for managing Obsidian vaults",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/jinyoungkim927/obsidian_librarian",
    packages=find_packages(),
    install_requires=[
        "click",
        "requests",
        "openai",
        "shellingham",
    ],
    extras_require={
        "completion": ["shellingham"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",  # or whatever license you choose
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
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
