import csv
import re
from pathlib import Path
import textstat


def extract_patch_lines(patch_content, line_prefix):
    if not patch_content:
        return ""
    lines = []
    for line in patch_content.split('\n'):
        if line.startswith('@@'):
            continue
        if line.startswith(line_prefix) and not line.startswith('+++') and not line.startswith('---'):
            content = line[1:].strip()
            if content:
                lines.append(content)
    return '\n'.join(lines)


def calculate_length_of_words(text):
    if not text:
        return 0
    text_without_code = re.sub(r'```[\s\S]*?```', '', text)
    words = re.findall(r'\b\w+\b', text_without_code)
    return len(words)


def calculate_complexity_score(text):
    if not text or len(text.strip()) < 10:
        return 0.0
    try:
        text_without_code = re.sub(r'```[\s\S]*?```', '', text)
        if len(text_without_code.strip()) < 10:
            return 0.0
        score = textstat.flesch_reading_ease(text_without_code)
        return round(score, 2)
    except Exception:
        return 0.0


def process_commit_dataset(input_csv, output_csv, dataset_name):
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    new_columns = ['del_lines_of_words', 'del_complexity_score', 'add_lines_of_words', 'add_complexity_score']
    for col in new_columns:
        if col not in fieldnames:
            fieldnames.append(col)

    processed_rows = []
    for row in rows:
        patch_content = row.get('patch_content', '')
        deleted_text = extract_patch_lines(patch_content, '-')
        added_text = extract_patch_lines(patch_content, '+')

        row['del_lines_of_words'] = calculate_length_of_words(deleted_text)
        row['del_complexity_score'] = calculate_complexity_score(deleted_text)
        row['add_lines_of_words'] = calculate_length_of_words(added_text)
        row['add_complexity_score'] = calculate_complexity_score(added_text)

        processed_rows.append(row)

    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(processed_rows)
