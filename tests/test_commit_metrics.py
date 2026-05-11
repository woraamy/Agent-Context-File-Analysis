"""Smoke test helper for commit readability metrics."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_analysis.utils.readability import ReadabilityMetrics

# Sample patch content from a real commit
sample_patch = """@@ -0,0 +1,132 @@
+# CLAUDE.md
+
+This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
+
+## Project Overview
+
+This is a macOS menu bar Electron application that monitors Claude Code usage in real-time.
+
+## Essential Commands
+
+### Development
+```bash
+npm run electron-dev  # Start with hot reload (recommended for development)
+npm run dev           # Build frontend only in watch mode
+npm start            # Start built app
+```"""

sample_patch_with_deletions = """@@ -15,7 +15,8 @@ def process_data():
-    # Old implementation
-    result = old_function(data)
-    return result
+    # New improved implementation
+    result = new_function(data)
+    print("Processing complete")
+    return result"""

print("="*80)
print("Testing Commit Metrics Calculation")
print("="*80)

# Test 1: Extract added lines
print("\n1. Testing extraction of ADDED lines (+)")
print("-" * 40)
added_text = ReadabilityMetrics.extract_patch_lines(sample_patch, '+')
print(f"Extracted text:\n{added_text[:200]}...")
print(f"\nWord count: {ReadabilityMetrics.calculate_length_of_words(added_text)}")
print(f"Complexity: {ReadabilityMetrics.calculate_complexity_score(added_text)}")

# Test 2: Extract deleted lines (should be empty for this patch)
print("\n2. Testing extraction of DELETED lines (-) from patch with only additions")
print("-" * 40)
deleted_text = ReadabilityMetrics.extract_patch_lines(sample_patch, '-')
print(f"Extracted text: '{deleted_text}'")
print(f"Word count: {ReadabilityMetrics.calculate_length_of_words(deleted_text)}")
print(f"Complexity: {ReadabilityMetrics.calculate_complexity_score(deleted_text)}")

# Test 3: Extract from patch with both additions and deletions
print("\n3. Testing patch with both deletions and additions")
print("-" * 40)
deleted_text = ReadabilityMetrics.extract_patch_lines(sample_patch_with_deletions, '-')
added_text = ReadabilityMetrics.extract_patch_lines(sample_patch_with_deletions, '+')

print(f"Deleted text: {deleted_text}")
print(f"  Word count: {ReadabilityMetrics.calculate_length_of_words(deleted_text)}")
print(f"  Complexity: {ReadabilityMetrics.calculate_complexity_score(deleted_text)}")

print(f"\nAdded text: {added_text}")
print(f"  Word count: {ReadabilityMetrics.calculate_length_of_words(added_text)}")
print(f"  Complexity: {ReadabilityMetrics.calculate_complexity_score(added_text)}")

print("\n" + "="*80)
print("✅ Tests complete!")
print("="*80)
