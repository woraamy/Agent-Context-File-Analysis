import lizard
import sys

def test_lizard(code, filename):
    print(f"--- Testing {filename} ---")
    try:
        analysis = lizard.analyze_file.analyze_source_code(filename, code)
        print(f"nloc: {analysis.nloc}")
        print(f"function_list size: {len(analysis.function_list)}")
        print(f"average_cyclomatic_complexity: {analysis.average_cyclomatic_complexity}")
    except Exception as e:
        print(f"Error: {e}")

# 1. Plain text / Markdown
test_lizard("Title\n\nSome text here.", "readme.md")

# 2. Python script without functions
test_lizard("print('hello')\nx = 1\nif x > 0:\n    print('yes')", "script.py")

# 3. Python script WITH functions
test_lizard("def foo():\n    if True:\n        return 1\n    return 0", "func.py")

# 4. JSON file (Lizard generally doesn't analyze JSON complexity like code)
test_lizard('{"key": "value", "list": [1, 2, 3]}', "data.json")

# 5. Empty file
test_lizard("", "empty.py")
