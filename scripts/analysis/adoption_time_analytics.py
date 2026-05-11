from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import get_manifest_dataset, iter_manifest_datasets

def analyze_category(category):
    file_path = get_manifest_dataset(category).adoption_commits_path
    
    if not file_path.exists():
        print(f"Dataset for {category} not found at {file_path}")
        return

    print(f"\n{'='*20} ANALYZING: {category.upper()} {'='*20}")
    
    df = pd.read_csv(file_path)
    if df.empty:
        print("Dataset is empty.")
        return

    # ---------------------------------------------------------
    # 1 & 2. REPO LEVEL ANALYTICS (Ratios)
    # ---------------------------------------------------------
    # The dataset has one row per commit, but ratio info is repeated per repo.
    # We need to extract unique repo level data.
    repo_cols = ['repository_owner', 'repository_name', 
                 'pre_adoption_ai_ratio', 'post_adoption_ai_ratio', 
                 'total_commits_pre', 'total_commits_post']
    
    # Drop duplicates to get one row per repository
    df_repos = df[repo_cols].drop_duplicates()
    
    # Filter: Exclude repos with 0 commits after manifest introduction
    # (Adoption rate is undefined or not meaningful if there's no history)
    df_repos_active = df_repos[df_repos['total_commits_post'] > 0]
    
    total_repos = len(df_repos_active)
    if total_repos == 0:
        print("No repositories found with post-adoption commits.")
    else:
        # Metric 1: Percentage of repos with Post > Pre
        increased_adoption = df_repos_active[
            df_repos_active['post_adoption_ai_ratio'] > df_repos_active['pre_adoption_ai_ratio']
        ]
        pct_increase = (len(increased_adoption) / total_repos) * 100
        
        # Metric 2: Averages/Medians of rates
        avg_pre_rate = df_repos_active['pre_adoption_ai_ratio'].mean()
        med_pre_rate = df_repos_active['pre_adoption_ai_ratio'].median()
        
        avg_post_rate = df_repos_active['post_adoption_ai_ratio'].mean()
        med_post_rate = df_repos_active['post_adoption_ai_ratio'].median()

        print("--- Adoption Rates (Repo Level) ---")
        print(f"Total Active Repos Analyzed: {total_repos}")
        print(f"Repos with Increased AI Adoption: {pct_increase:.2f}%")
        print(f"Pre-Adoption Rate:  Mean={avg_pre_rate:.4f}, Median={med_pre_rate:.4f}")
        print(f"Post-Adoption Rate: Mean={avg_post_rate:.4f}, Median={med_post_rate:.4f}")

    # ---------------------------------------------------------
    # 3. COMMIT LEVEL ANALYTICS (Pre vs Post Complexity/LOC)
    # ---------------------------------------------------------
    # We analyze the commit rows directly here.
    # 'avg_complexity' and 'avg_loc' are per-commit metrics calculated in previous step.
    
    print("\n--- Code Quality Metrics (Commit Level: Pre vs Post) ---")
    
    stats = df.groupby('period')[['avg_complexity', 'avg_loc']].agg(['mean', 'median'])
    
    # Format output
    for period in ['Pre-Adoption', 'Post-Adoption']:
        if period in stats.index:
            row = stats.loc[period]
            print(f"{period}:")
            print(f"  Complexity: Mean={row['avg_complexity']['mean']:.2f}, Median={row['avg_complexity']['median']:.2f}")
            print(f"  LOC:        Mean={row['avg_loc']['mean']:.2f}, Median={row['avg_loc']['median']:.2f}")
        else:
            print(f"{period}: No data")

    # ---------------------------------------------------------
    # 4. TOOL ANALYTICS
    # ---------------------------------------------------------
    print("\n--- AI Tool Performance ---")
    
    # Some commits might list multiple tools "Copilot/Claude". We treat them as distinct groups for now.
    tool_stats = df.groupby('ai_tool')[['avg_complexity', 'avg_loc']].mean()
    
    if not tool_stats.empty:
        # Sort by Complexity
        print("Average Metrics by Tool:")
        print(tool_stats.sort_values(by='avg_complexity', ascending=False))
        
        highest_compl_tool = tool_stats['avg_complexity'].idxmax()
        highest_compl_val = tool_stats['avg_complexity'].max()
        
        highest_loc_tool = tool_stats['avg_loc'].idxmax()
        highest_loc_val = tool_stats['avg_loc'].max()
        
        print(f"\nHighest Avg Complexity: {highest_compl_tool} ({highest_compl_val:.2f})")
        print(f"Highest Avg LOC:        {highest_loc_tool} ({highest_loc_val:.2f})")
    else:
        print("No tool data available.")

def main():
    for dataset in iter_manifest_datasets():
        analyze_category(dataset.key)

if __name__ == "__main__":
    main()
