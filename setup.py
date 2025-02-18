from setuptools import setup, find_packages

setup(
    name="obsidian-librarian",
    version="0.1.1",
    packages=find_packages(),
    install_requires=['click'],
    entry_points={
        'console_scripts': [
            'olib=obsidian_librarian.list_directory:list_directory',
            'olib-setup=obsidian_librarian.setup_command:run_setup',
        ],
    },
)
