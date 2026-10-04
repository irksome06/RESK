with open('generate_notebook.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix line 186
text = text.replace("    '''\n    Validates that the input DataFrame strictly adheres to the condition monitoring schema.\n    Raises ValueError or TypeError if columns are missing or have invalid datatypes.\n    \"\"\"",
                    "    '''\n    Validates that the input DataFrame strictly adheres to the condition monitoring schema.\n    Raises ValueError or TypeError if columns are missing or have invalid datatypes.\n    '''")

# Let's inspect all occurrences of ''' and """
with open('generate_notebook.py', 'w', encoding='utf-8') as f:
    f.write(text)

import py_compile
try:
    py_compile.compile('generate_notebook.py', doraise=True)
    print("SUCCESS: generate_notebook.py compiled with ZERO syntax errors!")
except py_compile.PyCompileError as e:
    print("Error:", e)
