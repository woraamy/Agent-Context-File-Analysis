"""Shared helpers for readability comparison scripts."""

from __future__ import annotations

import math
import re
import ssl
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple
from urllib.error import URLError

import nltk
import pandas as pd
import textstat
from readability import Readability
from readability.exceptions import ReadabilityException

from manifest_analysis.datasets.registry import ManifestDataset
from manifest_analysis.utils.paths import PROJECT_ROOT


PY_READABILITY_ENABLED = True
PY_READABILITY_DISABLED_REASON: Optional[str] = None
PY_READABILITY_AVAILABLE: Optional[bool] = None
SSL_CONTEXT_PATCHED = False
SSL_CERT_ERRORS = tuple(
    cls for cls in (getattr(ssl, "SSLCertVerificationError", None), ssl.SSLError) if cls
)

CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
NLTK_DATA_DIR = PROJECT_ROOT / "nltk_data_cache"
NLTK_DATA_DIR.mkdir(exist_ok=True)
if str(NLTK_DATA_DIR) not in nltk.data.path:
    nltk.data.path.append(str(NLTK_DATA_DIR))

REQUIRED_NLTK_RESOURCES: Tuple[Tuple[str, str], ...] = (
    ("tokenizers/punkt", "punkt"),
    ("tokenizers/punkt_tab", "punkt_tab"),
    ("corpora/cmudict", "cmudict"),
)

try:
    ssl._create_default_https_context = ssl._create_unverified_context
    SSL_CONTEXT_PATCHED = True
except Exception:
    pass


def strip_code_blocks(text: Optional[str]) -> str:
    """Remove fenced code blocks from Markdown text."""
    if not text or not isinstance(text, str):
        return ""
    return CODE_BLOCK_RE.sub(" ", text)


def patch_ssl_context() -> bool:
    """Patch SSL verification during NLTK downloads when needed."""
    global SSL_CONTEXT_PATCHED
    if SSL_CONTEXT_PATCHED:
        return False
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
        SSL_CONTEXT_PATCHED = True
        print("    Retrying download with unverified SSL context.")
        return True
    except Exception:
        return False


def download_nltk_package(name: str) -> bool:
    """Download an NLTK package with SSL fallback."""
    try:
        return nltk.download(
            name,
            download_dir=str(NLTK_DATA_DIR),
            quiet=True,
            raise_on_error=True,
        )
    except URLError as err:
        reason = getattr(err, "reason", None)
        if reason and SSL_CERT_ERRORS and isinstance(reason, SSL_CERT_ERRORS):
            if patch_ssl_context():
                try:
                    return nltk.download(
                        name,
                        download_dir=str(NLTK_DATA_DIR),
                        quiet=True,
                        raise_on_error=True,
                    )
                except Exception:
                    return False
        return False
    except Exception:
        return False


def ensure_nltk_resource(resource_path: str, download_name: str) -> bool:
    """Make sure a specific NLTK resource is available locally."""
    try:
        nltk.data.find(resource_path)
        return True
    except LookupError:
        print(f"  Downloading NLTK resource '{download_name}'...")
        if not download_nltk_package(download_name):
            print(f"      Unable to download '{download_name}'.")
            return False
        try:
            nltk.data.find(resource_path)
            return True
        except LookupError:
            print(f"      Resource '{download_name}' still missing after download.")
            return False


def disable_py_readability(reason: str) -> None:
    """Disable py-readability calculations after a fatal dependency failure."""
    global PY_READABILITY_ENABLED, PY_READABILITY_DISABLED_REASON, PY_READABILITY_AVAILABLE
    if not PY_READABILITY_ENABLED:
        return
    PY_READABILITY_ENABLED = False
    PY_READABILITY_AVAILABLE = False
    PY_READABILITY_DISABLED_REASON = reason
    print(
        "  Disabling py-readability-metrics computations due to missing "
        f"dependencies: {reason}"
    )


def ensure_py_readability_dependencies() -> bool:
    """Ensure all NLTK resources exist before running py-readability."""
    global PY_READABILITY_AVAILABLE
    if not PY_READABILITY_ENABLED:
        return False
    if PY_READABILITY_AVAILABLE is True:
        return True
    if PY_READABILITY_AVAILABLE is False:
        return False

    missing = []
    for resource_path, download_name in REQUIRED_NLTK_RESOURCES:
        if not ensure_nltk_resource(resource_path, download_name):
            missing.append(download_name)

    if missing:
        disable_py_readability("Missing NLTK resources: " + ", ".join(sorted(set(missing))))
        PY_READABILITY_AVAILABLE = False
        return False

    PY_READABILITY_AVAILABLE = True
    return True


def safe_float(value: Optional[str]) -> Optional[float]:
    """Convert a value to float if possible, otherwise return None."""
    if value is None or value == "":
        return None
    try:
        number = float(value)
        if math.isnan(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def compute_textstat_score(text: str) -> Optional[float]:
    """Compute Flesch score via textstat."""
    if len(text) < 10:
        return None
    try:
        score = textstat.flesch_reading_ease(text)
        if math.isnan(score):
            return None
        return float(score)
    except Exception:
        return None


def compute_py_readability_score(text: str) -> Optional[float]:
    """Compute Flesch score via py-readability-metrics."""
    if len(text) < 10:
        return None
    if not ensure_py_readability_dependencies():
        return None
    try:
        readability_obj = Readability(text)
        flesch_result = readability_obj.flesch()
        score = getattr(flesch_result, "score", None)
        if score is None or math.isnan(score):
            return None
        return float(score)
    except LookupError as err:
        disable_py_readability(str(err))
        return None
    except (ReadabilityException, ValueError, TypeError):
        return None


def create_fallback_key(
    owner: Optional[str],
    repo: Optional[str],
    file_url: Optional[str],
) -> Optional[str]:
    """Create the legacy key format used across datasets."""
    if not (owner and repo and file_url):
        return None
    return f"{owner}||{repo}||{file_url}"


def build_static_lookup(static_df: pd.DataFrame) -> Dict[str, str]:
    """Create a mapping from file identifiers to static content."""
    lookup: Dict[str, str] = {}
    for _, row in static_df.iterrows():
        static_text = row.get("static_content", "")
        key = row.get("file_composite_key")
        fallback_key = create_fallback_key(
            row.get("repository_owner"),
            row.get("repository_name"),
            row.get("file_url"),
        )

        if key:
            lookup[key] = static_text
        if fallback_key:
            lookup.setdefault(fallback_key, static_text)
    return lookup


def process_dataset(
    dataset: ManifestDataset,
    clean_text: Callable[[Optional[str]], str],
) -> pd.DataFrame:
    """Load, compute, and return the readability comparison for a dataset."""
    original_df = pd.read_csv(dataset.original_path)
    static_df = pd.read_csv(dataset.static_path)
    static_lookup = build_static_lookup(static_df)

    records = []
    missing_content = 0

    for _, row in original_df.iterrows():
        key = row.get("file_composite_key")
        if not key:
            key = create_fallback_key(
                row.get("repository_owner"),
                row.get("repository_name"),
                row.get("file_url"),
            )

        raw_text = static_lookup.get(key or "")
        prepared_text = clean_text(raw_text)

        if not prepared_text:
            missing_content += 1

        records.append(
            {
                "repository_owner": row.get("repository_owner"),
                "repository_name": row.get("repository_name"),
                "repository_url": row.get("repository_url"),
                "original_flesch_score": safe_float(row.get("complexity_score")),
                "textstat_score": compute_textstat_score(prepared_text),
                "py_readability_score": compute_py_readability_score(prepared_text),
            }
        )

    result_df = pd.DataFrame(records)
    print(
        f"Processed {dataset.key} dataset: {len(result_df)} rows "
        f"({missing_content} entries without prepared text)."
    )
    return result_df


def save_dataset(df: pd.DataFrame, path: Path) -> None:
    """Persist the dataframe to disk as CSV."""
    df.to_csv(path, index=False)
    print(f"  Saved {path.relative_to(PROJECT_ROOT)}")
