#!/usr/bin/env python3
"""Produce a per-sample comparison between ground truth and model predictions."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.utils.paths import DERIVED_CLASSIFICATION_DIR, ensure_dir
from measure_accuracy import LABEL_KEYS, find_id_column, normalize_gt_label, parse_prediction_cell


def semicolon_join(labels: List[str]) -> str:
    return ";".join(sorted(labels))


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main():
    gt_path = DERIVED_CLASSIFICATION_DIR / "inputs" / "final_am_classification_3.csv"
    pred_path = DERIVED_CLASSIFICATION_DIR / "inputs" / "gpt_5_file_classifications.csv"

    if not gt_path.exists() or not pred_path.exists():
        raise SystemExit("Ground truth or predictions file missing in datasets/derived/classification/inputs")

    df_gt = pd.read_csv(gt_path, dtype=str).fillna("")
    df_pred = pd.read_csv(pred_path, dtype=str).fillna("")

    id_gt = find_id_column(df_gt)
    id_pred = find_id_column(df_pred)

    label_cols = [column for column in df_gt.columns if column.lower().startswith("label")]
    if not label_cols:
        label_cols = [column for column in df_gt.columns if "label" in column.lower()]

    gt_map = {}
    for _, row in df_gt.iterrows():
        row_id = str(row[id_gt])
        raw_vals = [str(row.get(column, "")).strip() for column in label_cols if str(row.get(column, "")).strip()]
        canonical = []
        for value in raw_vals:
            canonical.extend(normalize_gt_label(value))
        gt_map[row_id] = {"gt_raw": ";".join(raw_vals), "gt_canonical": sorted(set(canonical))}

    if "type" not in df_pred.columns and "types" not in df_pred.columns:
        raise SystemExit("Predictions file must contain a 'type' column")
    type_col = "type" if "type" in df_pred.columns else "types"

    pred_map = {}
    for _, row in df_pred.iterrows():
        row_id = str(row[id_pred])
        parsed = [value.strip() for value in parse_prediction_cell(str(row.get(type_col, ""))) if value]
        normalized = []
        for token in parsed:
            lowered = token.lower()
            if lowered in LABEL_KEYS:
                normalized.append(lowered)
                continue
            mapped = normalize_gt_label(token)
            if mapped:
                normalized.extend(mapped)
                continue
            if "maintan" in lowered:
                normalized.append("maintainability")
                continue
            normalized.append(lowered)
        pred_map[row_id] = {"pred_raw": str(row.get(type_col, "")), "pred_canonical": sorted(set(normalized))}

    common_ids = sorted(set(gt_map.keys()) & set(pred_map.keys()))
    rows = []
    for row_id in common_ids:
        gt_info = gt_map[row_id]
        pred_info = pred_map[row_id]
        gt_set = set(gt_info["gt_canonical"])
        pred_set = set(pred_info["pred_canonical"])
        rows.append(
            {
                "id": row_id,
                "gt_raw": gt_info["gt_raw"],
                "gt_canonical": semicolon_join(gt_info["gt_canonical"]),
                "pred_raw": pred_info["pred_raw"],
                "pred_canonical": semicolon_join(pred_info["pred_canonical"]),
                "exact_match": gt_set == pred_set,
                "jaccard": round(jaccard(gt_set, pred_set), 4),
                "missing": ";".join(sorted(gt_set - pred_set)),
                "extra": ";".join(sorted(pred_set - gt_set)),
            }
        )

    results_dir = DERIVED_CLASSIFICATION_DIR / "results"
    ensure_dir(results_dir)
    out_file = results_dir / "per_sample_comparison.csv"
    pd.DataFrame(rows).to_csv(out_file, index=False)
    print(f"Wrote per-sample comparison to: {out_file} (rows={len(rows)})")


if __name__ == "__main__":
    main()
