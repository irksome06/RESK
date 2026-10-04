with open('generate_notebook.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Inside python code cells, replace any function/class docstrings:
# Let's inspect where triple quotes appear inside code cells
# Specifically:
# validate_dataset_schema
text = text.replace('    """\n    Validates that the input DataFrame', "    '''\n    Validates that the input DataFrame")
text = text.replace('    and expected metadata.\n    """', "    and expected metadata.\n    '''")
text = text.replace('    expected_metadata: list\n) -> bool:\n    """', "    expected_metadata: list\n) -> bool:\n    '''")
text = text.replace('    expected metadata.\n    """', "    expected metadata.\n    '''")
text = text.replace('    expected metadata columns validated successfully.\n    """', "    expected metadata columns validated successfully.\n    '''")
text = text.replace('    expected metadata columns.\n    """', "    expected metadata columns.\n    '''")

# Let's do a more general regex or string replace for inner docstrings
import re
# Replace `"""` with `'''` if it is preceded by indentation and followed by text (docstring start)
# or preceded by text and followed by newline (docstring end)
# But NOT when it's part of `cells.append` or `"""))`

lines = text.split('\n')
fixed_lines = []
in_outer = False
for line in lines:
    if 'cells.append' in line and '"""' in line:
        fixed_lines.append(line)
        in_outer = True
    elif line.strip() == '"""))' or line.strip() == '"""':
        fixed_lines.append(line)
        in_outer = False
    elif '"""' in line and in_outer:
        # This is an inner triple quote! Replace with triple single quotes
        fixed_lines.append(line.replace('"""', "'''"))
    else:
        fixed_lines.append(line)

new_text = '\n'.join(fixed_lines)

with open('generate_notebook.py', 'w', encoding='utf-8') as f:
    f.write(new_text)

import py_compile
try:
    py_compile.compile('generate_notebook.py', doraise=True)
    print("SUCCESS: generate_notebook.py compiled with zero errors!")
except py_compile.PyCompileError as e:
    print("Compile Error:", e)
