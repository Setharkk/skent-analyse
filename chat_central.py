import asyncio
import json
import os
import sqlalchemy as sa
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from langchain.llms import OpenAI, Together
from langchain.embeddings import OpenAIEmbeddings
from langchain.retrievers import GoogleSearchAPIRetriever
import threading
import time

DB_URL = os.getenv("DB_URL", "postgresql://user:pass@db:5432/reverse")
engine = sa.create_engine(DB_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Chat(Base):
    __tablename__ = 'chats'
    id = sa.Column(sa.Integer, primary_key=True)
    session_id = sa.Column(sa.String(64), unique=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = 'messages'
    id = sa.Column(sa.Integer, primary_key=True)
    chat_id = sa.Column(sa.Integer, sa.ForeignKey('chats.id'))
    sender = sa.Column(sa.String(16))
    content = sa.Column(sa.Text)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)

class Usage(Base):
    __tablename__ = 'usage'
    id = sa.Column(sa.Integer, primary_key=True)
    model = sa.Column(sa.String(32))
    tokens = sa.Column(sa.Integer)
    cost_usd = sa.Column(sa.Numeric(8,4))
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

# Throttling per model
class Throttle:
    def __init__(self, rate):
        self.rate = rate
        self.lock = threading.Lock()
        self.calls = {}

    def allow(self, model):
        now = time.time()
        with self.lock:
            if model not in self.calls:
                self.calls[model] = []
            self.calls[model] = [t for t in self.calls[model] if now-t < 1]
            if len(self.calls[model]) < self.rate:
                self.calls[model].append(now)
                return True
            return False

throttle = Throttle(rate=10)

class ChatCentralAgent:
    def __init__(self):
        self.llm = OpenAI(model="gpt-4.1", temperature=0.2)
        self.fallback_llm = Together(model="mixtral-8x22b", api_key=os.getenv("TOGETHER_KEY"))
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.retriever = GoogleSearchAPIRetriever(top_k=10, freshness_days=365, api_key=os.getenv("GOOGLE_KEY"))
        self.session = Session()

    async def run(self, session_id: str, message: str):
        chat = self.session.query(Chat).filter_by(session_id=session_id).first()
        if not chat:
            chat = Chat(session_id=session_id)
            self.session.add(chat)
            self.session.commit()
        msg = Message(chat_id=chat.id, sender="user", content=message)
        self.session.add(msg)
        self.session.commit()
        # RAG
        docs = self.retriever.retrieve(query=message)
        context = "\n".join([d['snippet'] for d in docs])
        prompt = f"{message}\nContexte:\n{context}"
        model = "gpt-4.1"
        if not throttle.allow(model):
            await asyncio.sleep(0.1)
        try:
            resp = self.llm(prompt)
            tokens = len(prompt.split()) + len(str(resp).split())
            cost = tokens * 0.00001  # Estimation simple
        except Exception:
            model = "mixtral-8x22b"
            if not throttle.allow(model):
                await asyncio.sleep(0.1)
            resp = self.fallback_llm(prompt)
            tokens = len(prompt.split()) + len(str(resp).split())
            cost = tokens * 0.000002
        msg2 = Message(chat_id=chat.id, sender="ai", content=resp)
        self.session.add(msg2)
        self.session.add(Usage(model=model, tokens=tokens, cost_usd=cost))
        self.session.commit()
        return resp

# WebSocket endpoint (FastAPI example)
from fastapi import APIRouter
router = APIRouter()

@router.websocket("/ws/chat/{session_id}")
async def chat_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    agent = ChatCentralAgent()
    try:
        while True:
            data = await websocket.receive_text()
            resp = await agent.run(session_id, data)
            # Streaming chunk (simulate)
            for chunk in [resp[i:i+50] for i in range(0, len(resp), 50)]:
                await websocket.send_text(chunk)
    except WebSocketDisconnect:
        await websocket.close()
