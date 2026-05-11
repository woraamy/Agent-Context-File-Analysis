import sys
import os
from pathlib import Path
from pydriller import Repository
import lizard
import signal

# --- Copied functions from analyze_adoption.py ---

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Processing timed out")

def is_programmatic_code(filename):
    """
    Determines if a file is source code that should have cyclomatic complexity.
    Based on Lizard supported languages.
    """
    ext = os.path.splitext(filename)[1].lower()
    # List of extensions supported by Lizard
    code_extensions = {
        '.cs', # C#
        '.c', '.cpp', '.h', '.hpp', '.cc', '.cxx', '.hxx', # C/C++
        '.erl', '.hrl', # Erlang
        '.f', '.f90', '.for', '.f95', # Fortran
        '.gd', # GDScript
        '.go', # Golang
        '.java', # Java
        '.js', '.jsx', '.mjs', # JavaScript
        '.kt', '.kts', # Kotlin
        '.lua', # Lua
        '.m', '.mm', # Objective-C
        '.pl', '.pm', '.t', # Perl
        '.php', # PHP
        '.sql', '.pks', '.pkb', # PL/SQL
        '.py', '.pyw', # Python
        '.r', '.R', # R
        '.rb', # Ruby
        '.rs', # Rust
        '.scala', # Scala
        '.sol', # Solidity
        '.st', '.iec', # Structured Text
        '.swift', # Swift
        '.ttcn', '.ttcn3', # TTCN-3
        '.ts', '.tsx', # TypeScript
        '.vue', # VueJS
        '.zig', # Zig
    }
    return ext in code_extensions

def calculate_metrics(code, filename):
    """
    Calculates NLOC and Complexity using Lizard.
    """
    if not code or not is_programmatic_code(filename):
        return 0, 0.0

    if len(code) > 100000: 
        return len(code.splitlines()), 1.0
    
    if any(len(line) > 1000 for line in code.splitlines()):
        return len(code.splitlines()), 1.0

    loc = 0
    complexity = 0.0

    signal.alarm(5)

    try:
        analysis = lizard.analyze_file.analyze_source_code(filename, code)
        loc = analysis.nloc
        complexity = analysis.average_cyclomatic_complexity
        
        if loc > 0 and complexity == 0:
            complexity = 1.0

    except TimeoutException:
        print(f"  [Timeout] Skipping complex file: {filename}")
        loc = len(code.splitlines())
        complexity = 1.0
        return loc, complexity
    except Exception as e:
        print(f"  [Error] Lizard analysis failed for {filename}: {e}")
        loc = len(code.splitlines())
        complexity = 1.0
    finally:
        signal.alarm(0)
        
    return loc, complexity

# --- Debug Logic ---

import subprocess

def debug_commit(repo_url, commit_sha):
    print(f"Analyzing commit {commit_sha} from {repo_url}")
    
    try:
        repo_name = repo_url.split('/')[-1]
        owner = repo_url.split('/')[-2]
        local_path = Path("data_collector/repositories") / owner / repo_name
        
        path_to_use = str(local_path) if local_path.exists() else repo_url
        print(f"Using path: {path_to_use}")

        repo_mining = Repository(path_to_use, single=commit_sha)
        
        found = False
        for commit in repo_mining.traverse_commits():
            found = True
            print(f"Commit found: {commit.hash}")
            print(f"Message: {commit.msg}")
            print(f"Merge: {commit.merge}")
            print(f"Project Path: {commit.project_path}")
            print(f"Parents: {commit.parents}")
            
            print("Files modified (pydriller):")
            for mod in commit.modified_files:
                print(f"  - {mod.filename} (Change type: {mod.change_type})")
            
            if not commit.modified_files and commit.merge:
                print("Commit is a clean merge (no modified_files). Attempting git diff fallback...")
                
                if not commit.parents:
                    print("No parents found.")
                    continue
                    
                parent = commit.parents[0]
                cwd = commit.project_path
                
                print(f"Diffing {parent}..{commit.hash} in {cwd}")
                
                try:
                    # Get list of changed files
                    cmd = ["git", "diff", "--name-only", parent, commit.hash]
                    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
                    files = result.stdout.strip().splitlines()
                    
                    print(f"Files found via git diff ({len(files)}):")
                    for fname in files:
                        print(f"  - {fname}")
                        
                        if is_programmatic_code(fname):
                            # Get content
                            try:
                                cmd_show = ["git", "show", f"{commit.hash}:{fname}"]
                                res_show = subprocess.run(cmd_show, cwd=cwd, capture_output=True, text=True, errors='ignore') # Ignore errors for binary etc
                                
                                code = res_show.stdout
                                l, c = calculate_metrics(code, fname)
                                print(f"    calculate_metrics: loc={l}, complexity={c}")
                                
                            except Exception as e:
                                print(f"    Error reading file {fname}: {e}")
                        else:
                            print("    Skipping (not programmatic)")
                            
                except subprocess.CalledProcessError as e:
                    print(f"Git command failed: {e}")
                except Exception as e:
                    print(f"Fallback failed: {e}")

        if not found:
            print("Commit not found.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    signal.signal(signal.SIGALRM, timeout_handler)
    
    # Case 1: smart-recipe-generator
    print("\n--- Case 1 ---")
    repo_url = "https://github.com/Dereje1/smart-recipe-generator"
    commit_sha = "24ca8c228fc0e57a41153ca59800a75af2e3f09e"
    debug_commit(repo_url, commit_sha)

    # Case 2: luminal
    print("\n--- Case 2 ---")
    repo_url = "https://github.com/jafioti/luminal"
    commit_sha = "d0083a0607e23ac7a6c3ae7fd93c08db8fd2f38e"
    debug_commit(repo_url, commit_sha)
