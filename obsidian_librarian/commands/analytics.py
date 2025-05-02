import click
import os
import re
from pathlib import Path
from datetime import datetime
import statistics
import pandas as pd  # For data handling, useful for plots/notebook

# Plotting library for terminal
try:
    import plotext as plt
except ImportError:
    plt = None # Handle optional dependency

# For Git history (optional, implement later)
try:
    import git
except ImportError:
    git = None

# For Jupyter Notebook generation (optional, implement later)
try:
    import nbformat as nbf
    import matplotlib.pyplot as plt_mpl
    import matplotlib.dates as mdates # For date formatting on plots
except ImportError:
    nbf = None
    plt_mpl = None
    mdates = None


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

# --- Jupyter Notebook Generation Function (Placeholder for now) ---
def generate_notebook(stats_df: pd.DataFrame, output_path: str):
    """Generates a Jupyter Notebook with analytics."""
    if not nbf or not plt_mpl or not mdates:
        click.echo("Error: Required libraries for notebook generation (nbformat, matplotlib) not found.", err=True)
        click.echo("Please install them: pip install nbformat matplotlib pandas", err=True)
        return

    click.echo(f"Generating Jupyter Notebook at {output_path}...")

    nb = nbf.v4.new_notebook()

    # --- Notebook Cells ---
    imports_code = """
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import json

# Load the data passed into the notebook environment (alternative: load from a file)
# For simplicity in this example, we'll embed the data as a JSON string
# In a real scenario, you might pass a path to a temporary CSV/JSON
stats_data_json = '''{}'''
stats_list = json.loads(stats_data_json)

# Convert to DataFrame and fix types
stats_df = pd.DataFrame(stats_list)
stats_df['modified_time'] = pd.to_datetime(stats_df['modified_time'])
stats_df['word_count'] = pd.to_numeric(stats_df['word_count'], errors='coerce').fillna(-1)

# Filter out entries where word count wasn't available if needed for specific plots
stats_df_wc = stats_df[stats_df['word_count'] != -1].copy()


print(f"Loaded {len(stats_df)} notes.")
stats_df.head()
""".format(stats_df.to_json(orient='records', date_format='iso')) # Embed data

    summary_code = """
print("\\n--- Basic Summary ---")
total_notes = len(stats_df)
# Calculate word stats only if available
if not stats_df_wc.empty:
    total_words = stats_df_wc['word_count'].sum()
    avg_words = stats_df_wc['word_count'].mean()
    median_words = stats_df_wc['word_count'].median()
    print(f"Total Words (where counted): {total_words}")
    print(f"Average Words per Note: {avg_words:.2f}")
    print(f"Median Words per Note: {median_words:.0f}")
else:
    print("Word counts not available in this dataset.")

print(f"Total Notes: {total_notes}")

"""

    length_dist_code = """
print("\\n--- Note Length Distribution ---")
if not stats_df_wc.empty:
    plt.figure(figsize=(12, 6))
    sns.histplot(stats_df_wc['word_count'], bins=30, kde=True)
    plt.title('Distribution of Note Lengths (Word Count)')
    plt.xlabel('Word Count')
    plt.ylabel('Number of Notes')
    plt.grid(axis='y', alpha=0.7)
    plt.show()

    print("\\nTop 5 Longest Notes:")
    print(stats_df_wc.nlargest(5, 'word_count')[['filename', 'word_count']])

    print("\\nTop 5 Shortest Notes:")
    print(stats_df_wc.nsmallest(5, 'word_count')[['filename', 'word_count']])
else:
    print("Word counts not available for distribution plot.")

"""

    activity_code = """
print("\\n--- Recent Activity (Based on Last Modified Date) ---")
stats_df['modified_date'] = stats_df['modified_time'].dt.date

# Notes modified per day
daily_activity = stats_df.groupby('modified_date').size()

plt.figure(figsize=(15, 7))
daily_activity.plot(kind='line', marker='o', linestyle='-')
plt.title('Notes Modified Per Day (Last Modified Date)')
plt.xlabel('Date')
plt.ylabel('Number of Notes Modified')
plt.xticks(rotation=45)
plt.grid(True, which='both', linestyle='--', linewidth=0.5)
plt.tight_layout()
plt.show()

print("\\nLast 10 Modified Notes:")
# Use original df here as word count isn't needed
print(stats_df.nlargest(10, 'modified_time')[['filename', 'modified_time']])
"""
    # --- Add cells to notebook ---
    nb['cells'].append(nbf.v4.new_markdown_cell("# Obsidian Vault Analytics"))
    nb['cells'].append(nbf.v4.new_code_cell(imports_code))
    nb['cells'].append(nbf.v4.new_markdown_cell("## Basic Summary Statistics"))
    nb['cells'].append(nbf.v4.new_code_cell(summary_code))
    nb['cells'].append(nbf.v4.new_markdown_cell("## Note Length Analysis"))
    nb['cells'].append(nbf.v4.new_code_cell(length_dist_code))
    nb['cells'].append(nbf.v4.new_markdown_cell("## Recent Activity Analysis (Based on Last Modified Time)"))
    nb['cells'].append(nbf.v4.new_markdown_cell("Note: This shows the *last* time a note was modified, not necessarily when content was added. For more detailed history (like words added per day), Git history analysis would be needed."))
    nb['cells'].append(nbf.v4.new_code_cell(activity_code))

    # --- Write notebook file ---
    try:
        with open(output_path, 'w') as f:
            nbf.write(nb, f)
        click.echo(f"Successfully generated notebook: {output_path}")
    except Exception as e:
        click.echo(f"Error writing notebook file: {e}", err=True)


# --- Main Analytics Command ---
@click.command(name="analytics")
@click.option('--use-git-history', is_flag=True, help='Analyze Git history for detailed changes (requires GitPython and repo).')
@click.option('-d', '--notebook', is_flag=True, help='Generate a Jupyter notebook with detailed visualizations on the Desktop.')
@click.option('--force-scan', is_flag=True, help='Force reading all files instead of using the index (slower).')
def run_analytics(use_git_history=False, notebook=False, force_scan=False):
    """
    Analyzes the Obsidian vault and displays statistics.

    Provides insights into note count, word counts, modification activity,
    and note length distribution. Optionally generates a Jupyter notebook
    for richer visualizations. Uses the index by default for speed.
    """
    # --- Perform checks at the beginning ---
    config = get_config()
    vault_path = get_vault_path_from_config()
    db_path = vault_state.DB_PATH

    if not vault_path:
        click.echo(click.style("Error: Vault path not configured. Run 'olib config setup' first.", fg="red"), err=True)
        import sys
        sys.exit(1)

    # Check index existence (unless force_scan is True)
    if not force_scan and not db_path.exists():
        click.echo(click.style("Error: The vault index database hasn't been created yet.", fg="red"), err=True)
        click.echo("Please run " + click.style("'olib update-index'", fg="cyan") + " or use --force-scan.")
        import sys
        sys.exit(1)

    # Check schedule prompt (only if not forcing scan, as index is relevant)
    if not force_scan and not config.get("schedule_prompted"):
        click.echo(click.style("Tip:", fg="yellow") + " To keep analytics accurate, it's recommended to schedule hourly index updates.")
        click.echo("Run " + click.style("'olib schedule-update'", fg="cyan") + " for instructions.")
        config["schedule_prompted"] = True
        save_config(config)
        click.echo("---") # Separator
    # --- End of checks ---

    click.echo(f"Analyzing vault: {vault_path}")

    # --- Data Gathering ---
    note_stats = []
    if force_scan:
        click.echo("Gathering note statistics by scanning files (may be slow)...")
        note_stats = get_note_stats(str(vault_path))
    else:
        click.echo("Gathering note statistics from index...")
        # Attempt to get stats from index
        # Note: This currently lacks word count. We might need to enhance
        # get_note_stats_from_index or add word count to the DB later.
        # For now, let's fall back to full scan if index data is insufficient
        # for requested analysis (e.g., word count needed).
        # A simple approach for now: Use index for basic counts/dates,
        # but if word count stats are needed, use get_note_stats.
        # Let's use get_note_stats for now to ensure word counts work.
        # TODO: Optimize later by adding word count to index or selectively scanning.
        click.echo("Note: Currently performing full scan for word counts. Index optimization pending.")
        note_stats = get_note_stats(str(vault_path))
        # note_stats = get_note_stats_from_index(db_path) # Use this when index is sufficient

    if not note_stats:
        click.echo("No markdown notes found or processed.")
        return

    # Convert to DataFrame for easier analysis
    stats_df = pd.DataFrame(note_stats)
    # Ensure correct types (especially if coming from mixed sources later)
    stats_df['modified_time'] = pd.to_datetime(stats_df['modified_time'])
    stats_df['word_count'] = pd.to_numeric(stats_df['word_count'], errors='coerce').fillna(0) # Coerce errors, fill NaN with 0

    # --- Basic Calculations ---
    total_notes = len(stats_df)
    total_words = stats_df['word_count'].sum()
    avg_words = stats_df['word_count'].mean() if total_notes > 0 else 0
    median_words = stats_df['word_count'].median() if total_notes > 0 else 0
    min_words = stats_df['word_count'].min() if total_notes > 0 else 0
    max_words = stats_df['word_count'].max() if total_notes > 0 else 0

    # --- Terminal Output ---
    click.echo("\n--- Basic Statistics ---")
    click.echo(f"Total Notes:         {total_notes}")
    click.echo(f"Total Words:         {total_words}")
    click.echo(f"Average Words/Note:  {avg_words:.2f}")
    click.echo(f"Median Words/Note:   {median_words:.0f}")
    click.echo(f"Min Words/Note:      {min_words}")
    click.echo(f"Max Words/Note:      {max_words}")

    # Note Length Distribution Plot (Terminal)
    if plt and total_notes > 0 and stats_df['word_count'].nunique() > 1: # Check if plotext exists and data is plottable
        click.echo("\n--- Note Length Distribution (Word Count) ---")
        word_counts = stats_df['word_count'].tolist()
        plt.clf()
        plt.hist(word_counts, bins=20)
        plt.title("Note Length Distribution")
        plt.xlabel("Word Count")
        plt.ylabel("Frequency")
        plt.show()
    elif not plt:
        click.echo("\nNote Length Distribution: Install 'plotext' for terminal plot.")
    elif not (total_notes > 0 and stats_df['word_count'].nunique() > 1):
         click.echo("\nNote Length Distribution: Not enough data or variation to plot.")


    # Recent Activity (Terminal)
    click.echo("\n--- Recent Activity (Last 10 Modified) ---")
    last_modified = stats_df.nlargest(10, 'modified_time')
    for _, row in last_modified.iterrows():
        # Ensure filename is treated as string
        filename_str = str(row.get('filename', 'N/A'))
        click.echo(f"- {filename_str} (Words: {row['word_count']}, Modified: {row['modified_time'].strftime('%Y-%m-%d %H:%M')})")


    # --- Git History Analysis (Placeholder) ---
    if use_git_history:
        click.echo("\n--- Git History Analysis (Placeholder) ---")
        if git:
            click.echo("GitPython found. Implement Git analysis here.")
            # Example: Check if vault_path is a repo
            # try:
            #     repo = git.Repo(vault_path)
            #     click.echo(f"Vault is a Git repository. Last commit: {repo.head.commit.summary} by {repo.head.commit.author} on {repo.head.commit.committed_datetime}")
            #     # TODO: Add logic to parse commits and diffs for words added/day
            # except git.InvalidGitRepositoryError:
            #     click.echo("Vault path is not a Git repository.")
            # except Exception as e:
            #     click.echo(f"Error accessing Git repository: {e}", err=True)
        else:
            click.echo("GitPython not installed. Cannot perform Git history analysis.")
            click.echo("Install it using: pip install GitPython")


    # --- Jupyter Notebook Generation ---
    if notebook:
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        if not os.path.isdir(desktop_path):
             click.echo(f"Warning: Desktop path not found at {desktop_path}. Saving notebook to current directory.", err=True)
             desktop_path = "." # Fallback to current directory
        notebook_filename = f"obsidian_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ipynb"
        output_path = os.path.join(desktop_path, notebook_filename)
        generate_notebook(stats_df, output_path)


    click.echo("\nAnalysis complete.")
