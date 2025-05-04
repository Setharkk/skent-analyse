import time
import tempfile
import os
import shutil
from app.scanner.core import ScannerEngine

def create_mock_repo(tmpdir, n_files=10000, lines_per_file=100):
    os.makedirs(tmpdir, exist_ok=True)
    for i in range(n_files):
        ext = ['py', 'js', 'ts', 'go'][i % 4]
        with open(os.path.join(tmpdir, f'f{i}.{ext}'), 'w') as f:
            for _ in range(lines_per_file):
                f.write('print("hello world")\n')

def main():
    tmpdir = tempfile.mkdtemp()
    try:
        create_mock_repo(tmpdir, n_files=10000, lines_per_file=100)
        engine = ScannerEngine(repo_url='mock')
        start = time.time()
        scan_id = engine.run(tmpdir)
        elapsed = time.time() - start
        total_lines = 10000 * 100
        print(f"Scanned {total_lines} lines in {elapsed:.2f} seconds ({total_lines/elapsed:.2f} lines/s)")
    finally:
        shutil.rmtree(tmpdir)

if __name__ == '__main__':
    main()
