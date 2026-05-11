"""Retry static-content fetches by probing multiple likely branch names."""

from __future__ import annotations

import sys
import csv
import time
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import iter_manifest_datasets
from manifest_analysis.utils.token_manager import token_manager


def get_repo_default_branch(owner, repo):
    """
    Get the default branch name for a repository.
    
    Args:
        owner: Repository owner
        repo: Repository name
    
    Returns:
        str: Default branch name or None if failed
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    
    try:
        headers = token_manager.get_headers()
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            default_branch = data.get('default_branch')
            print(f"  ℹ️  Default branch for {owner}/{repo}: {default_branch}")
            return default_branch
        else:
            print(f"  ⚠️  Failed to get repo info: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"  ⚠️  Error getting repo info: {e}")
        return None


def get_file_content_with_branch_detection(owner, repo, file_path, original_branch):
    """
    Retrieve file content by trying multiple branch names.
    
    Args:
        owner: Repository owner
        repo: Repository name
        file_path: Path to the file
        original_branch: The branch name from the dataset
    
    Returns:
        tuple: (content, commit_sha, actual_branch) or (None, None, None)
    """
    # First, try to get the actual default branch
    actual_default_branch = get_repo_default_branch(owner, repo)
    
    # Build a list of branches to try
    branches_to_try = []
    
    if actual_default_branch:
        branches_to_try.append(actual_default_branch)
    
    # Add the original branch if different
    if original_branch not in branches_to_try:
        branches_to_try.append(original_branch)
    
    # Add common branch names
    common_branches = ['main', 'master', 'develop', 'development', 'dev']
    for branch in common_branches:
        if branch not in branches_to_try:
            branches_to_try.append(branch)
    
    print(f"  🔍 Trying branches: {branches_to_try}")
    
    # Try each branch
    for branch in branches_to_try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        params = {'ref': branch}
        
        try:
            headers = token_manager.get_headers()
            response = requests.get(api_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                download_url = data.get('download_url')
                commit_sha = data.get('sha')
                
                if download_url:
                    # Fetch the actual content
                    content_response = requests.get(download_url, headers=headers, timeout=30)
                    
                    if content_response.status_code == 200:
                        content = content_response.text
                        print(f"  ✅ Found on branch '{branch}'! Length: {len(content)} chars")
                        return content, commit_sha, branch
                        
        except Exception as e:
            print(f"  ⚠️  Error trying branch '{branch}': {e}")
            continue
    
    print(f"  ❌ File not found on any branch")
    return None, None, None


def retry_failed_files(input_csv, output_csv, dataset_name):
    """
    Retry collecting files that failed in the initial run.
    
    Args:
        input_csv: Path to the static dataset CSV (with empty static_content)
        output_csv: Path to save the updated dataset
        dataset_name: Name for logging
    """
    print(f"\n{'='*80}")
    print(f"Retrying Failed Files: {dataset_name}")
    print(f"{'='*80}")
    
    # Read the static dataset
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    # Find failed entries (empty static_content)
    failed_rows = [row for row in rows if row.get('static_content', '') == '']
    success_rows = [row for row in rows if row.get('static_content', '') != '']
    
    print(f"📊 Total rows: {len(rows)}")
    print(f"   Already successful: {len(success_rows)}")
    print(f"   Failed to retry: {len(failed_rows)}")
    
    if not failed_rows:
        print("✅ No failed rows to retry!")
        return
    
    # Retry each failed row
    retry_success = 0
    retry_failed = 0
    
    for idx, row in enumerate(failed_rows, 1):
        owner = row['repository_owner']
        repo = row['repository_name']
        file_path = row['file_path']
        original_branch = row['branch']
        
        print(f"\n[{idx}/{len(failed_rows)}] Retrying: {owner}/{repo}/{file_path}")
        print(f"   Original branch: {original_branch}")
        
        content, commit_sha, actual_branch = get_file_content_with_branch_detection(
            owner, repo, file_path, original_branch
        )
        
        if content and commit_sha:
            row['static_content'] = content
            row['file_commit'] = commit_sha
            # Optionally update the branch name
            if actual_branch and actual_branch != original_branch:
                print(f"  📝 Updating branch: {original_branch} → {actual_branch}")
                row['branch'] = actual_branch
            retry_success += 1
        else:
            retry_failed += 1
        
        time.sleep(0.5)  # Be nice to the API
    
    # Merge successful and retried rows
    all_rows = success_rows + failed_rows
    
    # Write the updated CSV
    print(f"\n💾 Writing updated dataset to: {output_csv}")
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    
    print(f"\n✅ Retry complete!")
    print(f"   Retry Success: {retry_success}/{len(failed_rows)}")
    print(f"   Still Failed: {retry_failed}/{len(failed_rows)}")
    print(f"   Total Success: {len(success_rows) + retry_success}/{len(rows)}")


def main():
    """Main execution function."""
    print("="*80)
    print("Retry Failed Files with Branch Detection")
    print("="*80)
    
    for dataset in iter_manifest_datasets():
        retry_failed_files(
            str(dataset.static_path),
            str(dataset.static_path),
            f"{dataset.key} static dataset",
        )
    
    print("\n" + "="*80)
    print("🎉 All retries complete!")
    print("="*80)


if __name__ == "__main__":
    main()
