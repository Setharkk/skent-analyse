# Backend FastAPI minimal app
from fastapi import FastAPI, APIRouter, Request
from app.graph.builder import build_graph
from app.graph.recommender import generate_suggestions
import sqlalchemy as sa
import os
from sqlalchemy.orm import sessionmaker
from app.ml.finetune import get_status
from prometheus_fastapi_instrumentator import Instrumentator
from app.middleware.limiter import register_limiter, limiter
from app.middleware.audit import audit_log
from app.middleware.strict_base import StrictBaseModel
from slowapi.util import get_remote_address
from grafana_loki import LokiHandler
import logging
from loguru import logger

app = FastAPI()
register_limiter(app)
Instrumentator().instrument(app).expose(app)

loki_handler = LokiHandler(
    url="http://localhost:3100/loki/api/v1/push",
    tags={"app": "reverse-platform"},
    version="1",
    json=True
)
loki_handler.setLevel(logging.INFO)
logger.remove()
logger.add(loki_handler, level="INFO", serialize=True)

router = APIRouter()
DB_URL = os.getenv("DB_URL", "postgresql://user:pass@db:5432/reverse")
engine = sa.create_engine(DB_URL)
Session = sessionmaker(bind=engine)

@app.get("/")
def read_root():
    return {"msg": "Hello from FastAPI!"}

@router.get("/graph/{scan_id}")
async def get_graph(scan_id: int):
    """
    Retourne le graphe (DOT, JSON d3), les métriques et les suggestions pour un scan donné.
    """
    dot_str, json_dict = build_graph(scan_id)
    session = Session()
    metrics = session.execute(sa.text("SELECT file, score FROM metrics WHERE scan_id=:scan_id"), {"scan_id": scan_id}).fetchall()
    suggestions = session.execute(sa.text("SELECT type, suggestion FROM suggestions WHERE scan_id=:scan_id"), {"scan_id": scan_id}).fetchall()
    # Génère suggestions si absentes
    if not suggestions:
        await generate_suggestions(scan_id, json_dict)
        suggestions = session.execute(sa.text("SELECT type, suggestion FROM suggestions WHERE scan_id=:scan_id"), {"scan_id": scan_id}).fetchall()
    return {
        "dot": dot_str,
        "json": json_dict,
        "metrics": [{"file": m[0], "score": m[1]} for m in metrics],
        "suggestions": [{"type": s[0], "suggestion": s[1]} for s in suggestions],
    }

@app.get("/secure-example")
@limiter.limit("10/minute")
@audit_log
async def secure_example(request: Request):
    return {"msg": "Secure endpoint"}

@router.get("/finetune/status/{run_id}")
async def finetune_status(run_id: str):
    """
    Retourne le statut du fine-tune Together AI pour un run_id donné.
    """
    return await get_status(run_id)

# Pour tous vos modèles Pydantic, héritez de StrictBaseModel
# class MyModel(StrictBaseModel): ...
