import lizard

code_script = """
print('hello')
x = 1
if x > 0:
    print('yes')
elif x < 0:
    print('no')
else:
    print('zero')

for i in range(10):
    if i % 2 == 0:
        print(i)
"""

print("--- Original ---")
analysis = lizard.analyze_file.analyze_source_code("script.py", code_script)
print(f"nloc: {analysis.nloc}")
print(f"avg_ccn: {analysis.average_cyclomatic_complexity}")

print("\n--- Wrapped ---")
# Indent the original code
indented_code = "\n".join(["    " + line for line in code_script.splitlines()])
wrapped_code = f"def _global_scope_wrapper():\n{indented_code}"

analysis_wrapped = lizard.analyze_file.analyze_source_code("script.py", wrapped_code)
print(f"nloc: {analysis_wrapped.nloc}")
print(f"avg_ccn: {analysis_wrapped.average_cyclomatic_complexity}")
if analysis_wrapped.function_list:
    print(f"wrapper ccn: {analysis_wrapped.function_list[0].cyclomatic_complexity}")
