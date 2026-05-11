# Rules
- Always ask me questions if you are unsure about how to do the tasks
- Repeat the steps before taling any action

# Dataset Documentation

This directory contains the datasets used for analyzing agentic manifests. The datasets are categorized into three main groups based on the source manifest type:

- **Agents (`agents_*.csv`)**: Repositories containing general AI agent manifests (e.g., `ai-agents.md`, `.agentic`).
- **Claude (`claude_*.csv`)**: Repositories containing Claude-specific manifests or system prompts.
- **Copilot Instructions (`copilot-instructions_*.csv`)**: Repositories using `.github/copilot-instructions.md` to guide AI interactions.

Each category consists of four primary dataset types, described below:

## 1. Main Datasets (`*_dataset.csv`) - "main datasets"
These files contain metadata about the repositories and the target manifest files identified during the collection phase.

| Attribute | Description |
| :--- | :--- |
| `repository_owner` | The GitHub username or organization owning the repo. |
| `repository_name` | The name of the repository. |
| `file_path` | The path to the manifest file within the repository. |
| `filename` | The name of the file. |
| `original_file_path` | The original path of the file (useful if tracking moves). |
| `repository_url` | Full GitHub URL of the repository. |
| `file_url` | Direct GitHub URL to the manifest file content. |
| `branch` | The default branch of the repository. |
| `stargazers_count` | Number of stars (popularity metric). |
| `forks_count` | Number of forks (engagement metric). |
| `created_at` | Date when the repository was created. |
| `pushed_at` | Date of the latest push to the repository. |
| `updated_at` | Date of the latest update (metadata/code). |
| `lines_of_code` | Total line count of the manifest file. |
| `manifest_specific_commit_count` | Number of commits that specifically targeted this file. |
| `first_manifest_commit_date`| The date of the first commit that introduced or modified the file. |
| `file_composite_key` | A unique string identifying the file across the entire dataset. |
| `length_of_words` | Total word count in the manifest. |
| `complexity_score` | A metric representing the semantic or structural complexity of the content. |

## 2. Static Analysis Datasets (`*_static_dataset.csv`) - "static datasets
These files extend the main datasets with the actual content of the files and specific line-count metrics.

*Inherits all attributes from Main Datasets, plus:*

| Attribute | Description |
| :--- | :--- |
| `lines_of_claude` | Count of lines specifically related to Claude instructions. |
| `lines_of_agents` | Count of lines specifically related to general Agent instructions. |
| `lines_of_copilot-instructions` | Count of lines related to GitHub Copilot instructions. |
| `static_content` | The full raw text content of the manifest file. |
| `file_commit` | The specific commit SHA from which the static content was extracted. |

## 3. Structural Analysis Datasets (`*_sections.csv`) - "section datasets"
These files provide a breakdown of the Markdown structure within the manifests, focusing on header hierarchies and content distribution.

| Attribute | Description |
| :--- | :--- |
| `total_h1` - `total_h6` | The count of Markdown headers for levels 1 through 6. |
| `median_hX_under_hY` | Median number of sub-headers level X nested under a level Y header. |
| `avg_loc_hX` | Average lines of code (content) found under headers of level X. |
| `median_loc_hX` | Median lines of code (content) found under headers of level X. |

## 4. Evolution Datasets (`*_commit_changes.csv`) - ""commit datasets""
These files track the historical changes made to the manifest files through commits.

| Attribute | Description |
| :--- | :--- |
| `commit_sha` | The unique identifier for the commit. |
| `commit_message` | The text message associated with the commit. |
| `commit_url` | Link to the commit on GitHub. |
| `commit_date` | Date and time when the change was committed. |
| `lines_added` | Number of lines added to the file in this commit. |
| `lines_deleted` | Number of lines removed from the file in this commit. |
| `patch_content` | The raw diff (patch) showing the exact changes made. |
| `sections_changed_count` | Number of Markdown sections that were modified. |
| `del_lines_of_words` | Word count of the deleted lines. |
| `add_lines_of_words` | Word count of the added lines. |
| `del_complexity_score` | Average complexity score of deleted lines. |
| `add_complexity_score` | Average complexity score of added lines. |
