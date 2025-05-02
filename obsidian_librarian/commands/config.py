import click
import os
import json
from pathlib import Path
from typing import Optional, Dict
import time
from ..initial_setup import run_setup
from ..config import (
    get_config_dir,
    get_config,
    get_vault_path_from_config,
    save_config as save_config_main, # Rename to avoid conflict
    setup_vault_path as setup_vault_path_main, # Rename
    get_auto_update_settings,
    set_auto_update_setting,
    DEFAULT_AUTO_UPDATE_INTERVAL_SECONDS
)

@click.group(name="config")
def manage_config():
    """View or modify olib configuration."""
    pass

@manage_config.command()
def setup():
    """Run initial setup (Vault Path)."""
    click.echo("Starting Obsidian Librarian setup...")
    setup_vault_path_main()
    # Add setup for API keys etc. here later if needed
    click.echo("\nSetup complete. Configuration saved.")

@manage_config.command()
def show():
    """Show current configuration."""
    config = get_config()
    if not config:
        click.echo("Configuration file not found or empty. Run 'olib config setup'.")
        return

    click.echo("Current Configuration:")
    # Display vault path nicely
    vault_path = config.get('vault_path')
    click.echo(f"  Vault Path: {vault_path if vault_path else 'Not Set'}")

    # Display auto-update settings
    auto_update = get_auto_update_settings()
    enabled_str = "Enabled" if auto_update['enabled'] else "Disabled"
    interval_min = auto_update['interval_seconds'] // 60
    last_scan_ts = auto_update['last_scan_timestamp']
    last_scan_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_scan_ts)) if last_scan_ts > 0 else "Never"

    click.echo(f"\n  Auto Update Index:")
    click.echo(f"    Status: {enabled_str}")
    click.echo(f"    Interval: {interval_min} minutes ({auto_update['interval_seconds']} seconds)")
    click.echo(f"    Last Auto Scan Timestamp: {last_scan_str}")

    # Display other config items if added later
    # e.g., API keys (masked)

@manage_config.command(name="auto-update")
@click.option('--enable', 'status', flag_value=True, help='Enable automatic index updates on command run.')
@click.option('--disable', 'status', flag_value=False, help='Disable automatic index updates.')
@click.option('--interval', type=int, help=f'Set update check interval in minutes (default: {DEFAULT_AUTO_UPDATE_INTERVAL_SECONDS // 60}). Minimum 1.')
def configure_auto_update(status=None, interval=None):
    """Configure automatic index update settings."""
    if status is not None:
        set_auto_update_setting("auto_update_enabled", status)

    if interval is not None:
        if interval < 1:
            click.echo("Error: Interval must be at least 1 minute.", err=True)
            return
        set_auto_update_setting("auto_update_interval_seconds", interval * 60)

    if status is None and interval is None:
        # If no options given, show current settings
        click.echo("Current auto-update settings (use --enable/--disable/--interval to modify):")
        show() # Reuse the show command's logic indirectly

@manage_config.command()
def save():
    click.echo("Saving config...")

@manage_config.command()
def load():
    click.echo("Loading config...")

@manage_config.command()
def setup():
    """Run the initial setup process"""
    run_setup()
