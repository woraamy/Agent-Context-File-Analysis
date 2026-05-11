import sys
import numpy as np
import pandas as pd
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.datasets.registry import get_manifest_dataset
from manifest_analysis.utils.paths import DERIVED_STATISTICS_DIR, ensure_dir

try:
    from scipy.stats import mannwhitneyu
except Exception:
    mannwhitneyu = None


def cliff_delta(x, y):
    x = np.asarray(x)
    y = np.asarray(y)
    x = x[~np.isnan(x)]
    y = y[~np.isnan(y)]
    n = x.size
    m = y.size
    if n == 0 or m == 0:
        return np.nan
    y_sorted = np.sort(y)
    # For each xi count number of y < xi (less) and number of ties
    less = np.searchsorted(y_sorted, x, side='left')
    right = np.searchsorted(y_sorted, x, side='right')
    equal = right - less
    # contribution per xi: less - greater, where greater = m - less - equal
    contrib = less - (m - less - equal)
    delta = contrib.sum() / (n * m)
    return float(delta)


def interpret_cliff_delta(d):
    try:
        val = abs(float(d))
    except (TypeError, ValueError):
        return 'NA'
    if np.isnan(val):
        return 'NA'
    if val < 0.147:
        return 'negligible'
    if val < 0.33:
        return 'small'
    if val < 0.474:
        return 'medium'
    return 'large'


def load_post_adoption(path, tool_name=None):
    df = pd.read_csv(path)
    df = df[df['period'] == 'Post-Adoption']
    if tool_name is not None:
        mask_tool = df['ai_tool'].fillna('').str.contains(tool_name, na=False)
        mask_mixed = df['ai_tool'].fillna('').str.contains('/', na=False)
        df = df[mask_tool & (~mask_mixed)]
    return df


def describe_series(s):
    s = pd.to_numeric(s, errors='coerce')
    return {
        'count': int(s.count()),
        'mean': float(s.mean()) if s.count() else np.nan,
        'median': float(s.median()) if s.count() else np.nan,
        'std': float(s.std()) if s.count() else np.nan,
    }


def pairwise_tests(a, b, label_a, label_b):
    a = np.array(a.dropna())
    b = np.array(b.dropna())
    res = {'group_a': label_a, 'group_b': label_b, 'n_a': a.size, 'n_b': b.size}
    res['cliff_delta'] = cliff_delta(a, b)
    res['cliff_effect_size'] = interpret_cliff_delta(res['cliff_delta'])
    if mannwhitneyu is not None and a.size > 0 and b.size > 0:
        try:
            u_stat, p = mannwhitneyu(a, b, alternative='two-sided')
            res['mannwhitney_u'] = float(u_stat)
            res['p_value'] = float(p)
        except TypeError:
            # older scipy: no alternative param
            u_stat, p = mannwhitneyu(a, b)
            res['mannwhitney_u'] = float(u_stat)
            res['p_value'] = float(p)
    else:
        res['mannwhitney_u'] = np.nan
        res['p_value'] = np.nan
    return res


def main():
    files = {
        'copilot': get_manifest_dataset('copilot-instructions').tool_only_adoption_path,
        'claude': get_manifest_dataset('claude').tool_only_adoption_path,
        'codex': get_manifest_dataset('agents').tool_only_adoption_path,
    }

    dfs = {}
    for k, p in files.items():
        if not p.exists():
            print(f"Missing file: {p}")
            sys.exit(1)
        dfs[k] = load_post_adoption(p, tool_name=k.capitalize() if k != 'codex' else 'Codex')

    metrics = ['avg_complexity', 'median_complexity', 'avg_loc', 'median_loc', 'files_changed_count', 'avg_nloc']

    desc = []
    for name, df in dfs.items():
        row = {'tool': name}
        for m in metrics:
            if m in df.columns:
                d = describe_series(df[m])
            else:
                d = {'count': 0, 'mean': np.nan, 'median': np.nan, 'std': np.nan}
            row.update({f'{m}_{k}': v for k, v in d.items()})
        desc.append(row)

    desc_df = pd.DataFrame(desc)
    out_dir = ensure_dir(DERIVED_STATISTICS_DIR)
    desc_df.to_csv(out_dir / 'adoption_descriptives.csv', index=False)

    # Pairwise tests on avg_complexity and avg_loc (per-request "nloc")
    pairs = [('copilot', 'claude'), ('copilot', 'codex'), ('claude', 'codex')]
    compare_metrics = ['avg_complexity', 'avg_loc']
    tests = []
    for metric in compare_metrics:
        for a, b in pairs:
            sa = dfs[a][metric] if metric in dfs[a].columns else pd.Series(dtype=float)
            sb = dfs[b][metric] if metric in dfs[b].columns else pd.Series(dtype=float)
            if sa.empty and sb.empty:
                continue
            result = pairwise_tests(sa, sb, a, b)
            result['metric'] = metric
            tests.append(result)

    tests_df = pd.DataFrame(tests)
    tests_df.to_csv(out_dir / 'adoption_pairwise_tests.csv', index=False)

    # Print concise summary
    print('\nDescriptive summary (saved to statistics/adoption_descriptives.csv)')
    print(desc_df.to_string(index=False))
    print('\nPairwise tests (avg_complexity & avg_loc) saved to statistics/adoption_pairwise_tests.csv')
    print(tests_df.to_string(index=False))


if __name__ == '__main__':
    main()
