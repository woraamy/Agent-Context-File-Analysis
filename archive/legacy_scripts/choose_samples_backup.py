import pandas as pd
import os
import math
import requests
import time
from langdetect imp    # --- Phase 0: Load manual_classification_am.csv ---
    print("\n--- � Phase 0: Loading manual_classification_am.csv ---")
    
    same_entries_df = None
    same_entries_count = 0
    same_entries_by_source = {}
    
    if os.path.exists(SAME_ENTRIES_FILE):
        try:
            same_entries_df = pd.read_csv(SAME_ENTRIES_FILE)
            same_entries_count = len(same_entries_df)
            print(f"✅ Loaded {same_entries_count} entries from manual_classification_am.csv")LangDetectException

# --- Configuration ---
AGENT_NAMES = ['agents', 'claude', 'copilot-instructions']
TOTAL_SAMPLE_SIZE = 332
OUTPUT_FILENAME = "../datasets/am_samples.csv"
SAME_ENTRIES_FILE = "../RQ5/manual_classification_am.csv"
RANDOM_STATE = 42  # Ensures the "random" sample is the same every time

# GitHub API configuration
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
if not GITHUB_TOKEN:
    print("⚠️  Warning: GITHUB_TOKEN environment variable not set. Language detection may fail due to rate limits.")
    
HEADERS = {
    "Accept": "application/vnd.github.v3+json"
}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"

# Map agent keys to their canonical, case-insensitive filenames
CANONICAL_FILENAMES = {
    'agents': 'agents.md',
    'claude': 'claude.md',
    'copilot-instructions': 'copilot-instructions.md'
}


# --- Helper Functions ---
def fetch_file_content(owner, repo, file_path, branch='main'):
    """Fetches the raw content of a file from GitHub."""
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
    try:
        response = requests.get(raw_url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            return response.text
        elif response.status_code == 404 and branch == 'main':
            # Try master branch as fallback
            return fetch_file_content(owner, repo, file_path, branch='master')
        else:
            return None
    except Exception as e:
        return None


def is_english(text):
    """Detects if the given text is primarily in English."""
    if not text or len(text.strip()) < 50:
        return False
    try:
        detected_lang = detect(text)
        return detected_lang == 'en'
    except LangDetectException:
        return False


def check_file_is_english(row):
    """Checks if a file is in English by fetching its content."""
    owner = row['repository_owner']
    repo = row['repository_name']
    file_path = row['file_path']
    branch = row.get('branch', 'main')
    
    content = fetch_file_content(owner, repo, file_path, branch)
    if content:
        is_eng = is_english(content)
        return is_eng
    return False


# --- Main Script ---
def proportional_sampler_exact_match():
    """
    1. Loads same_entries.csv files
    2. Calculates proportional samples needed (332 total - same_entries count)
    3. Samples files proportionally based on dataset sizes
    4. Applies English language filter to ALL files (same_entries + new samples)
    5. Replaces non-English files with new samples until all 332 are English
    """

    print("=" * 80)
    print("CREATING AM_SAMPLES WITH LANGUAGE FILTERING")
    print("=" * 80)

    # --- Phase 0: Load same_entries.csv ---
    print("\n--- � Phase 0: Loading same_entries.csv ---")
    
    same_entries_df = None
    same_entries_count = 0
    same_entries_by_source = {}
    
    if os.path.exists(SAME_ENTRIES_FILE):
        try:
            same_entries_df = pd.read_csv(SAME_ENTRIES_FILE)
            same_entries_count = len(same_entries_df)
            print(f"✅ Loaded {same_entries_count} entries from same_entries.csv")
            
            # Count by source_dataset
            if 'source_dataset' in same_entries_df.columns:
                for agent in AGENT_NAMES:
                    count = len(same_entries_df[same_entries_df['source_dataset'] == agent])
                    same_entries_by_source[agent] = count
                    if count > 0:
                        print(f"   - {agent}: {count} files")
        except Exception as e:
            print(f"❌ Error loading same_entries.csv: {e}")
            same_entries_df = None
    else:
        print(f"⚠️  File not found: {SAME_ENTRIES_FILE}")
        print("   Proceeding without same_entries...")
    
    # Calculate how many more samples needed
    remaining_needed = TOTAL_SAMPLE_SIZE - same_entries_count
    print(f"\n📊 Target: {TOTAL_SAMPLE_SIZE} total files")
    print(f"   - From same_entries: {same_entries_count} files")
    print(f"   - Need to sample: {remaining_needed} files")
    
    if remaining_needed <= 0:
        print(f"\n⚠️  same_entries already has {same_entries_count} files (>= {TOTAL_SAMPLE_SIZE})")
        print("   Will use only same_entries and apply language filter...")
        remaining_needed = 0

    # --- Phase 1: Load and Filter Datasets ---
    print(f"\n--- 🔬 Phase 1: Loading Datasets ---")

    file_counts = {}
    filtered_dataframes = {}

    for agent in AGENT_NAMES:
        filename = f"../datasets/{agent}_dataset.csv"
        if not os.path.exists(filename):
            print(f"⚠️  Warning: File '{filename}' not found.")
            file_counts[agent] = 0
            continue

        try:
            df = pd.read_csv(filename)
            
            # Exclude files already in same_entries to avoid duplicates
            # Compare using repository_owner + repository_name + filename (not full file_path)
            if same_entries_df is not None and len(same_entries_df) > 0:
                # Create unique identifiers for comparison
                same_entries_ids = set()
                for _, row in same_entries_df.iterrows():
                    unique_id = f"{row['repository_owner']}/{row['repository_name']}/{row.get('filename', os.path.basename(row['file_path']))}"
                    same_entries_ids.add(unique_id)
                
                # Filter out duplicates
                def is_duplicate(row):
                    unique_id = f"{row['repository_owner']}/{row['repository_name']}/{row.get('filename', os.path.basename(row['file_path']))}"
                    return unique_id in same_entries_ids
                
                mask = ~df.apply(is_duplicate, axis=1)
                df = df[mask].copy()

            print(f"'{agent}': {len(df)} files available (after removing same_entries duplicates)")
            
            file_counts[agent] = len(df)
            filtered_dataframes[agent] = df

        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
            file_counts[agent] = 0

    total_files = sum(file_counts.values())

    if total_files == 0 and remaining_needed > 0:
        print("\n❌ No files available for sampling. Exiting.")
        return

    # --- Phase 2: Calculate Proportional Samples (Correct Method) ---
    print(f"\n--- 📊 Phase 2: Calculating Proportional Sample Sizes ---")
    
    samples_to_take = {}
    
    if remaining_needed > 0:
        print(f"Calculating proportions based on total {TOTAL_SAMPLE_SIZE} files:")
        print(f"Dataset sizes: {', '.join([f'{k}={v}' for k, v in file_counts.items()])}")
        
        # Step 1: Calculate ideal distribution for ALL 332 files based on dataset proportions
        ideal_distribution = {}
        remainders = {}
        
        for agent, count in file_counts.items():
            if total_files > 0 and count > 0:
                proportion = count / total_files
                ideal_total = proportion * TOTAL_SAMPLE_SIZE
                ideal_distribution[agent] = math.floor(ideal_total)
                remainders[agent] = ideal_total - math.floor(ideal_total)
            else:
                ideal_distribution[agent] = 0
                remainders[agent] = 0
        
        # Distribute remainder to reach exactly 332
        current_sum = sum(ideal_distribution.values())
        remainder_to_distribute = TOTAL_SAMPLE_SIZE - current_sum
        sorted_remainders = sorted(remainders.items(), key=lambda item: item[1], reverse=True)
        
        for i in range(remainder_to_distribute):
            agent_to_increment = sorted_remainders[i][0]
            ideal_distribution[agent_to_increment] += 1
        
        # Step 2: Subtract what we already have from same_entries
        print(f"\nIdeal distribution for {TOTAL_SAMPLE_SIZE} files:")
        for agent in AGENT_NAMES:
            already_have = same_entries_by_source.get(agent, 0)
            ideal_total = ideal_distribution.get(agent, 0)
            need_to_sample = max(0, ideal_total - already_have)
            samples_to_take[agent] = need_to_sample
            
            if total_files > 0 and file_counts.get(agent, 0) > 0:
                percentage = (file_counts[agent] / total_files) * 100
                print(f"  {agent}: {percentage:.1f}% → {ideal_total} total (have {already_have}, sample {need_to_sample})")
        
        print(f"\nTotal to sample: {sum(samples_to_take.values())} files")
    else:
        print("No additional sampling needed (same_entries sufficient)")
        for agent in AGENT_NAMES:
            samples_to_take[agent] = 0

    # --- Phase 3: Sample Files ---
    print(f"\n--- 🎲 Phase 3: Sampling Files from Datasets ---")
    
    newly_sampled = []
    
    for agent, num_samples in samples_to_take.items():
        if num_samples > 0:
            df_to_sample = filtered_dataframes[agent]
            if len(df_to_sample) >= num_samples:
                sample_df = df_to_sample.sample(n=num_samples, random_state=RANDOM_STATE)
                if 'source_dataset' not in sample_df.columns:
                    sample_df['source_dataset'] = agent
                newly_sampled.append(sample_df)
                print(f"✅ Sampled {num_samples} files from '{agent}'")
            else:
                print(f"⚠️  Only {len(df_to_sample)} files available for '{agent}', needed {num_samples}")
                sample_df = df_to_sample.copy()
                if 'source_dataset' not in sample_df.columns:
                    sample_df['source_dataset'] = agent
                newly_sampled.append(sample_df)

    # --- Phase 4: Combine same_entries + new samples ---
    print(f"\n--- 🔗 Phase 4: Combining Files ---")
    
    all_samples = []
    if same_entries_df is not None and len(same_entries_df) > 0:
        all_samples.append(same_entries_df)
        print(f"✅ Added {len(same_entries_df)} files from same_entries")
    
    if newly_sampled:
        newly_sampled_df = pd.concat(newly_sampled, ignore_index=True)
        all_samples.append(newly_sampled_df)
        print(f"✅ Added {len(newly_sampled_df)} newly sampled files")
    
    if not all_samples:
        print("❌ No files to process!")
        return
    
    combined_df = pd.concat(all_samples, ignore_index=True)
    print(f"\n📦 Total files before language filter: {len(combined_df)}")

    # --- Phase 5: Apply English Language Filter to ALL files ---
    print(f"\n--- 🌍 Phase 5: Applying English Language Filter to ALL {len(combined_df)} Files ---")
    print("This may take several minutes...")
    
    english_files = []
    non_english_files = []
    
    for idx, row in combined_df.iterrows():
        if (idx + 1) % 10 == 0:
            print(f"  Checked {idx + 1}/{len(combined_df)} files...")
        
        is_eng = check_file_is_english(row)
        if is_eng:
            english_files.append(row)
        else:
            non_english_files.append(row)
            print(f"  ⚠️  Non-English file: {row['repository_owner']}/{row['repository_name']}/{row['file_path']}")
        
        time.sleep(0.1)  # Rate limiting
    
    english_df = pd.DataFrame(english_files)
    print(f"\n✅ English files: {len(english_df)}/{len(combined_df)}")
    print(f"❌ Non-English files: {len(non_english_files)}")
    
    # --- Phase 6: Replace non-English files ---
    if len(non_english_files) > 0 and len(english_df) < TOTAL_SAMPLE_SIZE:
        print(f"\n--- 🔄 Phase 6: Replacing {len(non_english_files)} Non-English Files ---")
        
        replacements_needed_by_source = {}
        for row in non_english_files:
            source = row.get('source_dataset', 'unknown')
            replacements_needed_by_source[source] = replacements_needed_by_source.get(source, 0) + 1
        
        for agent, needed in replacements_needed_by_source.items():
            if agent not in filtered_dataframes:
                continue
                
            print(f"\n  Replacing {needed} non-English '{agent}' files...")
            df_available = filtered_dataframes[agent]
            
            # Exclude already sampled files
            already_sampled_paths = set(english_df['file_path'].tolist())
            df_available = df_available[~df_available['file_path'].isin(already_sampled_paths)]
            
            replacement_count = 0
            attempt = 0
            max_attempts = min(needed * 3, len(df_available))
            
            while replacement_count < needed and attempt < max_attempts:
                # Sample one file at a time
                if len(df_available) == 0:
                    print(f"    ⚠️  No more files available for '{agent}'")
                    break
                
                candidate = df_available.sample(n=1, random_state=RANDOM_STATE + attempt)
                attempt += 1
                
                # Check if English
                is_eng = check_file_is_english(candidate.iloc[0])
                if is_eng:
                    candidate_row = candidate.iloc[0].copy()
                    if 'source_dataset' not in candidate_row or pd.isna(candidate_row['source_dataset']):
                        candidate_row['source_dataset'] = agent
                    english_files.append(candidate_row)
                    replacement_count += 1
                    print(f"    ✅ Found replacement {replacement_count}/{needed}")
                    
                    # Remove from available
                    df_available = df_available[df_available['file_path'] != candidate.iloc[0]['file_path']]
                
                time.sleep(0.1)
            
            if replacement_count < needed:
                print(f"    ⚠️  Could only find {replacement_count}/{needed} English replacements for '{agent}'")
        
        # Recreate DataFrame with replacements
        english_df = pd.DataFrame(english_files)
        print(f"\n✅ Final count after replacements: {len(english_df)} English files")

    # --- Phase 7: Save Output ---
    print(f"\n--- 💾 Phase 7: Saving Output ---")
    
    # Take only target number if we have more
    if len(english_df) > TOTAL_SAMPLE_SIZE:
        print(f"  Trimming to {TOTAL_SAMPLE_SIZE} files...")
        english_df = english_df.head(TOTAL_SAMPLE_SIZE)
    
    english_df.to_csv(OUTPUT_FILENAME, index=False)
    
    print(f"\n" + "=" * 80)
    print(f"✨ SUCCESS!")
    print(f"=" * 80)
    print(f"Total files saved: {len(english_df)}")
    print(f"Target was: {TOTAL_SAMPLE_SIZE}")
    if 'source_dataset' in english_df.columns:
        print(f"\nBreakdown by source:")
        print(english_df['source_dataset'].value_counts().to_string())
    print(f"\n📁 Output saved to: {OUTPUT_FILENAME}")
    print("=" * 80)


# --- Execution ---
if __name__ == "__main__":
    proportional_sampler_exact_match()
