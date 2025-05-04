import os
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import openai

DB_URL = os.getenv("DB_URL", "postgresql://user:pass@db:5432/reverse")
engine = sa.create_engine(DB_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Suggestion(Base):
    __tablename__ = 'suggestions'
    id = sa.Column(sa.Integer, primary_key=True)
    scan_id = sa.Column(sa.Integer)
    suggestion = sa.Column(sa.Text)
    type = sa.Column(sa.String)
Base.metadata.create_all(engine)

GPT_MODEL = "gpt-4.1"

async def generate_suggestions(scan_id: int, graph_json: dict):
    """
    Génère des suggestions (refactor, perf, security) via GPT-4.1 et stocke en base.
    """
    session = Session()
    prompt = (
        "Voici un graphe de dépendances et d'appels de code (format JSON d3). "
        "Génère des suggestions de refactorisation, performance et sécurité pour ce projet. "
        "Réponds en français, liste séparée par type.\n"
        f"Graphe: {graph_json}"
    )
    resp = openai.ChatCompletion.create(
        model=GPT_MODEL,
        messages=[{"role": "system", "content": "Tu es un expert en architecture logicielle."},
                  {"role": "user", "content": prompt}],
        max_tokens=512
    )
    text = resp.choices[0].message['content']
    # Découpe suggestions par type (simple)
    for typ in ['refactor', 'perf', 'security']:
        if typ in text:
            s = Suggestion(scan_id=scan_id, suggestion=text, type=typ)
            session.add(s)
    session.commit()
    return text
