#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import backoff
import openai
import pandas as pd
import requests
import tiktoken

# -----------------------------------------------------------------------------
# 1. Configuration
# -----------------------------------------------------------------------------
# Read secrets from environment variables. Do NOT hardcode secrets in source.
MODEL = os.getenv("GPT_MODEL", "gpt-5")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


# Label definitions (unchanged)
LABELS = {
    "system_overview": "Overview of the system, features of the system",
    "ai_integration": "Specific aspects related to integrating or interacting with AI agents. Can be notes, roles or reminder given to AI agent",
    "documentation_references": "Documents and references for AI agents",
    "architecture": "High-level structure, organization, and design principle. Can be project structure or key components",
    "implementation_details": "Details of how to implement a part of the code or system, code styles, piece of code",
    "build_run": "Processes of compiling the code, commands to build and run the system",
    "test": "Processes of running tests, add tests, creation of tests. Also commands used for running tests",
    "config_environment": "Settings and parameters for making the system works",
    "deployment_operations": "The processes of releasing software and managing it in a production environment. CI/CD",
    "project_management": "Planning and organization of the project",
    "development_process": "Details related to how to properly use Git in a development environment and how to review",
    "performance": "Details about performance of the system, how to improve them, and how to do quality assurance",
    "security": "Security aspect of the system",
    "ui_ux": "Details related to user interface",
    "maintainability": "The ease with which a software system can be modified, corrected, or enhanced over time",
    "debugging": "Error Handling and ways to debug errors, problems in the manifests files"
}

JSON_SCHEMA = {
    "name": "classification",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "Step-by-step analysis of the file. Identify key sections and explain why each chosen label applies."
            },
            "output": {
                "type": "array",
                "items": {"type": "string", "enum": list(LABELS.keys())},
                "description": "A list of all relevant labels for the agent manifest content."
            },
            "confidence": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "description": "Overall confidence score (1-10) for the chosen set of labels."
            }
        },
        "required": ["reasoning", "output", "confidence"],
        "additionalProperties": False  # <-- THIS LINE WAS ADDED
    }
}


# Examples for Few-Shot learning.)
FEW_SHOT_EXAMPLES = [
    {
        "content": "Label: system_overview\nFile Content:\nA README-like section that describes the project's purpose, key features, and scope. It explains what the system does and who it's for.\nQuestion: Does this file contain the 'System Overview' label? Answer Yes or No and provide a short reasoning.",
        "json_output": {
            "reasoning": "This content is a high-level description of the project goals and features, which matches 'system_overview'.",
            "output": ["system_overview"],
            "confidence": 9
        }
    },
    {
        "content": "Label: build_run\nFile Content:\nA section giving specific commands: `npm run dev`, `npm run build`, and notes on build artifacts and deployment steps.\nQuestion: Does this file contain the 'Build and Run' label? Answer Yes or No and provide a short reasoning.",
        "json_output": {
            "reasoning": "The section lists exact build and run commands and how to produce artifacts, which maps to 'build_run'.",
            "output": ["build_run"],
            "confidence": 10
        }
    },
    {
        "content": "Label: ai_integration\nFile Content:\nA note for the AI agent describing its role: 'You are an expert in React & Next.js and should behave as a content editor for this repo.'\nQuestion: Does this file contain the 'AI Integration' label? Answer Yes or No and provide a short reasoning.",
        "json_output": {
            "reasoning": "The file includes explicit instructions aimed at an AI agent describing role and behavior, which is 'ai_integration'.",
            "output": ["ai_integration"],
            "confidence": 10
        }
    }
]

### Load LaTeX label examples file and include its plain text for context.
LABEL_EXAMPLES_PATH = Path(__file__).resolve().parent / "label_examples.txt"

def load_label_examples_text() -> str:
    """Read `label_examples.txt` and return as plain text (falls back to empty string)."""
    try:
        if LABEL_EXAMPLES_PATH.exists():
            text = LABEL_EXAMPLES_PATH.read_text(encoding="utf-8")
            # The file is in LaTeX; for prompt purposes we'll include it as-is. If desired, strip LaTeX commands.
            return text
    except Exception:
        pass
    return ""

LABEL_EXAMPLES_TEXT = load_label_examples_text()
# -----------------------------------------------------------------------------
# 2. Utilities
# -----------------------------------------------------------------------------
from utils import truncate_to_tokens, fetch_file_content


class GPTClassifier:
    """Encapsulates OpenAI classification logic and prompt construction."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or MODEL
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in the environment.")
        # create a client instance when needed
        self._client = openai.OpenAI(api_key=self.api_key)

    @backoff.on_exception(backoff.expo, (openai.RateLimitError, openai.APIConnectionError), max_tries=5)
    def classify(self, file_content: str) -> tuple[str, list, int]:
        """Classify the given file content and return (reasoning, labels, confidence)."""
        # Build the few-shot examples part of the prompt
        examples_str = ""
        for i, example in enumerate(FEW_SHOT_EXAMPLES, 1):
            examples_str += f"### Example {i}\n"
            examples_str += f"File Content:\n{example['content']}\n\n"
            examples_str += f"Correct JSON Output:\n{json.dumps(example['json_output'])}\n\n"

        labels_str = "\n".join([f"- {key}: {value}" for key, value in LABELS.items()])

        binary_instruction = (
            "For each label below, ask the question: \"Does this file contain the <LABEL_DISPLAY_NAME> label?\" "
            "Answer with Yes or No and provide a short reasoning sentence for that label."
        )

        extras = (
            f"Additional label examples (from repository file 'label_examples.txt'):\n{LABEL_EXAMPLES_TEXT}\n\n"
            if LABEL_EXAMPLES_TEXT
            else ""
        )

        system_prompt = f"""
You are an expert software engineering researcher specializing in agent context files.

We will follow a binary per-label prediction style using few-shot examples.

Label definitions:
{labels_str}

Binary instruction:
{binary_instruction}

Use the examples below to learn the format. Each example demonstrates asking a single label question and the correct JSON output showing that label when present.

{examples_str}

{extras}
Now, for the target file, perform the binary question for each label and then provide the final JSON output with fields: 'reasoning' (explain key label decisions), 'output' (list of labels predicted as present), and 'confidence' (1-10 overall confidence).
"""

        user_content = f"File Content:\n---\n{file_content}\n---"

        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
            temperature=1,
            response_format={"type": "json_schema", "json_schema": JSON_SCHEMA},
        )

        data = json.loads(resp.choices[0].message.content)
        return data["reasoning"], data["output"], int(data["confidence"])


# Provide a module-level default classifier and compatibility wrapper
_default_classifier: GPTClassifier | None = None

def get_default_classifier() -> GPTClassifier:
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = GPTClassifier()
    return _default_classifier

def classify_content_with_gpt(file_content: str) -> tuple[str, list, int]:
    return get_default_classifier().classify(file_content)

# Classification function with backoff
@backoff.on_exception(backoff.expo, (openai.RateLimitError, openai.APIConnectionError), max_tries=5)
def classify_content_with_gpt(file_content: str) -> tuple[str, list, int]:
    """Classifies file content using an advanced prompt with few-shot examples."""
    
    # Build the few-shot examples part of the prompt
    examples_str = ""
    for i, example in enumerate(FEW_SHOT_EXAMPLES, 1):
        examples_str += f"### Example {i}\n"
        examples_str += f"File Content:\n{example['content']}\n\n"
        examples_str += f"Correct JSON Output:\n{json.dumps(example['json_output'])}\n\n"

    labels_str = "\n".join([f"- {key}: {value}" for key, value in LABELS.items()])

    # Construct a binary, per-label few-shot prompt. The few-shot examples above
    # show the style: for a given label, ask whether the file contains it (Yes/No)
    # and provide short reasoning. After going through each label, return the
    # final JSON with reasoning, output (list of labels with Yes), and confidence.
    binary_instruction = (
        "For each label below, ask the question: \"Does this file contain the <LABEL_DISPLAY_NAME> label?\" "
        "Answer with Yes or No and provide a short reasoning sentence for that label."
    )

    extras = (
        f"Additional label examples (from repository file 'label_examples.txt'):\n{LABEL_EXAMPLES_TEXT}\n\n"
        if LABEL_EXAMPLES_TEXT
        else ""
    )

    system_prompt = f"""
You are an expert software engineering researcher specializing in agent context files.

We will follow a binary per-label prediction style using few-shot examples.

Label definitions:
{labels_str}

Binary instruction:
{binary_instruction}

Use the examples below to learn the format. Each example demonstrates asking a single label question and the correct JSON output showing that label when present.

{examples_str}

{extras}
Now, for the target file, perform the binary question for each label and then provide the final JSON output with fields: 'reasoning' (explain key label decisions), 'output' (list of labels predicted as present), and 'confidence' (1-10 overall confidence).
"""
    
    user_content = f"File Content:\n---\n{file_content}\n---"

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    # NOTE: some models (like the configured MODEL) only accept the default
    # temperature. Use 1 (the default) to avoid API errors for unsupported values.
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
        temperature=1,
        response_format={"type": "json_schema", "json_schema": JSON_SCHEMA},
    )

    data = json.loads(resp.choices[0].message.content)
    return data["reasoning"], data["output"], int(data["confidence"])

# -----------------------------------------------------------------------------
# 4. Main Driver
# -----------------------------------------------------------------------------
def main(input_csv: str, output_csv: str, id_column: str, url_column: str):
    df_input = pd.read_csv(input_csv)

    # If the configured id_column isn't present, fall back to the first column
    if id_column not in df_input.columns:
        print(f"ID column '{id_column}' not found in input CSV. Available columns: {list(df_input.columns)}")
        fallback = df_input.columns[0]
        print(f"Falling back to use the first column '{fallback}' as the id column.")
        id_column = fallback

    # Validate URL column exists
    if url_column not in df_input.columns:
        raise RuntimeError(f"URL column '{url_column}' not found in input CSV. Available columns: {list(df_input.columns)}")

    if Path(output_csv).exists():
        df_output = pd.read_csv(output_csv)
        existing_ids = set(df_output[id_column].astype(str))
        print(f"Found {len(existing_ids)} already processed items in {output_csv}.")
    else:
        df_output = pd.DataFrame()
        existing_ids = set()

    results = []
    for _, row in df_input.iterrows():
        item_id = str(row[id_column])
        if item_id in existing_ids:
            continue

        print(f"Processing item '{item_id}'...")
        file_url = row[url_column]
        content = fetch_file_content(file_url, github_token=GITHUB_TOKEN)

        if content:
            truncated_content = truncate_to_tokens(content, 8000, model_name=MODEL)
            try:
                reasoning, labels, conf = classify_content_with_gpt(truncated_content)
                print(f"  -> Classified as {labels} (Confidence: {conf})")
                results.append({
                    id_column: item_id,
                    "reasoning": reasoning,
                    "type": labels,
                    "confidence": conf,
                })
            except Exception as e:
                print(f"  -> ERROR classifying item '{item_id}': {e}")
        else:
            print(f"  -> SKIPPED item '{item_id}' due to fetch error.")
    
    if results:
        new_results_df = pd.DataFrame(results)
        final_df = pd.concat([df_output, new_results_df], ignore_index=True)
        final_df.to_csv(output_csv, index=False)
        print(f"\nSaved {len(new_results_df)} new classifications to {output_csv}")
    else:
        print("\nNo new items to process or save.")


if __name__ == "__main__":
    # --- Configuration ---
    INPUT_FILE = 'final_am_classification.csv'
    OUTPUT_FILE = 'gpt_5_file_classifications.csv'
    # The column in your CSV that uniquely identifies each row (e.g., commit_sha)
    ID_COLUMN_NAME = 'ID' 
    # The column in your CSV that contains the GitHub file URL
    URL_COLUMN_NAME = 'file_url' 

    main(input_csv=INPUT_FILE, output_csv=OUTPUT_FILE, id_column=ID_COLUMN_NAME, url_column=URL_COLUMN_NAME)