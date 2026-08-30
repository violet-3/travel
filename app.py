"""
山河游记 · FastAPI 纯后端
启动: python app.py
API:
  POST /api/generate  → 攻略 JSON
  GET  /api/config    → 前端地图所需的高德 JS Key / 安全密钥
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import default_config
from orchestrator import TravelOrchestrator

app = FastAPI(title="山河游记")
frontend = Path(__file__).parent / "frontend"
photo_dir = Path(__file__).parent / "static" / "photos"
photo_dir.mkdir(parents=True, exist_ok=True)   # 富化层图片缓存目录

# 单例复用（内部无请求态状态，可安全并发）
orch = TravelOrchestrator()


class GenReq(BaseModel):
    query: str = "想去安阳玩3天"


@app.post("/api/generate")
async def api_generate(req: GenReq):
    try:
        guide = await orch.generate(req.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {e}")
    return json.loads(guide.model_dump_json())


@app.get("/api/config")
async def api_config():
    """前端地图启动参数（高德 JS API Key + 安全密钥），前端不再硬编码"""
    amap = default_config.amap
    return {"amap_key": amap.route_key, "amap_secret": amap.secret}


@app.get("/")
async def index():
    return FileResponse(frontend / "index.html")


app.mount("/css", StaticFiles(directory=frontend / "css"), name="css")
app.mount("/js", StaticFiles(directory=frontend / "js"), name="js")
app.mount("/static/photos", StaticFiles(directory=photo_dir), name="photos")

if __name__ == "__main__":
    import uvicorn
    print("Shanhe Travel Guide")
    print("  http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
