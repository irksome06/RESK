import time
import nbformat
from nbclient import NotebookClient

def execute():
    nb_path = 'one.ipynb'
    print(f"Reading {nb_path}...")
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)
        
    client = NotebookClient(nb, timeout=600, kernel_name='python3')
    print("Executing notebook cells with NotebookClient...")
    t0 = time.time()
    client.execute()
    elapsed = time.time() - t0
    print(f"Notebook executed successfully in {elapsed:.2f} seconds!")
    
    with open(nb_path, 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)
    print(f"Executed notebook saved to {nb_path} with all outputs and figures.")

if __name__ == '__main__':
    execute()
