"""
Update Original and Sections Datasets Based on Static Datasets

This script performs two main tasks:
1. Updates original datasets (e.g., claude_dataset.csv) to only include entries 
   that exist in the static datasets and updates branch names if they changed
2. Recalculates sections datasets using the actual static_content from static datasets
   instead of fetching from GitHub API

Usage:
    python update_datasets_with_static.py
"""

import os
import sys
import csv
import numpy as np
from pathlib import Path
from markdown_it import MarkdownIt

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


def analyze_manifest_structure(markdown_content):
    """
    Analyzes markdown content to extract headers, their nesting relationships,
    and the lines of code (LOC) within each section.
    
    (Same logic as in analyze_sections_and_headers.py)
    
    Returns:
        A dictionary containing all calculated metrics for the file.
    """
    md = MarkdownIt()
    tokens = md.parse(markdown_content)
    lines = markdown_content.splitlines()
    num_lines = len(lines)

    # 1. Extract accurate header information (level, name, start line)
    headers = []
    for i, token in enumerate(tokens):
        if token.type == 'heading_open':
            level = int(token.tag[1])
            # The header name is in the next 'inline' token
            header_name = tokens[i + 1].content.strip() if (i + 1) < len(tokens) else ""
            # map is a list [start_line, end_line]
            start_line = token.map[0] if token.map else 0
            headers.append({'level': level, 'name': header_name, 'start_line': start_line})

    if not headers:
        return {}  # Return empty dict if no headers are found

    # 2. Calculate LOC for each header's section
    loc_per_header_level = {i: [] for i in range(1, 7)}
    for i, header in enumerate(headers):
        start_line = header['start_line']
        # Section ends at the next header of same or higher level, or at the end of the file
        end_line = num_lines
        for j in range(i + 1, len(headers)):
            next_header = headers[j]
            if next_header['level'] <= header['level']:
                end_line = next_header['start_line']
                break

        # Count non-empty lines within the section, ignoring code block fences
        section_lines = lines[start_line + 1: end_line]
        loc_count = 0
        in_code_block = False
        for line in section_lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            if not in_code_block and line.strip():
                loc_count += 1

        # Associate the calculated LOC with the header
        header['loc'] = loc_count
        loc_per_header_level[header['level']].append(loc_count)

    # 3. Calculate all aggregate metrics
    metrics = {}

    # Total header counts
    for level in range(1, 7):
        metrics[f'total_h{level}'] = sum(1 for h in headers if h['level'] == level)

    # Median nesting
    for p_level in range(1, 6):  # Parent H1 to H5
        for c_level in range(p_level + 1, 7):  # Child H2 to H6
            key = f"median_h{c_level}_under_h{p_level}"
            counts_for_median = []
            for i, p_header in enumerate(headers):
                if p_header['level'] == p_level:
                    child_count = 0
                    # Scan subsequent headers
                    for j in range(i + 1, len(headers)):
                        next_header = headers[j]
                        if next_header['level'] <= p_level:
                            break  # End of this parent's scope
                        if next_header['level'] == c_level:
                            child_count += 1
                    counts_for_median.append(child_count)
            metrics[key] = np.median(counts_for_median) if counts_for_median else 0.0

    # Average and Median LOC per header level
    for level in range(1, 7):
        counts = loc_per_header_level.get(level, [])
        if counts:
            metrics[f'avg_loc_h{level}'] = np.mean(counts)
            metrics[f'median_loc_h{level}'] = np.median(counts)
        else:
            metrics[f'avg_loc_h{level}'] = 0.0
            metrics[f'median_loc_h{level}'] = 0.0

    return metrics


def create_file_key(owner, repo, file_url):
    """Create a unique key for matching files across datasets."""
    return f"{owner}||{repo}||{file_url}"


def update_original_dataset(original_csv, static_csv, output_csv, dataset_name):
    """
    Update original dataset to only include entries in static dataset
    and update branch names if they changed.
    
    Args:
        original_csv: Path to original dataset (e.g., claude_dataset.csv)
        static_csv: Path to static dataset (e.g., claude_static_dataset.csv)
        output_csv: Path to save updated original dataset
        dataset_name: Name for logging
    """
    print(f"\n{'='*80}")
    print(f"Updating Original Dataset: {dataset_name}")
    print(f"{'='*80}")
    
    # Read static dataset to get the valid entries
    static_entries = {}
    with open(static_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = create_file_key(row['repository_owner'], row['repository_name'], row['file_url'])
            static_entries[key] = row
    
    print(f"📊 Static dataset has {len(static_entries)} entries")
    
    # Read original dataset
    with open(original_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        original_fieldnames = reader.fieldnames
        original_rows = list(reader)
    
    print(f"📊 Original dataset has {len(original_rows)} entries")
    
    # Filter and update original rows
    updated_rows = []
    matched = 0
    updated_branches = 0
    
    for row in original_rows:
        key = create_file_key(row['repository_owner'], row['repository_name'], row['file_url'])
        
        if key in static_entries:
            matched += 1
            static_row = static_entries[key]
            
            # Check if branch name changed
            if row['branch'] != static_row['branch']:
                print(f"  📝 Updating branch for {row['repository_owner']}/{row['repository_name']}: "
                      f"{row['branch']} → {static_row['branch']}")
                row['branch'] = static_row['branch']
                updated_branches += 1
            
            updated_rows.append(row)
    
    # Write updated dataset
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=original_fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)
    
    removed = len(original_rows) - matched
    
    print(f"\n✅ Update complete!")
    print(f"   Matched: {matched}/{len(original_rows)}")
    print(f"   Removed: {removed}")
    print(f"   Branch names updated: {updated_branches}")
    print(f"   Output: {output_csv}")


def update_sections_dataset(static_csv, sections_csv, output_csv, dataset_name):
    """
    Recalculate sections using static_content from static dataset.
    
    Args:
        static_csv: Path to static dataset with static_content column
        sections_csv: Path to existing sections dataset (for reference structure)
        output_csv: Path to save updated sections dataset
        dataset_name: Name for logging
    """
    print(f"\n{'='*80}")
    print(f"Updating Sections Dataset: {dataset_name}")
    print(f"{'='*80}")
    
    # Define the output columns (same as original sections file)
    sections_fieldnames = [
        'repository_owner', 'repository_name', 'file_url',
        'total_h1', 'total_h2', 'total_h3', 'total_h4', 'total_h5', 'total_h6',
        'median_h2_under_h1', 'median_h3_under_h1', 'median_h4_under_h1', 
        'median_h5_under_h1', 'median_h6_under_h1',
        'median_h3_under_h2', 'median_h4_under_h2', 'median_h5_under_h2', 'median_h6_under_h2',
        'median_h4_under_h3', 'median_h5_under_h3', 'median_h6_under_h3',
        'median_h5_under_h4', 'median_h6_under_h4',
        'median_h6_under_h5',
        'avg_loc_h1', 'median_loc_h1',
        'avg_loc_h2', 'median_loc_h2',
        'avg_loc_h3', 'median_loc_h3',
        'avg_loc_h4', 'median_loc_h4',
        'avg_loc_h5', 'median_loc_h5',
        'avg_loc_h6', 'median_loc_h6'
    ]
    
    # Read static dataset
    with open(static_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        static_rows = list(reader)
    
    print(f"📊 Processing {len(static_rows)} files from static dataset")
    
    # Process each file and calculate sections
    sections_rows = []
    success = 0
    failed = 0
    
    for idx, row in enumerate(static_rows, 1):
        owner = row['repository_owner']
        repo = row['repository_name']
        file_url = row['file_url']
        static_content = row.get('static_content', '')
        
        if idx % 100 == 0:
            print(f"  Progress: {idx}/{len(static_rows)} ({success} success, {failed} failed)")
        
        if not static_content:
            print(f"  ⚠️  [{idx}] No content for {owner}/{repo}")
            failed += 1
            continue
        
        try:
            # Analyze the markdown structure
            metrics = analyze_manifest_structure(static_content)
            
            if not metrics:
                print(f"  ⚠️  [{idx}] No headers found in {owner}/{repo}")
                failed += 1
                continue
            
            # Create the sections row
            sections_row = {
                'repository_owner': owner,
                'repository_name': repo,
                'file_url': file_url
            }
            
            # Add all metrics
            for field in sections_fieldnames[3:]:  # Skip owner, repo, url
                sections_row[field] = metrics.get(field, 0.0)
            
            sections_rows.append(sections_row)
            success += 1
            
        except Exception as e:
            print(f"  ❌ [{idx}] Error processing {owner}/{repo}: {e}")
            failed += 1
            continue
    
    # Write updated sections dataset
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=sections_fieldnames)
        writer.writeheader()
        writer.writerows(sections_rows)
    
    print(f"\n✅ Sections update complete!")
    print(f"   Success: {success}/{len(static_rows)}")
    print(f"   Failed: {failed}/{len(static_rows)}")
    print(f"   Output: {output_csv}")


def main():
    """Main execution function."""
    print("="*80)
    print("Update Datasets with Static Content")
    print("="*80)
    
    script_dir = Path(__file__).parent
    datasets_dir = script_dir.parent / 'datasets'
    
    # Define dataset configurations
    datasets = [
        {
            'name': 'Claude',
            'original': datasets_dir / 'claude_dataset.csv',
            'static': datasets_dir / 'claude_static_dataset.csv',
            'sections': datasets_dir / 'claude_sections.csv',
            'original_output': datasets_dir / 'claude_dataset.csv',  # Overwrite
            'sections_output': datasets_dir / 'claude_sections.csv'  # Overwrite
        },
        {
            'name': 'Agents',
            'original': datasets_dir / 'agents_dataset.csv',
            'static': datasets_dir / 'agents_static_dataset.csv',
            'sections': datasets_dir / 'agents_sections.csv',
            'original_output': datasets_dir / 'agents_dataset.csv',
            'sections_output': datasets_dir / 'agents_sections.csv'
        },
        {
            'name': 'Copilot-Instructions',
            'original': datasets_dir / 'copilot-instructions_dataset.csv',
            'static': datasets_dir / 'copilot-instructions_static_dataset.csv',
            'sections': datasets_dir / 'copilot-instructions_sections.csv',
            'original_output': datasets_dir / 'copilot-instructions_dataset.csv',
            'sections_output': datasets_dir / 'copilot-instructions_sections.csv'
        }
    ]
    
    for dataset in datasets:
        # Step 1: Update original dataset
        update_original_dataset(
            str(dataset['original']),
            str(dataset['static']),
            str(dataset['original_output']),
            f"{dataset['name']} Original Dataset"
        )
        
        # Step 2: Update sections dataset
        update_sections_dataset(
            str(dataset['static']),
            str(dataset['sections']),
            str(dataset['sections_output']),
            f"{dataset['name']} Sections Dataset"
        )
    
    print("\n" + "="*80)
    print("🎉 All datasets updated successfully!")
    print("="*80)
    print("\nUpdated files:")
    for dataset in datasets:
        print(f"  ✅ {dataset['original_output']}")
        print(f"  ✅ {dataset['sections_output']}")


if __name__ == "__main__":
    main()
