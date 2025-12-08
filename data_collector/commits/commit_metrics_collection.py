"""
Calculate Word Length and Complexity Scores for Commit Datasets

This script calculates length_of_words and complexity_score for both deleted
and added lines in commit patches. It parses the patch_content column to:
- Extract lines with "-" prefix (deleted lines)
- Extract lines with "+" prefix (added lines)

The script adds four new columns:
- del_lines_of_words: Word count for deleted lines
- del_complexity_score: Complexity score for deleted lines
- add_lines_of_words: Word count for added lines
- add_complexity_score: Complexity score for added lines

Usage:
    python calculate_commit_metrics.py
"""

import os
import sys
import csv
import re
from pathlib import Path
import textstat


def extract_patch_lines(patch_content, line_prefix):
    """
    Extract lines from patch content that start with the given prefix.
    
    Args:
        patch_content: The git patch content
        line_prefix: The prefix to filter by ('-' for deleted, '+' for added)
    
    Returns:
        str: Combined text of all matching lines
    """
    if not patch_content:
        return ""
    
    lines = []
    for line in patch_content.split('\n'):
        # Skip patch headers (@@ markers)
        if line.startswith('@@'):
            continue
        
        # Extract lines with the specified prefix
        if line.startswith(line_prefix) and not line.startswith('+++') and not line.startswith('---'):
            # Remove the prefix and add to lines
            content = line[1:].strip()
            if content:  # Only add non-empty lines
                lines.append(content)
    
    return '\n'.join(lines)


def calculate_length_of_words(text):
    """
    Calculate the total number of words in the text.
    
    Args:
        text: The text content to analyze
    
    Returns:
        int: Total word count
    """
    if not text:
        return 0
    
    # Remove code blocks (markdown style)
    text_without_code = re.sub(r'```[\s\S]*?```', '', text)
    
    # Count words
    words = re.findall(r'\b\w+\b', text_without_code)
    return len(words)


def calculate_complexity_score(text):
    """
    Calculate complexity score using Flesch Reading Ease score.
    
    Higher scores indicate easier text:
    - 90-100: Very Easy
    - 80-89: Easy
    - 70-79: Fairly Easy
    - 60-69: Standard
    - 50-59: Fairly Difficult
    - 30-49: Difficult
    - 0-29: Very Confusing
    
    Args:
        text: The text content to analyze
    
    Returns:
        float: Flesch Reading Ease score, rounded to 2 decimal places
    """
    if not text or len(text.strip()) < 10:
        return 0.0
    
    try:
        # Remove code blocks as they shouldn't be counted in readability
        text_without_code = re.sub(r'```[\s\S]*?```', '', text)
        
        if len(text_without_code.strip()) < 10:
            return 0.0
        
        # Calculate Flesch Reading Ease
        score = textstat.flesch_reading_ease(text_without_code)
        return round(score, 2)
    except Exception as e:
        # Return 0.0 for any calculation errors (e.g., no sentences, no syllables)
        return 0.0


def process_commit_dataset(input_csv, output_csv, dataset_name):
    """
    Process a commit dataset to calculate metrics for deleted and added lines.
    
    Args:
        input_csv: Path to input commit dataset
        output_csv: Path to output dataset with new metrics
        dataset_name: Name for logging
    """
    print(f"\n{'='*80}")
    print(f"Processing: {dataset_name}")
    print(f"{'='*80}")
    
    # Read input dataset
    print(f"📖 Reading dataset from {input_csv}...")
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)
    
    print(f"📊 Loaded {len(rows)} commit entries")
    
    # Add new columns if they don't exist
    new_columns = ['del_lines_of_words', 'del_complexity_score', 
                   'add_lines_of_words', 'add_complexity_score']
    for col in new_columns:
        if col not in fieldnames:
            fieldnames.append(col)
    
    # Process each row
    print(f"\n🔄 Calculating metrics for deleted and added lines...")
    processed_rows = []
    
    for idx, row in enumerate(rows, 1):
        patch_content = row.get('patch_content', '')
        
        # Extract deleted and added lines
        deleted_text = extract_patch_lines(patch_content, '-')
        added_text = extract_patch_lines(patch_content, '+')
        
        # Calculate metrics for deleted lines
        row['del_lines_of_words'] = calculate_length_of_words(deleted_text)
        row['del_complexity_score'] = calculate_complexity_score(deleted_text)
        
        # Calculate metrics for added lines
        row['add_lines_of_words'] = calculate_length_of_words(added_text)
        row['add_complexity_score'] = calculate_complexity_score(added_text)
        
        processed_rows.append(row)
        
        # Progress update
        if idx % 1000 == 0:
            print(f"  Progress: {idx}/{len(rows)} commits processed")
        
        # Show sample for first few rows
        if idx <= 3:
            repo_info = f"{row['repository_owner']}/{row['repository_name']}"
            print(f"\n  📝 Sample [{idx}] {repo_info}")
            print(f"      Deleted: {row['del_lines_of_words']} words, "
                  f"complexity {row['del_complexity_score']}")
            print(f"      Added: {row['add_lines_of_words']} words, "
                  f"complexity {row['add_complexity_score']}")
    
    # Write output dataset
    print(f"\n💾 Writing updated dataset to {output_csv}...")
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(processed_rows)
    
    print(f"\n✅ Processing complete!")
    print(f"   Total commits processed: {len(processed_rows)}")
    print(f"   Output saved to: {output_csv}")
    
    # Calculate and show statistics
    print(f"\n📈 Statistics:")
    total_del_words = sum(int(row['del_lines_of_words']) for row in processed_rows)
    total_add_words = sum(int(row['add_lines_of_words']) for row in processed_rows)
    avg_del_complexity = sum(float(row['del_complexity_score']) for row in processed_rows) / len(processed_rows) if processed_rows else 0
    avg_add_complexity = sum(float(row['add_complexity_score']) for row in processed_rows) / len(processed_rows) if processed_rows else 0
    
    print(f"   Total deleted words: {total_del_words:,}")
    print(f"   Total added words: {total_add_words:,}")
    print(f"   Avg deleted complexity: {avg_del_complexity:.2f}")
    print(f"   Avg added complexity: {avg_add_complexity:.2f}")


def main():
    """Main execution function."""
    print("="*80)
    print("Calculate Commit Metrics - Deleted vs Added Lines")
    print("="*80)
    print("\nThis script calculates word length and complexity scores for")
    print("deleted lines (prefix '-') and added lines (prefix '+') in commit patches.\n")
    
    script_dir = Path(__file__).parent
    datasets_dir = script_dir.parent / 'datasets'
    
    # Check if datasets directory exists
    if not datasets_dir.exists():
        print(f"❌ Error: Datasets directory not found: {datasets_dir}")
        return
    
    # Define commit dataset configurations
    datasets = [
        {
            'name': 'Claude Commit Changes',
            'input': datasets_dir / 'claude_commit_changes.csv',
            'output': datasets_dir / 'claude_commit_changes.csv'  # Overwrite
        },
        {
            'name': 'Agents Commit Changes',
            'input': datasets_dir / 'agents_commit_changes.csv',
            'output': datasets_dir / 'agents_commit_changes.csv'
        },
        {
            'name': 'Copilot-Instructions Commit Changes',
            'input': datasets_dir / 'copilot-instructions_commit_changes.csv',
            'output': datasets_dir / 'copilot-instructions_commit_changes.csv'
        }
    ]
    
    # Process each dataset
    for dataset in datasets:
        if not dataset['input'].exists():
            print(f"\n⚠️  Skipping {dataset['name']}: File not found")
            print(f"    Expected: {dataset['input']}")
            continue
        
        process_commit_dataset(
            str(dataset['input']),
            str(dataset['output']),
            dataset['name']
        )
    
    print("\n" + "="*80)
    print("🎉 All commit datasets processed successfully!")
    print("="*80)
    print("\nNew columns added:")
    print("  • del_lines_of_words - Word count for deleted lines")
    print("  • del_complexity_score - Flesch Reading Ease score for deleted lines")
    print("  • add_lines_of_words - Word count for added lines")
    print("  • add_complexity_score - Flesch Reading Ease score for added lines")
    print("\nUpdated files:")
    for dataset in datasets:
        if dataset['input'].exists():
            print(f"  ✅ {dataset['output']}")


if __name__ == "__main__":
    main()
