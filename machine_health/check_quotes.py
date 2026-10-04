with open('generate_notebook.py') as f:
    lines = f.readlines()

for i, line in enumerate(lines[:200]):
    if '"""' in line:
        print(f"Line {i+1}: {line.strip()}")
