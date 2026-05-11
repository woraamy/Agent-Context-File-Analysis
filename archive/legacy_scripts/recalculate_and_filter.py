import csv
import os
import requests
import lizard
import time
from bs4 import BeautifulSoup
import sys

# Configuration
LIMIT_REQUESTS = 5  # Limit number of network requests for demonstration
REQUEST_COUNT = 0

def get_changed_files(commit_url):
    """
    Parses a GitHub commit page to find changed file paths.
    Returns a list of (filename, raw_url_template).
    """
    global REQUEST_COUNT
    if REQUEST_COUNT >= LIMIT_REQUESTS:
        return []
    
    print(f"Fetching commit page: {commit_url}")
    try:
        response = requests.get(commit_url)
        REQUEST_COUNT += 1
        if response.status_code != 200:
            print(f"Failed to fetch {commit_url}: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        files = []
        
        # This is a heuristic to find file headers in GitHub commit view
        # The structure is dynamic, but usually files are in <div class="file-header">
        # or we find links to the "View file" or "raw".
        
        # GitHub's DOM structure changes, but searching for "files" container works.
        # We need the path.
        # Look for 'cop' (View file) links or similar.
        
        file_divs = soup.find_all('div', class_='file-header')
        for div in file_divs:
            # Try to find the filename
            path_div = div.find('div', class_='file-info')
            if path_div:
                link = path_div.find('a', title=True)
                if link:
                    path = link['title']
                    files.append(path)
            else:
                # Fallback: look for the first <a> in the header that looks like a path
                # This is tricky.
                pass
        
        # Alternative: look for "View file" links which contain the path
        # href="/owner/repo/blob/sha/path/to/file"
        # We can extract path from there.
        view_links = soup.select('a[data-hotkey="v"]') # 'v' is often hotkey for view file? No.
        
        # Let's try to extract from the 'input' elements that often hold the filename in the diff view
        # or the 'data-path' attribute.
        diff_divs = soup.find_all('div', attrs={'data-path': True})
        for div in diff_divs:
            path = div['data-path']
            if path not in files:
                files.append(path)
                
        return files
    except Exception as e:
        print(f"Error parsing {commit_url}: {e}")
        return []

def get_raw_content(owner, repo, sha, file_path):
    global REQUEST_COUNT
    if REQUEST_COUNT >= LIMIT_REQUESTS:
        return None
    
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{sha}/{file_path}"
    try:
        response = requests.get(url)
        REQUEST_COUNT += 1
        if response.status_code == 200:
            return response.text
    except:
        pass
    return None

def calculate_complexity(source_code, filename):
    try:
        analysis = lizard.analyze_file.analyze_source_code(filename, source_code)
        return analysis.average_cyclomatic_complexity, analysis.nloc
    except:
        return 0, 0

def process_dataset(filepath, output_path, context_name):
    print(f"Processing {filepath}...")
    
    updated_rows = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
        
    for i, row in enumerate(rows):
        # Update logic (limited)
        commit_url = row.get('commit_url')
        owner = row.get('repository_owner')
        repo = row.get('repository_name')
        sha = row.get('commit_sha')
        
        # Only process if we haven't hit limit and it's a valid commit
        files = []
        if REQUEST_COUNT < LIMIT_REQUESTS and commit_url:
            files = get_changed_files(commit_url)
            
            total_nloc = 0
            file_complexities = []
            
            for file_path in files:
                content = get_raw_content(owner, repo, sha, file_path)
                if content:
                    ccn, nloc = calculate_complexity(content, file_path)
                    total_nloc += nloc
                    file_complexities.append(ccn)
            
            if file_complexities:
                avg_comp = sum(file_complexities) / len(file_complexities)
                # Update row
                row['avg_complexity'] = avg_comp
                row['avg_loc'] = total_nloc / len(files) # avg loc per file? or total? "avg_loc" usually means per file
                # If the dataset has total_loc, we'd use that.
                
                print(f"Updated {commit_url}: CCN={avg_comp}, NLOC={row['avg_loc']}")
        
        updated_rows.append(row)

    with open(output_path, 'w', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

def filter_dataset(input_path, output_path, tool_name):
    print(f"Filtering {input_path} for tool {tool_name}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = [row for row in reader if row.get('ai_tool') == tool_name]
    
    if rows:
        with open(output_path, 'w', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Saved {len(rows)} rows to {output_path}")
    else:
        print(f"No rows found for {tool_name}")

if __name__ == "__main__":
    # Task 1: Update Metrics (Mock/Limited)
    # Datasets
    # 1. Agents
    process_dataset('datasets/agents_adoption_commits.csv', 'datasets/agents_adoption_commits_updated.csv', 'agents')
    # 2. Copilot
    process_dataset('datasets/copilot-instructions_adoption_commits.csv', 'datasets/copilot-instructions_adoption_commits_updated.csv', 'copilot')
    # 3. Claude
    process_dataset('datasets/claude_adoption_commits.csv', 'datasets/claude_adoption_commits_updated.csv', 'claude')

    # Task 2: Filter
    # Map: Agents -> Codex (or whatever the tool name is in the csv)
    # I should check the tool name for agents first.
    # From previous read: "Copilot" was allowed in agents?
    # Wait, the previous read of agents_adoption_commits.csv line 2 showed "Copilot"!
    # "copilot-swe-agent[bot],True,Copilot,Pre-Adoption"
    # But user asked: "agents_only_adoption_dataset should only contain commits with AI tool Codex from the original dataset agents_adoption_dataset"
    # This implies there ARE Codex commits there.
    
    filter_dataset('datasets/agents_adoption_commits_updated.csv', 'datasets/agents_only_adoption_dataset.csv', 'Codex')
    filter_dataset('datasets/copilot-instructions_adoption_commits_updated.csv', 'datasets/copilot_only_adoption_dataset.csv', 'Copilot')
    filter_dataset('datasets/claude_adoption_commits_updated.csv', 'datasets/claude_only_adoption_dataset.csv', 'Claude')
