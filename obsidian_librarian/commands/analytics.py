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


from ..config import get_config
from ..utils.file_operations import get_markdown_files # Assuming you have this utility

def count_words(text: str) -> int:
    """Counts words in a string, simple split by whitespace."""
    return len(text.split())

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
stats_df['word_count'] = pd.to_numeric(stats_df['word_count'])

print(f"Loaded {len(stats_df)} notes.")
stats_df.head()
""".format(stats_df.to_json(orient='records', date_format='iso')) # Embed data

    summary_code = """
print("\\n--- Basic Summary ---")
total_notes = len(stats_df)
total_words = stats_df['word_count'].sum()
avg_words = stats_df['word_count'].mean()
median_words = stats_df['word_count'].median()

print(f"Total Notes: {total_notes}")
print(f"Total Words: {total_words}")
print(f"Average Words per Note: {avg_words:.2f}")
print(f"Median Words per Note: {median_words:.0f}")
"""

    length_dist_code = """
print("\\n--- Note Length Distribution ---")
plt.figure(figsize=(12, 6))
sns.histplot(stats_df['word_count'], bins=30, kde=True)
plt.title('Distribution of Note Lengths (Word Count)')
plt.xlabel('Word Count')
plt.ylabel('Number of Notes')
plt.grid(axis='y', alpha=0.7)
plt.show()

print("\\nTop 5 Longest Notes:")
print(stats_df.nlargest(5, 'word_count')[['filename', 'word_count']])

print("\\nTop 5 Shortest Notes:")
print(stats_df.nsmallest(5, 'word_count')[['filename', 'word_count']])
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
@click.command()
@click.option('--use-git-history', is_flag=True, help='Analyze Git history for detailed changes (requires GitPython and repo).')
@click.option('-d', '--notebook', is_flag=True, help='Generate a Jupyter notebook with detailed visualizations on the Desktop.')
def analytics(use_git_history=False, notebook=False):
    """
    Analyzes the Obsidian vault and displays statistics.

    Provides insights into note count, word counts, modification activity,
    and note length distribution. Optionally generates a Jupyter notebook
    for richer visualizations.
    """
    config = get_config()
    vault_path = config.get('vault_path')

    if not vault_path or not os.path.isdir(vault_path):
        click.echo("Error: Vault path not configured or not found. Run 'olib config setup' first.", err=True)
        return

    click.echo(f"Analyzing vault: {vault_path}")

    # --- Data Gathering ---
    note_stats = get_note_stats(vault_path)
    if not note_stats:
        click.echo("No markdown notes found or processed.")
        return

    # Convert to DataFrame for easier analysis
    stats_df = pd.DataFrame(note_stats)
    stats_df['modified_time'] = pd.to_datetime(stats_df['modified_time']) # Ensure correct type

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
    if plt and total_notes > 0:
        click.echo("\n--- Note Length Distribution (Word Count) ---")
        word_counts = stats_df['word_count'].tolist()
        plt.clf() # Clear previous plots
        plt.hist(word_counts, bins=20) # Adjust bins as needed
        plt.title("Note Length Distribution")
        plt.xlabel("Word Count")
        plt.ylabel("Frequency")
        plt.show()
    elif not plt:
        click.echo("\nNote Length Distribution: Install 'plotext' for terminal plot.")

    # Recent Activity (Terminal)
    click.echo("\n--- Recent Activity (Last 10 Modified) ---")
    last_modified = stats_df.nlargest(10, 'modified_time')
    for _, row in last_modified.iterrows():
        click.echo(f"- {row['filename']} (Words: {row['word_count']}, Modified: {row['modified_time'].strftime('%Y-%m-%d %H:%M')})")

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
