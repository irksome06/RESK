import re

with open('generate_notebook.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace any occurrence of `)"""))` with `)\n"""))`
fixed = re.sub(r'([^\n])\s*"""\)\)', r'\1\n"""))', content)

with open('generate_notebook.py', 'w', encoding='utf-8') as f:
    f.write(fixed)

import py_compile
try:
    py_compile.compile('generate_notebook.py', doraise=True)
    print("Compilation successful! Zero syntax errors.")
except py_compile.PyCompileError as e:
    print("Error:", e)
