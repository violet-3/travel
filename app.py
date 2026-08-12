"""
山河游记 · FastAPI 纯后端
启动: python app.py
API: POST /api/generate  → 返回 JSON
"""

import json
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

from orchestrator import TravelOrchestrator

app = FastAPI(title="山河游记")
frontend = Path(__file__).parent / "frontend"


class GenReq(BaseModel):
    query: str = "想去安阳玩3天"


@app.post("/api/generate")
async def api_generate(req: GenReq):
    orch = TravelOrchestrator()
    guide = await orch.generate(req.query)
    return json.loads(guide.model_dump_json())


@app.get("/")
async def index():
    return FileResponse(frontend / "index.html")


app.mount("/css", StaticFiles(directory=frontend / "css"), name="css")
app.mount("/js", StaticFiles(directory=frontend / "js"), name="js")

if __name__ == "__main__":
    import uvicorn
    print("Shanhe Travel Guide")
    print("  http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
