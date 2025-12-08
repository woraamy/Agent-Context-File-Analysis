"""Compatibility shim for per_sample_comparison.

This module was moved; keep a small shim to avoid import errors.
"""

def compare_samples(*args, **kwargs):
    raise NotImplementedError("per_sample_comparison has been moved; implement or import from new location.")

__all__ = ["compare_samples"]






#!/usr/bin/env python3
"""Produce per-sample CSV comparing ground-truth and model predictions.

Outputs `per_sample_comparison.csv` with columns:
 - id: identifier column
 - gt_raw: concatenated original GT label cells
 - gt_canonical: canonical mapped labels (semicolon-separated)
 - pred_raw: original prediction cell
 - pred_canonical: predicted labels (semicolon-separated)
 - exact_match: whether sets are identical
 - jaccard: intersection/union
 - missing: gt - pred
 - extra: pred - gt

Usage: python3 per_sample_comparison.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pandas as pd

# Reuse parsing helpers from measure_accuracy
from measure_accuracy import normalize_gt_label, parse_prediction_cell, find_id_column, LABEL_KEYS


def semicolon_join(labels: List[str]) -> str:
    return ";".join(sorted(labels))


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a and b or (a and not b):
        return 0.0
    inter = a & b
    uni = a | b
    return len(inter) / len(uni)


def main():
    folder = Path(__file__).parent
    gt_path = folder / "final_am_classification.csv"
    pred_path = folder / "gpt_5_file_classifications.csv"

    if not gt_path.exists() or not pred_path.exists():
        raise SystemExit("Ground truth or predictions file missing in RQ5 folder")

    df_gt = pd.read_csv(gt_path, dtype=str).fillna("")
    df_pred = pd.read_csv(pred_path, dtype=str).fillna("")

    id_gt = find_id_column(df_gt)
    id_pred = find_id_column(df_pred)

    # label columns in GT
    label_cols = [c for c in df_gt.columns if c.lower().startswith("label")]
    if not label_cols:
        label_cols = [c for c in df_gt.columns if "label" in c.lower()]

    # build GT map of raw labels and canonical
    rows = []
    gt_map = {}
    for _, r in df_gt.iterrows():
        row_id = str(r[id_gt])
        raw_vals = [str(r.get(c, "")).strip() for c in label_cols if str(r.get(c, "")).strip()]
        gt_raw = ";".join(raw_vals)
        # Map each raw label cell to canonical set (if multi-label per cell, we map per cell too)
        canonical = []
        for v in raw_vals:
            canonical.extend(normalize_gt_label(v))
        canonical = sorted(set(canonical))
        gt_map[row_id] = {"gt_raw": gt_raw, "gt_canonical": canonical}

    # parse predictions
    if "type" not in df_pred.columns and "types" not in df_pred.columns:
        raise SystemExit("Predictions file must contain a 'type' column")
    type_col = "type" if "type" in df_pred.columns else "types"
    pred_map = {}
    for _, r in df_pred.iterrows():
        row_id = str(r[id_pred])
        cell = str(r.get(type_col, ""))
        parsed = parse_prediction_cell(cell)
        parsed = [p.strip() for p in parsed if p]

        # Normalize predicted tokens to canonical keys where possible.
        normalized = []
        for token in parsed:
            low = token.strip().lower()
            # If the model already returned a canonical key, keep it
            if low in LABEL_KEYS:
                normalized.append(low)
                continue

            # Use the GT normalizer as a fallback to map display names / misspellings
            mapped = normalize_gt_label(token)
            if mapped:
                normalized.extend(mapped)
                continue

            # Special-case common misspelling (Maintanability -> Maintainability)
            if "maintan" in low:
                normalized.append("maintainability")
                continue

            # Otherwise, keep the raw token (lowercased) so it's visible in the CSV
            normalized.append(low)

        pred_map[row_id] = {"pred_raw": cell, "pred_canonical": sorted(set(normalized))}

    # combine
    common = sorted(set(gt_map.keys()) & set(pred_map.keys()))
    out_rows = []
    for rid in common:
        gt_info = gt_map[rid]
        pred_info = pred_map[rid]
        gt_set = set(gt_info["gt_canonical"])
        pred_set = set(pred_info["pred_canonical"])
        inter = gt_set & pred_set
        miss = sorted(gt_set - pred_set)
        extra = sorted(pred_set - gt_set)
        j = jaccard(gt_set, pred_set)
        exact = gt_set == pred_set
        out_rows.append(
            {
                "id": rid,
                "gt_raw": gt_info["gt_raw"],
                "gt_canonical": semicolon_join(gt_info["gt_canonical"]),
                "pred_raw": pred_info["pred_raw"],
                "pred_canonical": semicolon_join(pred_info["pred_canonical"]),
                "exact_match": exact,
                "jaccard": round(j, 4),
                "missing": ";".join(miss),
                "extra": ";".join(extra),
            }
        )

    out_df = pd.DataFrame(out_rows)
    out_file = folder / "per_sample_comparison.csv"
    out_df.to_csv(out_file, index=False)
    print(f"Wrote per-sample comparison to: {out_file} (rows={len(out_df)})")


if __name__ == "__main__":
    main()
