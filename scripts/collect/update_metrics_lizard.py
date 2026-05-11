from __future__ import annotations

import os
import pandas as pd
import lizard
import numpy as np
import requests
import sys
from pathlib import Path
from pydriller import Repository

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.analysis.code_metrics import CodeMetricsAnalyzer
from manifest_analysis.utils.paths import DERIVED_ADOPTION_DIR, DERIVED_BACKUPS_DIR
from manifest_analysis.utils.token_manager import token_manager

DATASETS_DIR = DERIVED_BACKUPS_DIR
OUTPUT_DIR = DERIVED_ADOPTION_DIR
CATEGORIES = ["agents", "claude", "copilot-instructions"]

def is_programmatic_code(filename):
    return CodeMetricsAnalyzer.is_programmatic_code(filename)

def calculate_lizard_metrics(code, filename):
    return CodeMetricsAnalyzer.calculate_metrics(code, filename)

def process_commit_via_api(repo_owner, repo_name, commit_sha, current_idx, total_commits):
    """
    Fetches commit details via GitHub API and calculates metrics using Lizard.
    """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits/{commit_sha}"
    
    try:
        response = requests.get(url, headers=token_manager.get_headers())
        if response.status_code != 200:
            # print(f"API Error {response.status_code} for {repo_owner}/{repo_name}/{commit_sha}")
            return None
            
        data = response.json()
        files = data.get('files', [])
        total_files = len(files)
        
        nlocs = []
        complexities = []
        
        for i, file in enumerate(files):
            print(f"Processing commit {commit_sha[:7]} [{current_idx}/{total_commits}]: file {i+1}/{total_files} (Commit Progress: {current_idx/total_commits*100:.1f}%)", end='\r')
            
            if file.get('status') == 'removed':
                continue
                
            raw_url = file.get('raw_url')
            if not raw_url:
                continue
                
            # Fetch content
            # Try/Except for content fetch
            try:
                # Use headers? Raw URLs are public but token helps rate limit if checking API
                # But raw.githubusercontent.com usually doesn't need auth for public repos
                # Using token can sometimes cause 404 if scope issues, but generally safe to try without first?
                # Actually, file['raw_url'] often has tokens or is public.
                # Let's try regular get.
                file_resp = requests.get(raw_url)
                if file_resp.status_code == 200:
                    content = file_resp.text
                    nloc, ccn = calculate_lizard_metrics(content, file.get('filename', 'test.txt'))
                    
                    if nloc > 0 or ccn > 0:
                        nlocs.append(nloc)
                        complexities.append(ccn)
            except:
                pass
            

        if not nlocs:
            return None
        
        

        return {
            'avg_complexity': np.mean(complexities),
            'median_complexity': np.median(complexities),
            'avg_loc': np.mean(nlocs),
            'median_loc': np.median(nlocs),
            'files_changed_count': len(nlocs)
        }

    except Exception as e:
        print(f"Error processing commit {commit_sha}: {e}")
        return None

def process_category(category):
    input_file = DATASETS_DIR / f"{category}_adoption_commits_lizard.csv"
    if "--test" in sys.argv:
        input_file = DATASETS_DIR / f"{category}_adoption_commits_test.csv"
        
    if not input_file.exists():
        print(f"Skipping {category}: File not found.")
        return

    print(f"Processing {category} ({input_file})...")
    df = pd.read_csv(input_file)
    
    target_tool = ""
    output_filename = ""
    
    if category == "agents":
        target_tool = "Codex"
        output_filename = "agents_only_adoption_dataset.csv"
    elif category == "copilot-instructions":
        target_tool = "Copilot"
        output_filename = "copilot_only_adoption_dataset.csv"
    elif category == "claude":
        target_tool = "Claude"
        output_filename = "claude_only_adoption_dataset.csv"
        
    if target_tool:
        # Filter: ai_tool contains the target tool (case-insensitive just in case, though usually capitalized)
        # Handle NaN ai_tool
        print(f"Filtering {category} for tool '{target_tool}'...")
        df = df[df['ai_tool'].astype(str).str.contains(target_tool, case=False, na=False)].copy()
        df.reset_index(drop=True, inplace=True)
        print(f"Filtered dataset has {len(df)} rows.")

        output_path = OUTPUT_DIR / output_filename
        df.to_csv(output_path, index=False)
        print(f"Saved filtered dataset (before metrics) to {output_path}.")
        
    # Iterate rows
    total_commits = len(df)
    processed = 0
    updated_count = 0
    
    # print(f"Total commits to process: {total_commits}")
    
    # for idx, row in df.iterrows():
    #     processed += 1
    #     pct = (processed / total_commits) * 100
    #     # Print is now handled inside metrics function for smoother line updates, 
    #     # but we can keep a milestone print here if needed or relying on the file-level one.
    #     # process_commit_via_api uses \r so it might be overwritten by this print if we keep it.
    #     # Let's remove the milestone print here to avoid conflict with the \r status bar.
            
    #     metrics = process_commit_via_api(row['repository_owner'], row['repository_name'], row['commit_sha'], processed, total_commits)
        
    #     if metrics:
    #         updated_count += 1
    #         df.at[idx, 'avg_complexity'] = metrics['avg_complexity']
    #         df.at[idx, 'median_complexity'] = metrics['median_complexity']
    #         df.at[idx, 'avg_loc'] = metrics['avg_loc']
    #         df.at[idx, 'median_loc'] = metrics['median_loc']
            
    # print(f"Updated {updated_count} commits.")
    
    # Save Task 1 result
    if output_filename:
        output_path = OUTPUT_DIR / output_filename
        df.to_csv(output_path, index=False)
        print(f"Saved filtered and updated metrics to {output_path}.")
    else:
        # If no filter matches, we might just save back to original or skip saving
        # But based on categories we should always have a target
        pass


def main():
    # Allow filtering by category via args for testing
    cats_to_run = CATEGORIES
    if len(sys.argv) > 1:
        cats_to_run = [c for c in CATEGORIES if c in sys.argv]

    for cat in cats_to_run:
        process_category(cat)

if __name__ == "__main__":
    main()
