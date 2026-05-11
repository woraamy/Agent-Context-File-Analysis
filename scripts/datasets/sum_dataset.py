import pandas as pd
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import get_manifest_dataset
from manifest_analysis.utils.paths import DERIVED_STATISTICS_DIR, ensure_dir

def load_dataset(path: Path, source_label: str) -> pd.DataFrame:
    if not path.exists():
        print(f"Warning: dataset file not found: {path}")
        return pd.DataFrame()
    df = pd.read_csv(path, dtype=str).fillna("")
    df = df.copy()
    df["_source"] = source_label
    # normalize repo identifier
    if "repository_owner" in df.columns and "repository_name" in df.columns:
        df["repo_merged"] = df["repository_owner"].astype(str) + "/" + df["repository_name"].astype(str)
    else:
        # try repository_url or file_url
        if "repository_url" in df.columns:
            df["repo_merged"] = df["repository_url"].astype(str)
        elif "file_url" in df.columns:
            # best-effort parse owner/repo from file_url
            def parse_repo(u: str) -> str:
                try:
                    parts = u.split("github.com/")[-1].split("/")
                    return parts[0] + "/" + parts[1]
                except Exception:
                    return u
            df["repo_merged"] = df["file_url"].astype(str).apply(parse_repo)
        else:
            df["repo_merged"] = ""
    return df


def main():
    agents_df = load_dataset(get_manifest_dataset("agents").original_path, "agents")
    claude_df = load_dataset(get_manifest_dataset("claude").original_path, "claude")
    copilot_df = load_dataset(get_manifest_dataset("copilot-instructions").original_path, "copilot-instructions")

    all_df = pd.concat([agents_df, claude_df, copilot_df], ignore_index=True, sort=False)

    # Basic counts
    total_files = len(all_df)
    unique_repos = all_df["repo_merged"].replace("", pd.NA).dropna().nunique()
    print(f"Total files across datasets: {total_files}")
    print(f"Total unique repositories referenced: {unique_repos}")

    # Per-dataset counts
    for src, df in [("agents", agents_df), ("claude", claude_df), ("copilot-instructions", copilot_df)]:
        n = len(df)
        unique = df["repo_merged"].replace("", pd.NA).dropna().nunique()
        print(f"{src}: files={n}, unique_repos={unique}")

    # Per-repo aggregation: how many files per repo, and which sources they appear in
    grouped = all_df.groupby("repo_merged").agg(
        total_files=("repo_merged", "count"),
        unique_sources=("_source", lambda s: ";".join(sorted(set([x for x in s if x])))),
    ).reset_index()

    # Count number of distinct sources per repo
    grouped["num_sources"] = grouped["unique_sources"].apply(lambda s: 0 if not s else len(s.split(";")))

    # Flag repos that have multiple agent files (more than one row) or appear in multiple sources
    grouped["multiple_files"] = grouped["total_files"] > 1
    grouped["multiple_sources"] = grouped["num_sources"] > 1

    # Save per-repo summary CSV
    ensure_dir(DERIVED_STATISTICS_DIR)
    out_path = DERIVED_STATISTICS_DIR / "repo_file_counts.csv"
    grouped.to_csv(out_path, index=False)
    print(f"Saved per-repo summary to: {out_path}")

    # Print top repos with multiple files or multiple sources
    multi = grouped[(grouped["multiple_files"]) | (grouped["multiple_sources"])].sort_values(by=["total_files"], ascending=False)
    print(f"\nRepositories with multiple agent files or spanning multiple datasets: {len(multi)}")
    print(multi.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
