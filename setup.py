from setuptools import setup, find_packages

setup(
    name="obsidian-librarian",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'click',
    ],
    entry_points={
        'console_scripts': [
            # This is where you can add more commands/functions in your project
            # ex) 'obsidian-searchn=obsidian_librarian.main:search_files',
            'obsidian-librarian=obsidian_librarian.main:list_directory',
        ],
    },
    author="Your Name",
    description="A simple directory listing tool",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
)
