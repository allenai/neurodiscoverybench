#!/usr/bin/env python3
"""
Aggregate evaluated CSVs produced by `eval/eval.py`.

Produces:
- Overall mean and std of `hms_score` (both excluding NaNs and including NaNs in denominator by treating them as zeros).
- Mean score by each `dataset`.
- Mean scores aggregated for datasets classified as "fig" and "text" (based on dataset name containing 'fig' or 'text').

Usage:
    python analyse_scores.py --input path/to/evaluated.csv

Requires: pandas, rich
"""

from __future__ import annotations
import argparse
from pathlib import Path
import math
import sys

import pandas as pd
from rich.console import Console
from rich.table import Table
from rich import box
import numpy as np


def safe_float(x):
    try:
        return float(x)
    except Exception:
        return float("nan")


def compute_overall(df: pd.DataFrame, score_col: str = "hms_score"):
    total = len(df)
    non_null = df[score_col].notna().sum()
    sum_non_null = df[score_col].dropna().sum()
    mean_non_null = df[score_col].dropna().mean()
    # mean counting NaNs in denominator -> treat NaNs as 0 but denominator is total
    mean_incl_nans = sum_non_null / total if total > 0 else float("nan")
    # std (population) among non-null
    std_non_null = df[score_col].dropna().std(ddof=0)
    # std treating NaNs as 0
    std_incl_nans = df[score_col].fillna(0).std(ddof=0)

    return {
        "total_count": int(total),
        "non_null_count": int(non_null),
        "mean_non_null": mean_non_null,
        "mean_including_nans": mean_incl_nans,
        "std_non_null": std_non_null,
        "std_including_nans": std_incl_nans,
    }


def dataset_aggregates(df: pd.DataFrame, score_col: str = "hms_score") -> pd.DataFrame:
    groups = []
    for ds, g in df.groupby("dataset"):
        result = compute_overall(g, score_col)
        groups.append(
            {
                "dataset": ds,
                **result,
            }
        )
    return pd.DataFrame(groups).sort_values("dataset")


def type_aggregates(df: pd.DataFrame, score_col: str = "hms_score") -> pd.DataFrame:
    # classify datasets as 'fig' or 'text' (case-insensitive substring match)
    def classify(name: str) -> str:
        n = (name or "").lower()
        if "fig" in n:
            return "fig"
        # "WMB-raw-no-trace" & all other "text" datasets
        return "text"

    df = df.copy()
    df["__type__"] = df["dataset"].apply(classify)
    groups = []
    for t, g in df.groupby("__type__"):
        result = compute_overall(g, score_col)
        groups.append(
            {
                "type": t,
                **result,
            }
        )
    return pd.DataFrame(groups).sort_values("type")


def fmt(x):
    if pd.isna(x):
        return "NaN"
    if isinstance(x, (int,)):
        return str(x)
    # handle numpy numeric types too
    if isinstance(x, (float, np.floating, np.integer)):
        x_f = float(x)
        if math.isfinite(x_f):
            return f"{x_f:.4f}"
        return str(x_f)
    return str(x)


def print_tables(overall: dict, ds_df: pd.DataFrame, type_df: pd.DataFrame):
    console = Console()

    # Overall
    t = Table(title="Overall HMS Score", box=box.ROUNDED)
    t.add_column("Metric")
    t.add_column("Value (non-NaN)")
    t.add_column("Value (including NaNs as 0 / total)")
    t.add_column("Non-null Count")
    t.add_column("Total Count")

    t.add_row(
        "Mean",
        fmt(overall["mean_non_null"]),
        fmt(overall["mean_including_nans"]),
        str(overall["non_null_count"]),
        str(overall["total_count"]),
    )
    t.add_row(
        "Std (population)",
        fmt(overall["std_non_null"]),
        fmt(overall["std_including_nans"]),
        str(overall["non_null_count"]),
        str(overall["total_count"]),
    )
    console.print(t)

    # By dataset
    t2 = Table(title="By Dataset (hms_score)", box=box.ROUNDED)
    # display names similar to the Overall table
    ds_keys = [
        "dataset",
        "mean_non_null",
        "mean_including_nans",
        "non_null_count",
        "total_count",
        "std_non_null",
        "std_including_nans",
    ]
    ds_display = [
        "dataset",
        "Value (non-NaN)",
        "Value (including NaNs as 0 / total)",
        "Non-null Count",
        "Total Count",
        "Std (non-NaN)",
        "Std (including NaNs)",
    ]
    for name in ds_display:
        t2.add_column(name)
    for _, r in ds_df.iterrows():
        t2.add_row(*(fmt(r[k]) for k in ds_keys))
    console.print(t2)

    # By type (fig/text)
    t3 = Table(title="By Dataset Type (fig / text / other)", box=box.ROUNDED)
    type_keys = [
        "type",
        "mean_non_null",
        "mean_including_nans",
        "non_null_count",
        "total_count",
        "std_non_null",
        "std_including_nans",
    ]
    type_display = [
        "type",
        "Value (non-NaN)",
        "Value (including NaNs as 0 / total)",
        "Non-null Count",
        "Total Count",
        "Std (non-NaN)",
        "Std (including NaNs)",
    ]
    for name in type_display:
        t3.add_column(name)
    for _, r in type_df.iterrows():
        t3.add_row(*(fmt(r[k]) for k in type_keys))
    console.print(t3)


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--input", "-i", required=True, type=Path, help="Path to evaluated CSV"
    )
    p.add_argument(
        "--score-col",
        default="hms_score",
        help="Score column name (default: hms_score)",
    )
    p.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Optional: write dataset-level aggregates to CSV",
    )
    args = p.parse_args()

    if not args.input.exists():
        print(f"Input file not found: {args.input}")
        sys.exit(2)

    df = pd.read_csv(args.input)

    if args.score_col not in df.columns:
        print(
            f"Score column '{args.score_col}' not found in CSV. Columns: {df.columns.tolist()}"
        )
        sys.exit(2)

    overall = compute_overall(df, args.score_col)
    ds_df = dataset_aggregates(df, args.score_col)
    type_df = type_aggregates(df, args.score_col)

    print_tables(overall, ds_df, type_df)

    if args.output_csv:
        ds_df.to_csv(args.output_csv, index=False)
        print(f"Wrote dataset-level aggregates to {args.output_csv}")


if __name__ == "__main__":
    main()
