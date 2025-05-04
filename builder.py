import os
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import json
from graphviz import Digraph
from collections import defaultdict

DB_URL = os.getenv("DB_URL", "postgresql://user:pass@db:5432/reverse")
engine = sa.create_engine(DB_URL)
Session = sessionmaker(bind=engine)

# Table for metrics
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
class Metric(Base):
    __tablename__ = 'metrics'
    id = sa.Column(sa.Integer, primary_key=True)
    scan_id = sa.Column(sa.Integer)
    file = sa.Column(sa.String)
    score = sa.Column(sa.Float)
Base.metadata.create_all(engine)

def build_graph(scan_id: int):
    """
    Construit le graphe pour un scan donné.
    Retourne (dot_str, json_dict)
    """
    session = Session()
    # Récupère les AST compressés pour le scan
    ast_chunks = session.execute(
        sa.text("SELECT relpath, compressed_ast FROM ast_chunks WHERE scan_id=:scan_id"),
        {"scan_id": scan_id}
    ).fetchall()
    nodes = set()
    edges = []
    d3_nodes = []
    d3_links = []
    # Simulé: parse AST, extraire fichiers/classes/fonctions et relations
    for row in ast_chunks:
        relpath = row[0]
        nodes.add((relpath, 'file'))
        # Simule extraction classes/fonctions
        for i in range(2):
            cname = f"Class_{i}_{relpath}"
            nodes.add((cname, 'class'))
            edges.append((relpath, cname, 'contains'))
            for j in range(2):
                fname = f"func_{j}_{cname}"
                nodes.add((fname, 'function'))
                edges.append((cname, fname, 'contains'))
                # Simule appel/call
                if j == 1:
                    edges.append((fname, f"func_0_{cname}", 'call'))
        # Simule import
        if relpath.endswith('1.py'):
            edges.append((relpath, 'file2.py', 'import'))
    # DOT
    dot = Digraph('G')
    for n, t in nodes:
        shape = {'file': 'box', 'class': 'ellipse', 'function': 'diamond'}.get(t, 'oval')
        dot.node(n, shape=shape)
        d3_nodes.append({'id': n, 'type': t})
    for src, tgt, typ in edges:
        dot.edge(src, tgt, label=typ)
        d3_links.append({'source': src, 'target': tgt, 'type': typ})
    dot_str = dot.source
    json_dict = {'nodes': d3_nodes, 'links': d3_links}
    # Calculs metrics (simulé)
    for n, t in nodes:
        if t == 'file':
            score = 1.0  # Simulé: complexité
            m = Metric(scan_id=scan_id, file=n, score=score)
            session.add(m)
    session.commit()
    return dot_str, json_dict
