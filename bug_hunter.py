import yaml
import openai
from langchain.llms import OpenAI, Together
from langchain.embeddings import OpenAIEmbeddings
from langchain.retrievers import GoogleSearchAPIRetriever
import os

class BugHunterAgent:
    def __init__(self):
        with open(os.path.join(os.path.dirname(__file__), 'prompts', 'bug_hunter.yaml'), encoding='utf-8') as f:
            self.prompt = yaml.safe_load(f)
        self.llm = OpenAI(model="gpt-4.1", temperature=0.1)
        self.fallback_llm = Together(model="mixtral-8x22b", api_key=os.getenv("TOGETHER_KEY"))
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.retriever = GoogleSearchAPIRetriever(top_k=10, freshness_days=365, api_key=os.getenv("GOOGLE_KEY"))

    async def run(self, code: str):
        # RAG: recherche web + embeddings
        docs = self.retriever.retrieve(query=code)
        context = "\n".join([d['snippet'] for d in docs])
        user_prompt = self.prompt['user'].replace('{code}', code)
        full_prompt = f"{self.prompt['system']}\n{user_prompt}\nContexte:\n{context}"
        try:
            resp = self.llm(full_prompt)
        except Exception:
            resp = self.fallback_llm(full_prompt)
        return resp
