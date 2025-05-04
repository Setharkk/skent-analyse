import os
import faiss
import numpy as np
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import httpx

DB_URL = os.getenv("DB_URL", "postgresql://user:pass@db:5432/reverse")
engine = sa.create_engine(DB_URL)
Session = sessionmaker(bind=engine)
FAISS_DIR = os.path.join(os.path.dirname(__file__), 'faiss_index')
INDEX_PATH = os.path.join(FAISS_DIR, 'ast.index')
EMBEDDING_DIM = 3072

async def retrieve(query, top_k=5):
    # Embedding requête
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_KEY')}"},
            json={"input": query, "model": "text-embedding-3-large"}
        )
        qvec = np.array(resp.json()["data"][0]["embedding"], dtype=np.float32)
    # Recherche FAISS
    if not os.path.exists(INDEX_PATH):
        return []
    index = faiss.read_index(INDEX_PATH)
    D, I = index.search(qvec.reshape(1, -1), top_k)
    session = Session()
    # Récupère les chunks correspondants
    results = []
    for idx in I[0]:
        if idx < 0:
            continue
        chunk = session.execute(sa.text("SELECT chunk_id, scan_id FROM embeddings WHERE id=:id"), {"id": int(idx)+1}).fetchone()
        if chunk:
            results.append(dict(chunk))
    # Fallback GoogleSearch si rien
    if not results:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://www.googleapis.com/customsearch/v1?q={query}&key={os.getenv('GOOGLE_KEY')}")
            return resp.json().get('items', [])
    return results
