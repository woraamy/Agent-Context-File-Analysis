"""Smoke test helper for static file collection."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.collect.static_files_collection import get_file_content_and_commit


def test_single_file():
    """Test retrieving content from a single file."""
    print("="*80)
    print("Testing single file retrieval")
    print("="*80)
    
    # Test with a known file from the datasets
    test_cases = [
        {
            'owner': 'accretion-xyz',
            'repo': 'solana-data-reverser',
            'file_path': 'CLAUDE.md',
            'branch': 'main'
        },
        {
            'owner': 'arc42',
            'repo': 'quality.arc42.org-site',
            'file_path': 'AGENTS.md',
            'branch': 'main'
        }
    ]
    
    for idx, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"Test {idx}: {test['owner']}/{test['repo']}/{test['file_path']}")
        print(f"{'='*80}")
        
        content, commit_sha = get_file_content_and_commit(
            test['owner'],
            test['repo'],
            test['file_path'],
            test['branch']
        )
        
        if content and commit_sha:
            print(f"✅ Success!")
            print(f"   Content length: {len(content)} characters")
            print(f"   Commit SHA: {commit_sha}")
            print(f"   First 200 chars of content:")
            print(f"   {'-'*80}")
            print(f"   {content[:200]}")
            print(f"   {'-'*80}")
        else:
            print(f"❌ Failed to retrieve content")
    
    print(f"\n{'='*80}")
    print("Test complete!")
    print(f"{'='*80}")


if __name__ == "__main__":
    test_single_file()
