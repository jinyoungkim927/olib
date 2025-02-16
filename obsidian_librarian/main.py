import os
import click

@click.command()
def list_directory():
    """Lists all files in the current directory"""
    files = os.listdir('.')
    for file in files:
        print(file)

if __name__ == '__main__':
    list_directory()
