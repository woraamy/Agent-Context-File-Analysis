import os
import re

# Input CSV files location; raw datasets
RAW_DATASETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'raw_datasets')


def parse_file_path(file_path):
    """
    Parses a file_path from the CSV dump files.
    Expected format: raw/owner/repo/path/to/file.md
    Returns: (owner, repo, file_path_in_repo, filename)
    """
    if not isinstance(file_path, str) or not file_path.startswith("raw/"):
        return None, None, None, None

    path_without_raw = file_path[4:]
    parts = path_without_raw.split('/', 2)
    if len(parts) < 3:
        return None, None, None, None

    owner, repo, file_path_in_repo = parts
    filename = os.path.basename(file_path_in_repo)
    return owner, repo, file_path_in_repo, filename


def count_sections_changed(patch_content):
    """Analyzes a Git patch to count how many unique Markdown sections (headings) were changed."""
    if not isinstance(patch_content, str):
        return 0
    heading_regex = re.compile(r'^(#+)\s*(.*)$')
    changed_sections = set()
    for line in patch_content.split('\n'):
        if line.startswith('+') or line.startswith('-'):
            stripped_line = line[1:].strip()
            match = heading_regex.match(stripped_line)
            if match:
                heading_text = match.group(2).strip()
                changed_sections.add(heading_text)
    return len(changed_sections)
