import os
import tempfile
import shutil
import hashlib
import multiprocessing as mp
import lz4.frame
import redis
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import git
import glob
import importlib
import json
from tree_sitter import Language, Parser
from celery import Celery
from .celeryconfig import *

# --- SQLAlchemy setup ---
DB_URL = os.getenv("DB_URL", "postgresql://user:pass@db:5432/reverse")
engine = sa.create_engine(DB_URL)
Session = sessionmaker(bind=engine)

# --- Redis setup ---
REDIS_URL = os.getenv("REDIS_URL", "redis://cache:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL)

# --- Table definitions ---
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

class Scan(Base):
    __tablename__ = 'scans'
    id = sa.Column(sa.Integer, primary_key=True)
    repo_url = sa.Column(sa.String, nullable=False)
    status = sa.Column(sa.String, default='done')

class ASTChunk(Base):
    __tablename__ = 'ast_chunks'
    id = sa.Column(sa.Integer, primary_key=True)
    scan_id = sa.Column(sa.Integer, sa.ForeignKey('scans.id'))
    file_sha256 = sa.Column(sa.String, index=True)
    compressed_ast = sa.Column(sa.LargeBinary)
    relpath = sa.Column(sa.String)
    lang = sa.Column(sa.String)
    n_lines = sa.Column(sa.Integer)

Base.metadata.create_all(engine)

# --- Tree-sitter setup ---
LANGUAGES = {
    'py': 'python',
    'js': 'javascript',
    'ts': 'typescript',
    'go': 'go',
}
LANG_LIB = os.path.join(os.path.dirname(__file__), 'tree-sitter-libs.so')
if not os.path.exists(LANG_LIB):
    # Build the language library if missing
    Language.build_library(
        LANG_LIB,
        [
            'tree-sitter-python',
            'tree-sitter-javascript',
            'tree-sitter-typescript/typescript',
            'tree-sitter-go',
        ]
    )

TS_LANGS = {
    lang: Language(LANG_LIB, name) for lang, name in LANGUAGES.items()
}

celery_app = Celery('scanner', broker=broker_url, backend=result_backend)
celery_app.config_from_object('app.scanner.celeryconfig')

class ScannerEngine:
    def __init__(self, repo_url: str):
        self.repo_url = repo_url
        self.session = Session()

    def run(self, repo_path: str) -> int:
        scan = Scan(repo_url=self.repo_url)
        self.session.add(scan)
        self.session.commit()
        scan_id = scan.id
        files = self._collect_files(repo_path)
        batches = [files[i:i+5000] for i in range(0, len(files), 5000)]
        pool = mp.Pool(processes=mp.cpu_count())
        for batch in batches:
            results = pool.map(self._process_file, [(f, repo_path) for f in batch])
            self._bulk_insert(scan_id, results)
        pool.close()
        pool.join()
        self.session.commit()
        return scan_id

    def _collect_files(self, repo_path):
        exts = ('*.py', '*.js', '*.ts', '*.go')
        files = []
        for ext in exts:
            files.extend(glob.glob(os.path.join(repo_path, '**', ext), recursive=True))
        return files

    def _process_file(self, args):
        f, repo_path = args
        relpath = os.path.relpath(f, repo_path)
        ext = relpath.split('.')[-1]
        lang = LANGUAGES.get(ext)
        if not lang:
            return None
        parser = Parser()
        parser.set_language(TS_LANGS[ext])
        with open(f, 'rb') as fh:
            code = fh.read()
        tree = parser.parse(code)
        ast_dict = self._tree_to_dict(tree.root_node, code)
        ast_bytes = json.dumps(ast_dict).encode()
        compressed = lz4.frame.compress(ast_bytes)
        sha = hashlib.sha256(compressed).hexdigest()
        redis_client.set(sha, compressed)
        n_lines = code.count(b'\n')
        return {
            'file_sha256': sha,
            'compressed_ast': compressed,
            'relpath': relpath,
            'lang': lang,
            'n_lines': n_lines,
        }

    def _tree_to_dict(self, node, code):
        d = {
            'type': node.type,
            'start': node.start_point,
            'end': node.end_point,
            'children': [self._tree_to_dict(c, code) for c in node.children]
        }
        return d

    def _bulk_insert(self, scan_id, results):
        objs = [ASTChunk(scan_id=scan_id, **r) for r in results if r]
        self.session.bulk_save_objects(objs)

def scan_repo(repo_url: str):
    # ...existing code to clone and scan...
    # For demo, just call CLI or ScannerEngine
    import tempfile, shutil, git
    tmpdir = tempfile.mkdtemp()
    try:
        git.Repo.clone_from(repo_url, tmpdir, depth=1, multi_options=['--filter=blob:none'])
        engine = ScannerEngine(repo_url)
        scan_id = engine.run(tmpdir)
        return scan_id
    finally:
        shutil.rmtree(tmpdir)

celery_app.task(name="scan_repo")(scan_repo)
