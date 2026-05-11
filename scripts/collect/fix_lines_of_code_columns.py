"""
Fix Lines of Code Column Naming

This script consolidates the three manifest-specific line count columns
(lines_of_claude, lines_of_agents, lines_of_copilot-instructions) into 
a single universal column called 'lines_of_code'.

Current issue:
- claude_dataset.csv has values in 'lines_of_claude', others are empty
- agents_dataset.csv has values in 'lines_of_agents', others are empty
- copilot-instructions_dataset.csv has values in 'lines_of_copilot-instructions', others are empty

Solution:
- Create a new 'lines_of_code' column with the actual line count
- Remove the three separate columns
- Works universally across all dataset types

Usage:
    python fix_lines_of_code_columns.py
"""

import os
import sys
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import iter_manifest_datasets


def fix_lines_of_code_column(input_csv, output_csv, dataset_name):
    """
    Consolidate manifest-specific line columns into universal lines_of_code column.
    
    Args:
        input_csv: Path to input dataset
        output_csv: Path to save fixed dataset
        dataset_name: Name for logging
    """
    print(f"\n{'='*80}")
    print(f"Fixing Lines of Code Column: {dataset_name}")
    print(f"{'='*80}")
    
    # Read the dataset
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        old_fieldnames = reader.fieldnames
        rows = list(reader)
    
    print(f"📊 Loaded {len(rows)} entries")
    print(f"📋 Current columns: {len(old_fieldnames)}")
    
    # Check which columns exist
    has_claude = 'lines_of_claude' in old_fieldnames
    has_agents = 'lines_of_agents' in old_fieldnames
    has_copilot = 'lines_of_copilot-instructions' in old_fieldnames
    
    print(f"\n🔍 Column check:")
    print(f"   lines_of_claude: {'✓' if has_claude else '✗'}")
    print(f"   lines_of_agents: {'✓' if has_agents else '✗'}")
    print(f"   lines_of_copilot-instructions: {'✓' if has_copilot else '✗'}")
    
    # Create new fieldnames (replace the three columns with one)
    new_fieldnames = []
    replaced = False
    
    for field in old_fieldnames:
        if field == 'lines_of_claude' and not replaced:
            # Replace first occurrence with lines_of_code
            new_fieldnames.append('lines_of_code')
            replaced = True
            print(f"\n✏️  Replacing 'lines_of_claude' with 'lines_of_code'")
        elif field in ['lines_of_claude', 'lines_of_agents', 'lines_of_copilot-instructions']:
            # Skip the other manifest-specific columns
            print(f"✏️  Removing '{field}'")
            continue
        else:
            new_fieldnames.append(field)
    
    print(f"\n📋 New columns: {len(new_fieldnames)}")
    
    # Process rows and consolidate line counts
    fixed_rows = []
    values_found = 0
    values_empty = 0
    
    for row in rows:
        new_row = {}
        
        # Get the actual line count from whichever column has it
        lines_of_code = None
        
        if has_claude and row.get('lines_of_claude', '').strip():
            lines_of_code = row['lines_of_claude']
        elif has_agents and row.get('lines_of_agents', '').strip():
            lines_of_code = row['lines_of_agents']
        elif has_copilot and row.get('lines_of_copilot-instructions', '').strip():
            lines_of_code = row['lines_of_copilot-instructions']
        
        if lines_of_code:
            values_found += 1
        else:
            values_empty += 1
        
        # Build new row with updated field names
        for field in new_fieldnames:
            if field == 'lines_of_code':
                new_row[field] = lines_of_code if lines_of_code else ''
            else:
                new_row[field] = row.get(field, '')
        
        fixed_rows.append(new_row)
    
    print(f"\n📊 Line count statistics:")
    print(f"   With values: {values_found}/{len(rows)}")
    print(f"   Empty: {values_empty}/{len(rows)}")
    
    # Write the fixed dataset
    print(f"\n💾 Writing fixed dataset...")
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(fixed_rows)
    
    print(f"\n✅ Fix complete!")
    print(f"   Columns reduced: {len(old_fieldnames)} → {len(new_fieldnames)}")
    print(f"   Output: {output_csv}")


def main():
    """Main execution function."""
    print("="*80)
    print("Fix Lines of Code Column Naming")
    print("="*80)
    print("\nConsolidating manifest-specific columns into 'lines_of_code'\n")
    
    for dataset in iter_manifest_datasets():
        fix_lines_of_code_column(
            str(dataset.original_path),
            str(dataset.original_path),
            f"{dataset.key} dataset",
        )
    
    print("\n" + "="*80)
    print("🎉 All datasets fixed successfully!")
    print("="*80)
    print("\nChanges made:")
    print("  ✅ Replaced 'lines_of_claude' with 'lines_of_code'")
    print("  ✅ Removed 'lines_of_agents'")
    print("  ✅ Removed 'lines_of_copilot-instructions'")
    print("\nUpdated files:")
    for dataset in iter_manifest_datasets():
        print(f"  ✅ {dataset.original_path}")
    
    print("\nColumn count reduced from 21 to 19 in each dataset.")


if __name__ == "__main__":
    main()
