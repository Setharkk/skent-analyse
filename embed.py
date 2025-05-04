import os
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import faiss
import numpy as np
import httpx
from datetime import datetime

DB_URL = os.getenv("DB_URL", "postgresql://user:pass@db:5432/reverse")
engine = sa.create_engine(DB_URL)
Session = sessionmaker(bind=engine)
FAISS_DIR = os.path.join(os.path.dirname(__file__), 'faiss_index')
os.makedirs(FAISS_DIR, exist_ok=True)
INDEX_PATH = os.path.join(FAISS_DIR, 'ast.index')

EMBEDDING_DIM = 3072  # text-embedding-3-large

class Embedding(sa.ext.declarative.declarative_base()):
    __tablename__ = 'embeddings'
    id = sa.Column(sa.Integer, primary_key=True)
    chunk_id = sa.Column(sa.Integer)
    scan_id = sa.Column(sa.Integer)
    vector = sa.Column(sa.ARRAY(sa.Float))
    doc_type = sa.Column(sa.String(16))
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)

def embed_all():
    session = Session()
    # Récupère tous les AST chunks non encodés
    ast_chunks = session.execute(sa.text("SELECT id, relpath, compressed_ast, scan_id FROM ast_chunks LEFT JOIN embeddings ON ast_chunks.id = embeddings.chunk_id WHERE embeddings.id IS NULL")).fetchall()
    if not ast_chunks:
        print("Aucun chunk à encoder.")
        return
    # Prépare FAISS
    if os.path.exists(INDEX_PATH):
        index = faiss.read_index(INDEX_PATH)
    else:
        index = faiss.IndexFlatL2(EMBEDDING_DIM)
    vectors = []
    ids = []
    for row in ast_chunks:
        chunk_id, relpath, compressed_ast, scan_id = row[:4]
        # Décompresse et prépare le texte (ici simplifié)
        import lz4.frame, json
        ast_dict = json.loads(lz4.frame.decompress(compressed_ast))
        text = relpath + "\n" + str(ast_dict)
        # Appel OpenAI embedding
        async def get_embedding(text):
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {os.getenv('OPENAI_KEY')}"},
                    json={"input": text, "model": "text-embedding-3-large"}
                )
                return resp.json()["data"][0]["embedding"]
        import asyncio
        vector = asyncio.run(get_embedding(text))
        vectors.append(np.array(vector, dtype=np.float32))
        ids.append(chunk_id)
        # Stocke en DB
        emb = Embedding(chunk_id=chunk_id, scan_id=scan_id, vector=vector, doc_type="ast")
        session.add(emb)
    if vectors:
        index.add(np.stack(vectors))
        faiss.write_index(index, INDEX_PATH)
    session.commit()
    print(f"Embeddings FAISS mis à jour ({len(vectors)} chunks)")

if __name__ == '__main__':
    embed_all()