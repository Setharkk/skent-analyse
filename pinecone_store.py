import os
try:
    import pinecone
except ImportError:
    pinecone = None
import faiss

class VectorStore:
    def __init__(self):
        try:
            self.faiss_index = faiss.read_index("faiss_index/ast.index")
            self.use_faiss = True
        except Exception:
            if pinecone:
                pinecone.init(api_key=os.getenv("PINECONE_API_KEY"), environment="us-east1-gcp")
                self.index = pinecone.Index("reverse-index")
                self.use_faiss = False
            else:
                raise RuntimeError("No vector store available (FAISS and Pinecone unavailable)")

    def search(self, vector, top_k=5):
        if self.use_faiss:
            D, I = self.faiss_index.search(vector, top_k)
            return I
        else:
            return self.index.query(vector.tolist(), top_k=top_k)["matches"]
