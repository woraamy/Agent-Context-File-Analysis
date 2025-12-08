"""Compatibility shim for measure_accuracy (moved).

If needed, implement the function here or import from the new location.
Currently this module provides a placeholder to avoid import errors.
"""

def measure_accuracy(*args, **kwargs):
    raise NotImplementedError("measure_accuracy has been moved or removed; implement as needed.")

__all__ = ["measure_accuracy"]
#!/usr/bin/env python3
"""Compute multilabel classification metrics between ground truth and GPT predictions.

Usage: python3 measure_accuracy.py
Reads `final_am_classification_2.csv` and `gpt_5_file_classifications.csv` from the same folder.
Saves `classification_report.json` and prints a human-readable report.
"""
from __future__ import annotations

import ast
import re
import json
from pathlib import Path
from typing import List

import pandas as pd
from sklearn.metrics import classification_report
from sklearn.preprocessing import MultiLabelBinarizer


LABEL_KEYS = [
    "system_overview",
    "ai_integration",
    "documentation_references",
    "architecture",
    "implementation_details",
    "build_run",
    "test",
    "config_environment",
    "deployment_operations",
    "project_management",
    "development_process",
    "performance",
    "security",
    "ui_ux",
    "maintainability",
    "debugging",
]

DISPLAY_NAMES = {
    "system_overview": "System Overview",
    "ai_integration": "AI Integration",
    "documentation_references": "Documentation References",
    "architecture": "Architecture",
    "implementation_details": "Implementation Details",
    "build_run": "Build & Run",
    "test": "Test",
    "config_environment": "Configuration & Environment",
    "deployment_operations": "Deployment & Operations",
    "project_management": "Project Management",
    "development_process": "Development Process",
    "performance": "Performance",
    "security": "Security",
    "ui_ux": "UI/UX",
    "maintainability": "Maintainability",
    "debugging": "Debugging",
}


def normalize_gt_label(label: str) -> List[str]:
    """Map a human label string (from ground truth CSV) to one or more canonical keys.
    Uses keyword matching and returns a list (often length 0 or 1).
    """
    if not isinstance(label, str) or not label.strip() or label.strip().lower() in {"nan", "#n/a"}:
        return []
    s = label.lower()
    mapped = []
    if "overview" in s:
        mapped.append("system_overview")

    # Tokenize into whole-word tokens to avoid matching substrings like
    # the 'ai' inside 'maintainability'. Use simple regex to capture words.
    tokens = re.findall(r"\b[a-z0-9]+\b", s)
    if any(t in tokens for t in ("ai", "claude", "copilot", "agent", "bot")):
        mapped.append("ai_integration")
    if "documentation" in s:
        mapped.append("documentation_references")
    if "architect" in s or "project structure" in s or "project layout" in s:
        mapped.append("architecture")
    if "implement" in s or "code style" in s or "coding" in s or "convention" in s or "jsdoc" in s or "typed" in s:
        mapped.append("implementation_details")
    if "build" in s or "run" in s or "npm" in s or "make" in s or "docker" in s or "compile" in s:
        mapped.append("build_run")
    if "test" in s or "pytest" in s or "vitest" in s or "unittest" in s:
        mapped.append("test")
    if "config" in s or "environment" in s or "env" in s or "docker" in s and "env" in s:
        mapped.append("config_environment")
    if "deploy" in s or "ci" in s or "cd" in s or "cicd" in s or "ops" in s or "deployment" in s:
        mapped.append("deployment_operations")
    if "project management" in s or "backlog" in s or "roadmap" in s:
        mapped.append("project_management")
    if "development process" in s or "commit" in s or "pull request" in s or "conventional commit" in s:
        mapped.append("development_process")
    if "perform" in s and "ance" in s or "optimi" in s:
        mapped.append("performance")
    if "security" in s or "permission" in s or "auth" in s:
        mapped.append("security")
    if "ui" in s and "ux" in s:
        mapped.append("ui_ux")
    # Handle common spellings and variants for 'maintainability'
    if any(sub in s for sub in ("maintain", "maintan", "maintenance", "maintainab", "maintainabil")) or "stable interface" in s:
        mapped.append("maintainability")
    if "debug" in s or "trace" in s or "stacktrace" in s:
        mapped.append("debugging")

    # remove duplicates while preserving order
    seen = set()
    out = []
    for x in mapped:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def parse_prediction_cell(cell) -> List[str]:
    """Parse the prediction 'type' cell which should be a list-like string.
    Accepts a Python-list-like string (e.g. "['a','b']") or a JSON array string.
    """
    if not isinstance(cell, str):
        return []
    cell = cell.strip()
    if not cell:
        return []
    # Try JSON first
    try:
        parsed = json.loads(cell)
        if isinstance(parsed, list):
            return [p for p in parsed if isinstance(p, str)]
    except Exception:
        pass
    # Fallback to python literal
    try:
        parsed = ast.literal_eval(cell)
        if isinstance(parsed, (list, tuple)):
            return [p for p in parsed if isinstance(p, str)]
    except Exception:
        pass
    # If it's a comma-separated string
    if "," in cell:
        return [c.strip().strip("'\"") for c in cell.split(",") if c.strip()]
    # Single token
    return [cell.strip().strip("'\"")]


def find_id_column(df: pd.DataFrame) -> str:
    candidates = [c for c in ["ID", "Id", "id", "#", "Unnamed: 0"] if c in df.columns]
    return candidates[0] if candidates else df.columns[0]


def main():
    folder = Path(__file__).parent
    gt_path = folder / "final_am_classification_2.csv"
    pred_path = folder / "gpt_5_file_classifications.csv"

    if not gt_path.exists():
        raise SystemExit(f"Ground truth file not found: {gt_path}")
    if not pred_path.exists():
        raise SystemExit(f"Predictions file not found: {pred_path}")

    df_gt = pd.read_csv(gt_path)
    df_pred = pd.read_csv(pred_path)

    id_gt = find_id_column(df_gt)
    id_pred = find_id_column(df_pred)
    print(f"Using id columns: ground_truth='{id_gt}', predictions='{id_pred}'")

    # find label columns in ground truth
    label_cols = [c for c in df_gt.columns if c.lower().startswith("label")]
    if not label_cols:
        # fallback: any column that contains 'label' case-insensitive
        label_cols = [c for c in df_gt.columns if "label" in c.lower()]
    if not label_cols:
        raise SystemExit("No label columns found in ground truth CSV")

    # Build ground truth multilabel list per row
    gt_map = {}
    for _, r in df_gt.iterrows():
        row_id = str(r[id_gt])
        labels = []
        for c in label_cols:
            val = r.get(c, "")
            if pd.isna(val):
                continue
            mapped = normalize_gt_label(str(val))
            labels.extend(mapped)
        # dedupe
        gt_map[row_id] = sorted(set(labels))

    # Parse predictions
    pred_map = {}
    if "type" not in df_pred.columns and "types" not in df_pred.columns:
        raise SystemExit("Predictions file must contain a 'type' column with predicted labels")
    type_col = "type" if "type" in df_pred.columns else "types"
    for _, r in df_pred.iterrows():
        row_id = str(r[id_pred])
        cell = r.get(type_col, "")
        parsed = parse_prediction_cell(cell)
        # normalize keys: assume model outputs canonical keys; lowercase them
        parsed_norm = [p.strip() for p in parsed if p]
        pred_map[row_id] = parsed_norm

    # Align rows that are present in both
    common_ids = sorted(set(gt_map.keys()) & set(pred_map.keys()))
    if not common_ids:
        raise SystemExit("No overlapping IDs between ground truth and predictions")

    y_true = [gt_map[r] for r in common_ids]
    y_pred = [pred_map[r] for r in common_ids]

    mlb = MultiLabelBinarizer(classes=LABEL_KEYS)
    Y_true = mlb.fit_transform(y_true)
    Y_pred = mlb.transform(y_pred)

    report = classification_report(Y_true, Y_pred, target_names=[DISPLAY_NAMES[k] for k in mlb.classes_], output_dict=True, zero_division=0)

    # Save report
    out_json = folder / "classification_report.json"
    out_txt = folder / "classification_report.txt"
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Print human readable report
    with out_txt.open("w", encoding="utf-8") as f:
        header = f"Classification report for {len(common_ids)} examples\n"
        print(header)
        f.write(header)
        # pretty-print per-label
        for label in mlb.classes_:
            name = DISPLAY_NAMES[label]
            metrics = report.get(name, {})
            line = f"{name}: precision={metrics.get('precision',0):.4f} recall={metrics.get('recall',0):.4f} f1={metrics.get('f1-score',0):.4f} support={metrics.get('support',0)}\n"
            print(line, end="")
            f.write(line)
        # macro/micro averages
        for avg in ("micro avg", "macro avg", "weighted avg"):
            if avg in report:
                m = report[avg]
                line = f"{avg}: precision={m.get('precision',0):.4f} recall={m.get('recall',0):.4f} f1={m.get('f1-score',0):.4f} support={m.get('support',0)}\n"
                print(line, end="")
                f.write(line)

    print(f"Saved JSON report to: {out_json}\nSaved text report to: {out_txt}")


if __name__ == "__main__":
    main()
import pandas as pd
import numpy as np
import ast # To safely evaluate the string representation of the list

def measure_accuracy(predicted_file: str, ground_truth_file: str, common_id_column: str):
    """
    Measures classification accuracy with detailed multi-label metrics,
    including overall dataset-wide micro-averaged scores.
    """
    try:
        df_predicted = pd.read_csv(predicted_file)
        df_ground_truth = pd.read_csv(ground_truth_file)
    except FileNotFoundError as e:
        print(f"Error: {e}. Please ensure file paths are correct.")
        return

    # --- Prepare Ground Truth Labels ---
    label_cols = [col for col in df_ground_truth.columns if col.startswith('Label')]
    df_ground_truth['manual_labels'] = df_ground_truth[label_cols].apply(
        lambda row: [str(label).lower().replace(' ', '_') for label in row if pd.notna(label)],
        axis=1
    )
    df_ground_truth_processed = df_ground_truth[[common_id_column, 'manual_labels']]

    # --- Prepare Predicted Labels ---
    df_predicted['predicted_labels'] = df_predicted['type'].apply(ast.literal_eval)

    # --- Merging Data ---
    df_merged = pd.merge(
        df_predicted,
        df_ground_truth_processed,
        on=common_id_column,
        how='inner'
    )

    if df_merged.empty:
        print(f"Error: No matching entries found between files using the column '{common_id_column}'.")
        return

    # --- Calculate Metrics for Each Row & Aggregate Totals ---
    results = []
    total_true_positives = 0
    total_false_positives = 0
    total_false_negatives = 0

    for _, row in df_merged.iterrows():
        predicted_set = set(row['predicted_labels'])
        manual_set = set(row['manual_labels'])

        intersection = len(predicted_set.intersection(manual_set))
        union = len(predicted_set.union(manual_set))

        tp = intersection
        fp = len(predicted_set) - tp
        fn = len(manual_set) - tp

        # Add to the dataset-wide totals
        total_true_positives += tp
        total_false_positives += fp
        total_false_negatives += fn

        # Per-item metrics (for averaging later)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        jaccard = tp / union if union > 0 else 0.0

        results.append({
            'precision': precision,
            'recall': recall,
            'jaccard_score': jaccard,
            'overlap_correct': intersection > 0
        })

    df_results = pd.DataFrame(results)

    # --- Calculate Overall Dataset Metrics (Micro Averages) ---
    # This pools all predictions together before scoring.

    # This is the metric you asked for: Correct Predictions / Total Predictions
    micro_precision = total_true_positives / (total_true_positives + total_false_positives) if (total_true_positives + total_false_positives) > 0 else 0.0
    
    # For context, here are the other micro-averaged scores
    micro_recall = total_true_positives / (total_true_positives + total_false_negatives) if (total_true_positives + total_false_negatives) > 0 else 0.0
    micro_f1 = 2 * (micro_precision * micro_recall) / (micro_precision + micro_recall) if (micro_precision + micro_recall) > 0 else 0.0


    # --- Print Summary ---
    print(f"--- Multi-Label Classification Results ---")
    print(f"Total items compared: {len(df_results)}\n")

    # --- Per-Item Average Metrics (Macro Averages) ---
    # Calculates the metric for each item, then averages those scores.
    print("--- Per-Item Average Metrics (Macro Averages) ---")
    print(f"Overlap Accuracy (at least one label matched): {df_results['overlap_correct'].mean():.2%}")
    print(f"Average Precision: {df_results['precision'].mean():.2%}")
    print(f"Average Recall: {df_results['recall'].mean():.2%}")
    print(f"Average Jaccard Score: {df_results['jaccard_score'].mean():.2%}\n")

    # --- Overall Dataset Metrics (Micro Averages) ---
    # Pools all individual predictions together first, then calculates the metric.
    print("--- Overall Dataset Metrics (Micro Averages) ---")
    print(f"Percentage of Correct Predictions (Micro Precision): {micro_precision:.2%}")
    print(f"  (Calculated as: {total_true_positives} correct labels / {total_true_positives + total_false_positives} total predicted labels)\n")
    print(f"Percentage of Found Labels (Micro Recall): {micro_recall:.2%}")
    print(f"Harmonic Mean of Precision & Recall (Micro F1-Score): {micro_f1:.2%}")



if __name__ == '__main__':
    # !!! IMPORTANT: Please update these file paths and the ID column name !!!
    gpt_results_csv = "gpt_4_file_classifications.csv"
    manual_labels_csv = "manual_classification_am.csv"

    # This ID must exist in both files to link a prediction to its ground truth
    # Based on your image, this might be 'commit_sha'
    common_identifier = 'ID' 

    measure_accuracy(gpt_results_csv, manual_labels_csv, common_identifier)