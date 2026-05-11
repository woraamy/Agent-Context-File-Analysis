#!/usr/bin/env python3
"""Compute multilabel classification metrics from the derived classification inputs."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import List

import pandas as pd
from sklearn.metrics import classification_report
from sklearn.preprocessing import MultiLabelBinarizer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.utils.paths import DERIVED_CLASSIFICATION_DIR, ensure_dir


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

INPUTS_DIR = DERIVED_CLASSIFICATION_DIR / "inputs"
RESULTS_DIR = DERIVED_CLASSIFICATION_DIR / "results"


def normalize_gt_label(label: str) -> List[str]:
    """Map a human label string from the ground-truth CSV to canonical keys."""
    if not isinstance(label, str) or not label.strip() or label.strip().lower() in {"nan", "#n/a"}:
        return []

    s = label.lower()
    mapped: list[str] = []
    if "overview" in s:
        mapped.append("system_overview")

    tokens = re.findall(r"\b[a-z0-9]+\b", s)
    if any(token in tokens for token in ("ai", "claude", "copilot", "agent", "bot")):
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
    if "config" in s or "environment" in s or "env" in s:
        mapped.append("config_environment")
    if "deploy" in s or "ci" in s or "cd" in s or "cicd" in s or "ops" in s or "deployment" in s:
        mapped.append("deployment_operations")
    if "project management" in s or "backlog" in s or "roadmap" in s:
        mapped.append("project_management")
    if "development process" in s or "commit" in s or "pull request" in s or "conventional commit" in s:
        mapped.append("development_process")
    if ("perform" in s and "ance" in s) or "optimi" in s:
        mapped.append("performance")
    if "security" in s or "permission" in s or "auth" in s:
        mapped.append("security")
    if "ui" in s and "ux" in s:
        mapped.append("ui_ux")
    if any(sub in s for sub in ("maintain", "maintan", "maintenance", "maintainab", "maintainabil")):
        mapped.append("maintainability")
    if "debug" in s or "trace" in s or "stacktrace" in s:
        mapped.append("debugging")

    seen = set()
    deduped = []
    for item in mapped:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def parse_prediction_cell(cell) -> List[str]:
    """Parse prediction cells that may be JSON, Python literals, or comma-separated."""
    if not isinstance(cell, str):
        return []

    cell = cell.strip()
    if not cell:
        return []

    try:
        parsed = json.loads(cell)
        if isinstance(parsed, list):
            return [value for value in parsed if isinstance(value, str)]
    except Exception:
        pass

    try:
        parsed = ast.literal_eval(cell)
        if isinstance(parsed, (list, tuple)):
            return [value for value in parsed if isinstance(value, str)]
    except Exception:
        pass

    if "," in cell:
        return [value.strip().strip("'\"") for value in cell.split(",") if value.strip()]
    return [cell.strip().strip("'\"")]


def find_id_column(df: pd.DataFrame) -> str:
    candidates = [column for column in ["ID", "Id", "id", "#", "Unnamed: 0"] if column in df.columns]
    return candidates[0] if candidates else df.columns[0]


def main():
    gt_path = INPUTS_DIR / "final_am_classification_3.csv"
    pred_path = INPUTS_DIR / "gpt_5_file_classifications.csv"

    if not gt_path.exists():
        raise SystemExit(f"Ground truth file not found: {gt_path}")
    if not pred_path.exists():
        raise SystemExit(f"Predictions file not found: {pred_path}")

    df_gt = pd.read_csv(gt_path)
    df_pred = pd.read_csv(pred_path)

    id_gt = find_id_column(df_gt)
    id_pred = find_id_column(df_pred)
    print(f"Using id columns: ground_truth='{id_gt}', predictions='{id_pred}'")

    label_cols = [column for column in df_gt.columns if column.lower().startswith("label")]
    if not label_cols:
        label_cols = [column for column in df_gt.columns if "label" in column.lower()]
    if not label_cols:
        raise SystemExit("No label columns found in ground truth CSV")

    gt_map = {}
    for _, row in df_gt.iterrows():
        row_id = str(row[id_gt])
        labels = []
        for column in label_cols:
            value = row.get(column, "")
            if pd.isna(value):
                continue
            labels.extend(normalize_gt_label(str(value)))
        gt_map[row_id] = sorted(set(labels))

    pred_map = {}
    if "type" not in df_pred.columns and "types" not in df_pred.columns:
        raise SystemExit("Predictions file must contain a 'type' or 'types' column")
    type_col = "type" if "type" in df_pred.columns else "types"
    for _, row in df_pred.iterrows():
        row_id = str(row[id_pred])
        parsed = parse_prediction_cell(row.get(type_col, ""))
        pred_map[row_id] = [value.strip() for value in parsed if value]

    common_ids = sorted(set(gt_map.keys()) & set(pred_map.keys()))
    if not common_ids:
        raise SystemExit("No overlapping IDs between ground truth and predictions")

    y_true = [gt_map[row_id] for row_id in common_ids]
    y_pred = [pred_map[row_id] for row_id in common_ids]

    mlb = MultiLabelBinarizer(classes=LABEL_KEYS)
    y_true_bin = mlb.fit_transform(y_true)
    y_pred_bin = mlb.transform(y_pred)

    report = classification_report(
        y_true_bin,
        y_pred_bin,
        target_names=[DISPLAY_NAMES[key] for key in mlb.classes_],
        output_dict=True,
        zero_division=0,
    )

    ensure_dir(RESULTS_DIR)
    out_json = RESULTS_DIR / "classification_report.json"
    out_txt = RESULTS_DIR / "classification_report.txt"
    with out_json.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    with out_txt.open("w", encoding="utf-8") as handle:
        header = f"Classification report for {len(common_ids)} examples\n"
        print(header)
        handle.write(header)
        for label in mlb.classes_:
            name = DISPLAY_NAMES[label]
            metrics = report.get(name, {})
            line = (
                f"{name}: precision={metrics.get('precision', 0):.4f} "
                f"recall={metrics.get('recall', 0):.4f} "
                f"f1={metrics.get('f1-score', 0):.4f} "
                f"support={metrics.get('support', 0)}\n"
            )
            print(line, end="")
            handle.write(line)

        for average_name in ("micro avg", "macro avg", "weighted avg"):
            if average_name in report:
                metrics = report[average_name]
                line = (
                    f"{average_name}: precision={metrics.get('precision', 0):.4f} "
                    f"recall={metrics.get('recall', 0):.4f} "
                    f"f1={metrics.get('f1-score', 0):.4f} "
                    f"support={metrics.get('support', 0)}\n"
                )
                print(line, end="")
                handle.write(line)

    print(f"Saved JSON report to: {out_json}\nSaved text report to: {out_txt}")


if __name__ == "__main__":
    main()
