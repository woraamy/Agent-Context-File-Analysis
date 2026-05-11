from __future__ import annotations

import os
import sys
import pandas as pd
import lizard
import requests
import time
import base64
import numpy as np
import signal
from pathlib import Path

"""
Recalculate cyclomatic complexity and NLOC for Codex commits
"""

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.analysis.code_metrics import CodeMetricsAnalyzer
from manifest_analysis.datasets.registry import get_manifest_dataset
from manifest_analysis.utils.token_manager import fetch_with_token_rotation

# Configuration
INPUT_FILE = get_manifest_dataset("agents").tool_only_adoption_path
OUTPUT_FILE = INPUT_FILE.with_name("agents_only_adoption_dataset_recalculated.csv")

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Processing timed out")

def is_programmatic_code(filename):
    return CodeMetricsAnalyzer.is_programmatic_code(filename)

def calculate_metrics(code, filename):
    return CodeMetricsAnalyzer.calculate_metrics(code, filename)

def fetch_file_content(owner, repo, file_path, sha):
    """
    Fetches file content from GitHub API.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={sha}"
    
    try:
        response = fetch_with_token_rotation(url)
        if response and response.status_code == 200:
            data = response.json()
            if 'content' in data:
                return base64.b64decode(data['content']).decode('utf-8', errors='ignore')
        elif response and response.status_code == 404:
            # File might be deleted or renamed, or commit behaves weirdly
            return None
    except Exception as e:
        print(f"  Error fetching {file_path}: {e}")
    return None

def process_commit(row):
    owner = row['repository_owner']
    repo = row['repository_name']
    sha = row['commit_sha']
    
    print(f"Processing {owner}/{repo} - {sha[:7]}...")
    
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
    
    try:
        response = fetch_with_token_rotation(url)
        if not response or response.status_code != 200:
            status = response.status_code if response else "No Response"
            print(f"  Failed to get commit details: {status}")
            return None
            
        data = response.json()
        files = data.get('files', [])
        
        locs = []
        complexities = []
        
        for file in files:
            filename = file.get('filename')
            status = file.get('status') # modified, added, removed
            
            if status == 'removed':
                continue
                
            if is_programmatic_code(filename):
                # Try to get the content
                # 'raw_url' is often available but might valid token or be public
                # We can try fetching content via API
                code = fetch_file_content(owner, repo, filename, sha)
                
                if code:
                    l, c = calculate_metrics(code, filename)
                    if l > 0:
                        locs.append(l)
                        complexities.append(c)
                        # print(f"    {filename}: NLOC={l}, Comp={c}")
        
        avg_nloc = np.mean(locs) if locs else 0
        median_nloc = np.median(locs) if locs else 0
        avg_complex = np.mean(complexities) if locs else 0
        median_complex = np.median(complexities) if locs else 0
        file_count = len(locs)
        
        # Update row
        row['avg_complexity'] = avg_complex
        row['median_complexity'] = median_complex
        row['avg_nloc'] = avg_nloc
        # Use a flexible key check for avg_loc vs avg_nloc as CSV headers might vary
        row['avg_loc'] = avg_nloc 
        row['median_loc'] = median_nloc # assuming 'median_loc' or 'median_nloc'
        row['files_changed_count'] = file_count
        
        return row
        
    except Exception as e:
        print(f"  Error processing commit: {e}")
        return None

def main():
    global INPUT_FILE
    signal.signal(signal.SIGALRM, timeout_handler)
    
    if not INPUT_FILE.exists():
        print(f"File not found: {INPUT_FILE}")
        # Try finding the file the user might have meant
        alt_file = get_manifest_dataset("agents").adoption_commits_path
        if alt_file.exists():
             print(f"Found {alt_file}, using that instead.")
             INPUT_FILE = alt_file
        else:
             return

    print(f"Reading {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)
    
    # Process rows
    updated_rows = []
    total = len(df)
    
    for index, row in df.iterrows():
        
        # Optimization: Only process if it is a Codex commit with missing metrics
        # to avoid hitting API rate limits for 22k commits
        ai_tool = str(row.get('ai_tool', '')).lower()
        complexity = float(row.get('avg_complexity', 0))
        nloc = float(row.get('avg_nloc', 0) if 'avg_nloc' in row else row.get('avg_loc', 0))
        
        # Check if it is Codex and has no metrics
        is_codex = 'codex' in ai_tool
        missing_metrics = (complexity == 0 and nloc == 0)
        
        if is_codex and missing_metrics:
            print(f"[{index+1}/{total}] Recalculating Codex commit... ", end="")
            processed_row = process_commit(row)
            if processed_row is not None:
                updated_rows.append(processed_row)
            else:
                updated_rows.append(row)
        else:
            updated_rows.append(row)
            
        # Periodic save
        if (index + 1) % 100 == 0:
             pd.DataFrame(updated_rows).to_csv(OUTPUT_FILE, index=False)
             print(f"  [Saved progress to {OUTPUT_FILE}]")

             
    # Final save
    pd.DataFrame(updated_rows).to_csv(OUTPUT_FILE, index=False)
    print(f"Done! Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
