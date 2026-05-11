from __future__ import annotations

import os
import sys
import csv
import re
import pandas as pd
import lizard
import requests
import subprocess
import signal
import time
from pathlib import Path
from pydriller import Repository
from datetime import datetime
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.analysis.code_metrics import CodeMetricsAnalyzer
from manifest_analysis.datasets.registry import get_manifest_dataset
from manifest_analysis.utils.paths import DERIVED_ADOPTION_DIR, ORIGINAL_DATASETS_DIR
from manifest_analysis.utils.token_manager import token_manager

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Processing timed out")

# For analyzing adoption commits for review comments

# Configuration
DATASETS_DIR = ORIGINAL_DATASETS_DIR
REPOS_DIR = PROJECT_ROOT / "archive" / "repositories"
OUTPUT_DIR = DERIVED_ADOPTION_DIR

categories = ["agents"]

def is_programmatic_code(filename):
    return CodeMetricsAnalyzer.is_programmatic_code(filename)

def get_codex_prs(repo_owner, repo_name):
    """
    Fetches PRs merged from 'codex' related branches to identify Codex commits.
    Returns a set of merge commit SHAs.
    """
    query = f"is:pr repo:{repo_owner}/{repo_name} head:codex merged:true"
    url = f"https://api.github.com/search/issues?q={query}"
    
    codex_shas = set()
    
    try:
        # Search for PRs
        response = requests.get(url, headers=token_manager.get_headers())
        if response.status_code == 200:
            data = response.json()
            for item in data.get("items", []):
                # For each PR, we need the merge commit SHA.
                # The search API doesn't give the merge commit SHA directly in the item list usually.
                # We need to fetch the PR details.
                pr_url = item.get("pull_request", {}).get("url")
                if pr_url:
                    pr_resp = requests.get(pr_url, headers=token_manager.get_headers())
                    if pr_resp.status_code == 200:
                        pr_data = pr_resp.json()
                        merge_commit_sha = pr_data.get("merge_commit_sha")
                        if merge_commit_sha:
                            codex_shas.add(merge_commit_sha)
    except Exception as e:
        print(f"Error fetching Codex PRs for {repo_owner}/{repo_name}: {e}")
        
    return codex_shas

def calculate_metrics(code, filename):
    return CodeMetricsAnalyzer.calculate_metrics(code, filename)

def detect_ai_author(commit, codex_shas):
    """
    Detects if a commit is authored/co-authored by AI.
    Returns (is_ai, tool_name).
    """
    is_ai = False
    tool = []

    msg = commit.msg.lower() if commit.msg else ""
    author_name = commit.author.name.lower() if commit.author.name else ""
    committer_name = commit.committer.name.lower() if commit.committer.name else ""
    author_email = commit.author.email.lower() if commit.author.email else ""

    # 1. Claude
    if "co-authored-by" in msg and "claude" in msg:
        is_ai = True
        tool.append("Claude")
    if "co-authored-by" in msg and "anthropic" in msg:
        is_ai = True
        tool.append("Claude")

    # 2. Copilot
    if "copilot" in author_name or "copilot" in committer_name:
        is_ai = True
        tool.append("Copilot")
    if "copilot" in author_email: # e.g. copilot@github.com logic if exists
        is_ai = True
        tool.append("Copilot")
    if "co-authored-by" in msg and "copilot" in msg:
        is_ai = True
        tool.append("Copilot")

    # 3. Codex
    # Check pre-fetched SHAs or heuristic in message
    if commit.hash in codex_shas:
        is_ai = True
        tool.append("Codex")
    
    # Fallback Codex heuristic (branch merge)
    if "merge pull request" in msg and "codex" in msg:
        is_ai = True
        tool.append("Codex")
    
    # 4. General AI
    if "co-authored-by" in msg and " ai " in msg: # vague
         # You mentioned "check for co-authored by AI agent for every tool"
         pass

    if not is_ai:
        return False, None
    
    return True, "/".join(set(tool))

def analyze_repo(repo_row, category, output_list):
    owner = repo_row['repository_owner']
    name = repo_row['repository_name']
    adoption_date_str = repo_row.get('first_manifest_commit_date')
    
    if pd.isna(adoption_date_str):
        print(f"Skipping {owner}/{name}: No adoption date")
        return

    try:
        adoption_date = datetime.strptime(str(adoption_date_str).replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        # Try simplified format if Z is missing or different
        try:
             adoption_date = datetime.fromisoformat(str(adoption_date_str).replace('Z', '+00:00'))
        except:
            print(f"Skipping {owner}/{name}: Invalid date format {adoption_date_str}")
            return

    # Determine Repo Path
    local_path = REPOS_DIR / owner / name
    repo_url = repo_row['repository_url']
    path_to_use = str(local_path) if local_path.exists() else repo_url
    
    print(f"Analyzing {owner}/{name} using {path_to_use}...")

    # Fetch Codex PRs (optimization: only if 'codex' is likely or always?)
    # Generating API calls for EVERY repo might be slow. 
    # I'll enable it but catch errors softly.
    codex_shas = set()
    if "agents" in category: # Only relevant for agents? Or all? User mentioned Codex for agents.md specifically.
         codex_shas = get_codex_prs(owner, name)

    # Initialize Stats
    pre_commits_count = 0
    post_commits_count = 0
    ai_pre_commits_count = 0
    ai_post_commits_count = 0

    repo_ai_commits_data = []
    
    # We replaced signal.alarm(600) with a manual time check inside the loop
    # to allow calculate_metrics to use signal.alarm for file-level timeouts
    start_time = time.time()
    TIMEOUT_SECONDS = 600 # 10 minutes

    try:
        for commit in Repository(path_to_use).traverse_commits():
            # Check for repo-level timeout
            if time.time() - start_time > TIMEOUT_SECONDS:
                 raise TimeoutException("Repo analysis exceeded 10 minutes")

            commit_date = commit.committer_date
            
            period = "Pre-Adoption"
            if commit_date > adoption_date:
                period = "Post-Adoption"
                post_commits_count += 1
            else:
                pre_commits_count += 1

            is_ai, tool = detect_ai_author(commit, codex_shas)
            
            if is_ai:
                if period == "Pre-Adoption":
                    ai_pre_commits_count += 1
                else:
                    ai_post_commits_count += 1
                
                # Calculate Metrics for Modified Files
                locs = []
                complexities = []
                
                for mod in commit.modified_files:
                    # Filter binaries/deleted
                    if mod.source_code is None:
                        continue
                    
                    # Only calculate/add if it's a programmatic code file
                    # calculate_metrics now checks is_programmatic_code internally too, but checking here cleans up the logic
                    if is_programmatic_code(mod.filename):
                        l, c = calculate_metrics(mod.source_code, mod.filename)
                        if l > 0: # Only count if it has NLOC
                            locs.append(l)
                            complexities.append(c)

                # Fallback implementation for AI Merge Commits (specifically Codex)
                # If it's a merge commit, pydriller often shows 0 modified files.
                # We want the diff against the first parent to capture the PR's work.
                if is_ai and not locs and commit.merge and hasattr(commit, 'project_path') and commit.project_path:
                   try:
                       if commit.parents:
                           parent = commit.parents[0]
                           cwd = commit.project_path
                           
                           # Get list of changed files
                           cmd = ["git", "diff", "--name-only", parent, commit.hash]
                           result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
                           
                           if result.returncode == 0:
                               files = result.stdout.strip().splitlines()
                               for fname in files:
                                   if is_programmatic_code(fname):
                                       try:
                                           cmd_show = ["git", "show", f"{commit.hash}:{fname}"]
                                           res_show = subprocess.run(cmd_show, cwd=cwd, capture_output=True, text=True, errors='ignore')
                                           if res_show.returncode == 0:
                                                code = res_show.stdout
                                                l, c = calculate_metrics(code, fname)
                                                if l > 0:
                                                    locs.append(l)
                                                    complexities.append(c)
                                       except Exception:
                                           pass
                   except Exception as e:
                       # Start thread or subprocess might be limited, avoiding excessive logging
                       pass
                
                avg_nloc = np.mean(locs) if locs else 0
                median_nloc = np.median(locs) if locs else 0
                avg_complex = np.mean(complexities) if locs else 0
                median_complex = np.median(complexities) if locs else 0
                
                repo_ai_commits_data.append({
                    "repository_owner": owner,
                    "repository_name": name,
                    "commit_sha": commit.hash,
                    "commit_url": f"https://github.com/{owner}/{name}/commit/{commit.hash}", # Construct URL
                    "commit_date": commit_date,
                    "author_name": commit.author.name,
                    "is_ai": True,
                    "ai_tool": tool,
                    "period": period,
                    "avg_complexity": avg_complex,
                    "median_complexity": median_complex,
                    "avg_nloc": avg_nloc,
                    "median_nloc": median_nloc,
                    "files_changed_count": len(locs)
                })

    except TimeoutException:
        print(f"Skipping {owner}/{name}: Timed out after 10 minutes.")
        return
    except Exception as e:
        print(f"Error traversing {owner}/{name}: {e}")
        return
    # Finally block for signal.alarm(0) is no longer needed since we don't use repo-level alarm
    
    # Post-process: Add aggregate ratios to each row
    pre_ratio = (ai_pre_commits_count / pre_commits_count) if pre_commits_count > 0 else 0
    post_ratio = (ai_post_commits_count / post_commits_count) if post_commits_count > 0 else 0

    for row in repo_ai_commits_data:
        row["pre_adoption_ai_ratio"] = pre_ratio
        row["post_adoption_ai_ratio"] = post_ratio
        row["total_commits_pre"] = pre_commits_count
        row["total_commits_post"] = post_commits_count
        output_list.append(row)

def main():
    # Register the signal handler ONCE for the entire execution
    signal.signal(signal.SIGALRM, timeout_handler)

    if not os.path.exists(REPOS_DIR):
        print(f"Warning: {REPOS_DIR} does not exist. Script will clone via pydriller if needed.")

    for cat in categories:
        # Check for test override
        input_csv = get_manifest_dataset(cat).original_path
        if len(sys.argv) > 1 and sys.argv[1] == "--test":
             input_csv = DATASETS_DIR / f"{cat}_dataset_test.csv"
             
        if not input_csv.exists():
            continue
            
        print(f"Processing {cat} dataset...")
        df = pd.read_csv(input_csv)
        
        adoption_commits = []
        output_path = get_manifest_dataset(cat).adoption_commits_path
        
        start_index = 0
        if output_path.exists():
            try:
                # Load existing data to resume
                existing_df = pd.read_csv(output_path)
                if not existing_df.empty:
                    adoption_commits = existing_df.to_dict('records')
                    last_processed = adoption_commits[-1]
                    last_owner = last_processed.get('repository_owner')
                    last_name = last_processed.get('repository_name')
                    
                    # Find where this repo is in the input dataframe
                    # matches will be a boolean series, we want the index of the last True
                    matches = df.index[(df['repository_owner'] == last_owner) & (df['repository_name'] == last_name)].tolist()
                    
                    if matches:
                        # Start from the NEXT repo
                        start_index = matches[-1] + 1
                        print(f"Creating resume point: Skipping first {start_index} repos (Last was {last_owner}/{last_name})")
            except Exception as e:
                print(f"Could not load existing file for resume: {e}")

        # Slice the dataframe to start from start_index
        if start_index >= len(df):
            print(f"All repos in {cat} seem to be processed.")
            continue
            
        df_to_process = df.iloc[start_index:]
        
        total_repos = len(df) # Total original count for progress usage
        
        # Iterate over the subset
        for index, row in df_to_process.iterrows():
            print(f"[{index+1}/{total_repos}] ", end="")
            analyze_repo(row, cat, adoption_commits)
            
            # Save periodically every 100 repos (calculated based on count processed in this run or absolute index?)
            # Let's just save frequently enough
            if (index + 1) % 100 == 0:
                out_df = pd.DataFrame(adoption_commits)
                out_df.to_csv(output_path, index=False)
                print(f"\n[Auto-Save] Saved progress to {output_path} ({len(adoption_commits)} commits)")
            
        # Save Final Result
        out_df = pd.DataFrame(adoption_commits)
        out_df.to_csv(output_path, index=False)
        print(f"Saved {output_path}")

if __name__ == "__main__":
    main()
