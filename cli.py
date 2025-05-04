import argparse
import tempfile
import shutil
import os
import json
from .core import ScannerEngine
import git

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True, help='Git repo URL')
    args = parser.parse_args()
    tmpdir = tempfile.mkdtemp()
    try:
        git.Repo.clone_from(args.repo, tmpdir, depth=1, multi_options=['--filter=blob:none'])
        engine = ScannerEngine(args.repo)
        scan_id = engine.run(tmpdir)
        print(json.dumps({'scan_id': scan_id}))
    finally:
        shutil.rmtree(tmpdir)

if __name__ == '__main__':
    main()
