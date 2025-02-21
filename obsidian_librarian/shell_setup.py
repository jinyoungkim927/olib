import os
import click
from pathlib import Path

def install_completions():
    """Install shell completions automatically"""
    shell = os.environ.get("SHELL", "").lower()
    home = Path.home()
    
    if "zsh" in shell:
        rc_file = home / ".zshrc"
        completion_command = '\neval "$(_OLIB_COMPLETE=zsh_source olib)"\n'
    elif "bash" in shell:
        rc_file = home / ".bashrc"
        completion_command = '\neval "$(_OLIB_COMPLETE=bash_source olib)"\n'
    elif "fish" in shell:
        rc_file = home / ".config/fish/config.fish"
        completion_command = '\neval (env _OLIB_COMPLETE=fish_source olib)\n'
    else:
        click.echo("Unsupported shell or shell not detected. Please configure completions manually.")
        return False

    try:
        # Create parent directories if they don't exist
        rc_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if completion is already installed
        if rc_file.exists():
            with open(rc_file, 'r') as f:
                if completion_command.strip() in f.read():
                    click.echo("Shell completions already installed.")
                    return True

        # Append completion command to rc file
        with open(rc_file, 'a') as f:
            f.write(completion_command)
        
        click.echo(f"Shell completions installed successfully in {rc_file}")
        click.echo("Please restart your shell or run:")
        click.echo(f"source {rc_file}")
        return True
    
    except Exception as e:
        click.echo(f"Error installing completions: {e}")
        return False 
