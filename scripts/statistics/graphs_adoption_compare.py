import sys
from pathlib import Path

try:
    import pandas as pd
    import seaborn as sns
    import matplotlib.pyplot as plt
except Exception as e:
    print('Failed to import plotting dependencies:', e)
    print('\nTo run this plotting script you need a Python environment with pandas, numpy, seaborn, and matplotlib installed.')
    print('If you have a virtualenv in `myenv`, run:')
    print('\n  source myenv/bin/activate')
    print('  pip install -r requirements.txt')
    print('\nOr run the script with the venv python directly:')
    print('\n  ./myenv/bin/python3 scripts/statistics/graphs_adoption_compare.py')
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import get_manifest_dataset
from manifest_analysis.utils.paths import DERIVED_STATISTICS_DIR, FIGURES_DIR

figures_dir = FIGURES_DIR
figures_dir.mkdir(parents=True, exist_ok=True)

# Load the datasets (use dataset dir so script works from any CWD)
agents_df = pd.read_csv(get_manifest_dataset('agents').tool_only_adoption_path)
claude_df = pd.read_csv(get_manifest_dataset('claude').tool_only_adoption_path)
copilot_df = pd.read_csv(get_manifest_dataset('copilot-instructions').tool_only_adoption_path)

# Ensure an `avg_nloc` column exists (fallback to `avg_loc` if present)
for df in (agents_df, claude_df, copilot_df):
    if 'avg_nloc' not in df.columns and 'avg_loc' in df.columns:
        df['avg_nloc'] = df['avg_loc']

# Combine datasets into a single dataframe for comparison
# Adding a source column to identify them if ai_tool names overlap or are generic
combined_df = pd.concat([agents_df, claude_df, copilot_df], ignore_index=True)

# Data Cleaning and Filtering
# 1. Focus only on 'Post-Adoption' period
# 2. Exclude commits where no files were changed (files_changed_count > 0)
filtered_df = combined_df[
    (combined_df['period'] == 'Post-Adoption') & 
    (combined_df['files_changed_count'] > 0)
].copy()

# Set visual style
sns.set_theme(style="whitegrid")

# ----- Handle mixed-tool entries -----
# exploded_df: duplicate rows where `ai_tool` contains multiple tools like 'Claude/Codex'
exploded_df = combined_df.copy()
exploded_df['ai_tool'] = exploded_df['ai_tool'].fillna('')
exploded_df = exploded_df.assign(ai_tool=exploded_df['ai_tool'].str.split(r'[/,]'))
exploded_df = exploded_df.explode('ai_tool')
exploded_df['ai_tool'] = exploded_df['ai_tool'].str.strip()

# clean_df: rows that were single-tool (no '/' or ',') — used for pairwise tests to preserve independence
clean_mask = ~combined_df['ai_tool'].fillna('').astype(str).str.contains(r'[/,]')
clean_df = combined_df[clean_mask].copy()

# For plotting and descriptive summaries we use exploded_df (duplicates show each tool distribution)
plot_df = exploded_df[ (exploded_df['period'] == 'Post-Adoption') & (exploded_df['files_changed_count'] > 0) ].copy()
plot_df = plot_df.reset_index(drop=True)

# Function to remove outliers per-group using IQR rule (k=1.5)
def remove_outliers_iqr(df, col, k=1.5):
    df = df.copy()
    df[col] = pd.to_numeric(df[col], errors='coerce')
    def filter_group(g):
        vals = g[col].dropna()
        if vals.empty:
            return g.iloc[0:0]
        q1 = vals.quantile(0.25)
        q3 = vals.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - k * iqr
        upper = q3 + k * iqr
        return g[(g[col].isna()) | ((g[col] >= lower) & (g[col] <= upper))]
    return df.groupby('ai_tool', group_keys=False).apply(filter_group).reset_index(drop=True)

# Create separate plotting datasets where outliers are removed per metric
plot_df_comp = remove_outliers_iqr(plot_df, 'avg_complexity', k=1.5)
plot_df_nloc = remove_outliers_iqr(plot_df, 'avg_nloc', k=1.5)

# For pairwise tests we will compute two versions:
# 1) excluding mixed rows (clean_df)
# 2) including mixed rows by using exploded duplicates (plot_df) — sensitivity check
test_df_exclude_mixed = clean_df[ (clean_df['period'] == 'Post-Adoption') & (clean_df['files_changed_count'] > 0) ].copy()
test_df_with_mixed = plot_df.copy()
# Figure 1: Average Cyclomatic Complexity per Agent
plt.figure(figsize=(12, 6))
complexity_plot = sns.violinplot(
    data=plot_df_comp,
    x='ai_tool',
    y='avg_complexity',
    inner="quartile",
    order=sorted(plot_df_comp['ai_tool'].dropna().unique())
)
plt.ylabel('Average Cyclomatic Complexity', fontsize=20)
plt.xticks(fontsize=20)
# Ensure y-axis starts at 0 and remove bottom margin
try:
    ymax = complexity_plot.get_ylim()[1]
    complexity_plot.set_ylim(0, ymax)
    complexity_plot.margins(y=0)
except Exception:
    pass
# Increase y-axis tick label size (numbers)
try:
    complexity_plot.tick_params(axis='y', labelsize=20)
except Exception:
    pass
plt.tight_layout()
plt.savefig(str(figures_dir / 'task_difficulty_complexity.pdf'))
plt.show()
# Increase x-axis tick label font size (AI tool names)
try:
    complexity_plot.set_xticklabels(complexity_plot.get_xticklabels(), fontsize=22)
    complexity_plot.set_yticklabels(complexity_plot.get_yticklabels(), fontsize=22)
except Exception:
    pass

# Figure 2: Average Lines of Code (nloc) per Agent
plt.figure(figsize=(12, 6))
nloc_plot = sns.violinplot(
    data=plot_df_nloc,
    x='ai_tool',
    y='avg_nloc',
    inner="quartile",
    order=sorted(plot_df_nloc['ai_tool'].dropna().unique())
)
plt.ylabel('Average nloc (Lines of Code)', fontsize=20)
plt.xticks(fontsize=20)
# Ensure y-axis starts at 0 and remove bottom margin for nloc plot
try:
    ymax = nloc_plot.get_ylim()[1]
    nloc_plot.set_ylim(0, ymax)
    nloc_plot.margins(y=0)
except Exception:
    pass
# Increase y-axis tick label size (numbers)
try:
    nloc_plot.tick_params(axis='y', labelsize=20)
except Exception:
    pass
plt.tight_layout()
plt.savefig(str(figures_dir / 'task_difficulty_nloc.pdf'))
plt.show()
# Increase x-axis tick label font size for nloc plot
try:
    nloc_plot.set_xticklabels(nloc_plot.get_xticklabels(), fontsize=16)
except Exception:
    pass

# Calculate summary statistics for the paper
# Use exploded rows for descriptive summaries so mixed commits contribute to each tool's distribution
stats = plot_df.groupby('ai_tool').agg({
    'avg_complexity': ['mean', 'median', 'std'],
    'avg_nloc': ['mean', 'median', 'std']
}).round(2)

print("Summary Statistics for Post-Adoption Tasks:")
print(stats)

# ----- Pairwise tests: compute both excluding mixed rows and including mixed rows (exploded duplicates)
import csv
from math import isnan

def cliff_delta(a, b):
    a = [x for x in a if x is not None and x == x]
    b = [x for x in b if x is not None and x == x]
    n = len(a)
    m = len(b)
    if n == 0 or m == 0:
        return float('nan')
    gt = lt = 0
    for x in a:
        for y in b:
            if x > y:
                gt += 1
            elif x < y:
                lt += 1
    return (gt - lt) / (n * m)

try:
    from scipy.stats import mannwhitneyu
except Exception:
    mannwhitneyu = None

def pairwise_on_df(df, out_path):
    tools = sorted(df['ai_tool'].dropna().unique())
    rows = []
    for i in range(len(tools)):
        for j in range(i+1, len(tools)):
            a = df[df['ai_tool'] == tools[i]]['avg_complexity'].dropna().astype(float)
            b = df[df['ai_tool'] == tools[j]]['avg_complexity'].dropna().astype(float)
            cd = cliff_delta(a.tolist(), b.tolist())
            if mannwhitneyu is not None and len(a) > 0 and len(b) > 0:
                try:
                    u, p = mannwhitneyu(a, b, alternative='two-sided')
                except TypeError:
                    u, p = mannwhitneyu(a, b)
            else:
                u, p = float('nan'), float('nan')
            rows.append({'group_a': tools[i], 'group_b': tools[j], 'n_a': len(a), 'n_b': len(b), 'mean_a': float(a.mean()) if len(a)>0 else float('nan'), 'mean_b': float(b.mean()) if len(b)>0 else float('nan'), 'median_a': float(a.median()) if len(a)>0 else float('nan'), 'median_b': float(b.median()) if len(b)>0 else float('nan'), 'cliff_delta': cd, 'mannwhitney_u': u, 'p_value': p})
    # save
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['group_a','group_b','n_a','n_b','mean_a','mean_b','median_a','median_b','cliff_delta','mannwhitney_u','p_value'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return rows

stats_dir = DERIVED_STATISTICS_DIR
rows_excl = pairwise_on_df(test_df_exclude_mixed, stats_dir / 'adoption_pairwise_exclude_mixed.csv')
rows_with = pairwise_on_df(test_df_with_mixed, stats_dir / 'adoption_pairwise_with_mixed_exploded.csv')

print('\nPairwise tests (excluded mixed rows):')
for r in rows_excl:
    print(r)

print('\nPairwise tests (with mixed rows exploded duplicates):')
for r in rows_with:
    print(r)
