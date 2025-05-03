import click
import os
import re
from pathlib import Path
from datetime import datetime
import statistics

# Keep standard library imports at top

from ..config import get_config, save_config, get_vault_path_from_config
from .. import vault_state
from ..utils.file_operations import get_markdown_files, count_words

def get_note_stats(vault_path: str) -> list[dict]:
    """Gathers statistics for each note."""
    stats = []
    markdown_files = get_markdown_files(vault_path)
    for file_path in markdown_files:
        try:
            p = Path(file_path)
            content = p.read_text(encoding='utf-8')
            word_count = count_words(content)
            mtime = p.stat().st_mtime
            stats.append({
                'path': file_path,
                'filename': p.name,
                'word_count': word_count,
                'modified_time': datetime.fromtimestamp(mtime)
            })
        except Exception as e:
            click.echo(f"Warning: Could not process file {file_path}: {e}", err=True)
    return stats

@click.group()
def analytics():
    """Analyze vault statistics and history."""
    pass

@analytics.command()
@click.option('--sort-by', type=click.Choice(['words', 'modified', 'name']), default='modified', help='Sort criteria.')
@click.option('--limit', type=int, default=10, help='Number of notes to show.')
@click.option('--reverse', is_flag=True, help='Reverse sort order.')
def summary(sort_by, limit, reverse):
    """Show a summary of vault statistics."""
    # Import pandas only when summary is called
    try:
        import pandas as pd
    except ImportError:
        click.echo("Error: pandas library is required for summary. Install with 'pip install pandas'", err=True)
        return

    vault_path = get_vault_path_from_config()
    if not vault_path:
        return # Error message handled by get_vault_path_from_config

    click.echo("Gathering note statistics...")
    note_stats = get_note_stats(vault_path)
    if not note_stats:
        click.echo("No markdown notes found or processed.")
        return

    df = pd.DataFrame(note_stats)
    # ... (rest of the summary function using df) ...
    click.echo(f"\nTotal Notes: {len(df)}")
    # ... (more summary stats) ...

@analytics.command()
@click.option('--output', type=click.Path(dir_okay=False, writable=True), help='Save plot to file instead of showing.')
@click.option('--days', type=int, default=30, help='Number of past days to plot.')
def activity(output, days):
    """Plot note activity (modifications over time)."""
    # Import pandas and plotting libraries only when activity is called
    try:
        import pandas as pd
    except ImportError:
        click.echo("Error: pandas library is required for activity. Install with 'pip install pandas'", err=True)
        return

    # Decide which plotting library to use
    use_plotext = True
    plt = None
    plt_mpl = None
    mdates = None

    if output: # If saving to file, prefer matplotlib
        try:
            import matplotlib.pyplot as plt_mpl
            import matplotlib.dates as mdates
            use_plotext = False
        except ImportError:
            click.echo("Warning: matplotlib is required to save plots. Install with 'pip install matplotlib'. Falling back to terminal plot.", err=True)
            # Fall through to try plotext for terminal display
    
    if use_plotext:
        try:
            import plotext as plt
        except ImportError:
            click.echo("Error: plotext library is required for terminal plots. Install with 'pip install plotext'", err=True)
            # If matplotlib also failed or wasn't requested, we can't plot
            if not output: # Only error out if terminal plot was the goal
                 return

    vault_path = get_vault_path_from_config()
    if not vault_path:
        return

    click.echo("Gathering note statistics for activity plot...")
    note_stats = get_note_stats(vault_path)
    if not note_stats:
        click.echo("No markdown notes found or processed.")
        return

    df = pd.DataFrame(note_stats)
    df['modified_date'] = pd.to_datetime(df['modified_time']).dt.date
    # ... (calculate activity_counts) ...
    activity_counts = df.groupby('modified_date').size().resample('D').sum().fillna(0)
    # Filter for the last 'days'
    end_date = datetime.now().date()
    start_date = end_date - pd.Timedelta(days=days - 1)
    activity_counts = activity_counts[activity_counts.index >= pd.to_datetime(start_date)]


    if use_plotext and plt:
        click.echo(f"\n--- Note Modifications (Last {days} Days) ---")
        dates = [d.strftime("%Y-%m-%d") for d in activity_counts.index]
        counts = activity_counts.values
        
        plt.clear_figure()
        plt.date_form('Y-m-d')
        plt.plot_date(dates, counts)
        plt.title("Note Modification Activity")
        plt.xlabel("Date")
        plt.ylabel("Notes Modified")
        plt.show()

    elif not use_plotext and plt_mpl and mdates:
        fig, ax = plt_mpl.subplots(figsize=(12, 6))
        ax.bar(activity_counts.index, activity_counts.values, width=0.8)
        ax.set_title(f"Note Modification Activity (Last {days} Days)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Notes Modified")
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        fig.autofmt_xdate() # Rotate date labels
        plt_mpl.grid(axis='y', linestyle='--')
        
        try:
            plt_mpl.savefig(output)
            click.echo(f"Activity plot saved to: {output}")
        except Exception as e:
            click.echo(f"Error saving plot to {output}: {e}", err=True)
        plt_mpl.close(fig) # Close the plot figure

    else:
         # This case should ideally not be reached if checks above are correct
         click.echo("Error: No suitable plotting library found or an error occurred.", err=True)


@analytics.command()
@click.option('--output', type=click.Path(dir_okay=False, writable=True),
              default="vault_report.ipynb", help='Output path for the Jupyter Notebook.')
def notebook(output):
    """Generate a Jupyter Notebook report."""
    # Import notebook/plotting libraries only when notebook is called
    try:
        import pandas as pd
        import nbformat as nbf
        import matplotlib.pyplot as plt_mpl
        import matplotlib.dates as mdates
    except ImportError:
        click.echo("Error: pandas, nbformat, and matplotlib are required for notebook generation.", err=True)
        click.echo("Install with: pip install pandas nbformat matplotlib", err=True)
        return

    vault_path = get_vault_path_from_config()
    if not vault_path:
        return

    click.echo("Generating Jupyter Notebook report...")
    note_stats = get_note_stats(vault_path)
    if not note_stats:
        click.echo("No notes found to generate report.", err=True)
        return

    df = pd.DataFrame(note_stats)
    df['modified_date'] = pd.to_datetime(df['modified_time']).dt.date

    nb = nbf.v4.new_notebook()
    
    # --- Notebook Cells ---
    nb['cells'].append(nbf.v4.new_markdown_cell("# Obsidian Vault Analytics Report"))
    nb['cells'].append(nbf.v4.new_markdown_cell(f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
    
    # Imports cell
    nb['cells'].append(nbf.v4.new_code_cell(
        "import pandas as pd\n"
        "import matplotlib.pyplot as plt\n"
        "import matplotlib.dates as mdates\n"
        "# Load data (assuming df is pre-loaded or loaded from a file here)\n"
        "# For this example, we'll recreate the dataframe structure\n"
        f"data = {df.to_dict(orient='records')}\n" # Embed data directly for simplicity
        "df = pd.DataFrame(data)\n"
        "df['modified_time'] = pd.to_datetime(df['modified_time'])\n"
        "df['modified_date'] = df['modified_time'].dt.date"
    ))

    # Summary Stats Cell
    nb['cells'].append(nbf.v4.new_markdown_cell("## Vault Summary"))
    nb['cells'].append(nbf.v4.new_code_cell(
        "total_notes = len(df)\n"
        "total_words = df['word_count'].sum()\n"
        "avg_words = df['word_count'].mean()\n"
        "print(f'Total Notes: {total_notes}')\n"
        "print(f'Total Words: {total_words}')\n"
        "print(f'Average Words per Note: {avg_words:.2f}')"
    ))

    # Activity Plot Cell
    nb['cells'].append(nbf.v4.new_markdown_cell("## Note Activity (Last 30 Days)"))
    nb['cells'].append(nbf.v4.new_code_cell(
        "activity_counts = df.groupby('modified_date').size().resample('D').sum().fillna(0)\n"
        "end_date = pd.to_datetime('today').date()\n"
        "start_date = end_date - pd.Timedelta(days=29)\n"
        "activity_counts = activity_counts[activity_counts.index >= pd.to_datetime(start_date)]\n\n"
        "fig, ax = plt.subplots(figsize=(12, 6))\n"
        "ax.bar(activity_counts.index, activity_counts.values, width=0.8)\n"
        "ax.set_title('Note Modification Activity (Last 30 Days)')\n"
        "ax.set_xlabel('Date')\n"
        "ax.set_ylabel('Notes Modified')\n"
        "ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))\n"
        "ax.xaxis.set_major_locator(mdates.AutoDateLocator())\n"
        "fig.autofmt_xdate()\n"
        "plt.grid(axis='y', linestyle='--')\n"
        "plt.show()"
    ))
    
    # Word Count Distribution Cell
    nb['cells'].append(nbf.v4.new_markdown_cell("## Word Count Distribution"))
    nb['cells'].append(nbf.v4.new_code_cell(
        "fig, ax = plt.subplots(figsize=(10, 6))\n"
        "ax.hist(df['word_count'], bins=30, edgecolor='black')\n"
        "ax.set_title('Distribution of Word Counts per Note')\n"
        "ax.set_xlabel('Word Count')\n"
        "ax.set_ylabel('Number of Notes')\n"
        "plt.grid(axis='y', linestyle='--')\n"
        "plt.show()"
    ))

    # --- Save Notebook ---
    try:
        with open(output, 'w') as f:
            nbf.write(nb, f)
        click.echo(f"Notebook report saved to: {output}")
    except Exception as e:
        click.echo(f"Error writing notebook file {output}: {e}", err=True)

# Potentially add git history analysis here, importing 'git' inside the function
# @analytics.command()
# def history():
#     """Analyze vault history using Git (if available)."""
#     try:
#         import git
#     except ImportError:
#         click.echo("Error: GitPython library is required for history analysis.", err=True)
#         click.echo("Install with: pip install GitPython", err=True)
#         return
#     # ... rest of git analysis logic ...
