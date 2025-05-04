import os
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import httpx
from datetime import datetime

DB_URL = os.getenv("DB_URL", "postgresql://user:pass@db:5432/reverse")
engine = sa.create_engine(DB_URL)
Session = sessionmaker(bind=engine)

class FineTune(sa.ext.declarative.declarative_base()):
    __tablename__ = 'fine_tunes'
    id = sa.Column(sa.Integer, primary_key=True)
    run_id = sa.Column(sa.String(64), unique=True)
    status = sa.Column(sa.String(32))
    started_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    finished_at = sa.Column(sa.DateTime)
    model = sa.Column(sa.String(64))
    params = sa.Column(sa.JSON)

async def prepare_and_launch():
    session = Session()
    # Prépare les données (issues + patches)
    issues = session.execute(sa.text("SELECT * FROM issues WHERE patch IS NOT NULL")).fetchall()
    if len(issues) < 5000:
        print("Pas assez d'exemples pour fine-tune.")
        return
    # Format JSONL
    data = [
        {"input": i['description'], "output": i['patch']} for i in issues
    ]
    import json, tempfile
    with tempfile.NamedTemporaryFile('w+', delete=False) as f:
        for row in data:
            f.write(json.dumps(row) + '\n')
        data_path = f.name
    # Upload & launch fine-tune (Together AI API)
    async with httpx.AsyncClient() as client:
        upload_resp = await client.post(
            "https://api.together.xyz/v1/fine-tunes/files",
            headers={"Authorization": f"Bearer {os.getenv('TOGETHER_KEY')}"},
            files={"file": open(data_path, 'rb')}
        )
        file_id = upload_resp.json()["id"]
        launch_resp = await client.post(
            "https://api.together.xyz/v1/fine-tunes",
            headers={"Authorization": f"Bearer {os.getenv('TOGETHER_KEY')}"},
            json={
                "training_file": file_id,
                "model": "mixtral-8x22b-instruct",
                "n_epochs": 3,
                "batch_size": 16
            }
        )
        run_id = launch_resp.json()["id"]
        ft = FineTune(run_id=run_id, status="running", model="mixtral-8x22b-instruct", params={"epochs": 3, "batch_size": 16})
        session.add(ft)
        session.commit()
        print(f"Fine-tune lancé, run_id={run_id}")
    os.remove(data_path)

async def get_status(run_id):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.together.xyz/v1/fine-tunes/{run_id}",
            headers={"Authorization": f"Bearer {os.getenv('TOGETHER_KEY')}"}
        )
        return resp.json()