"""
山河游记 · FastAPI 纯后端
启动: python app.py
API:
  POST /api/generate         → 攻略 JSON (一次性)
  POST /api/generate/stream  → NDJSON 流: 进度事件 + 最终攻略 (前端用)
  GET  /api/config           → 前端地图所需的高德 JS Key / 安全密钥
"""

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
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


def _guide_json(guide) -> dict:
    # by_alias: Transport 的 from/to 别名输出为 "from"/"to"，与前端字段对齐
    return json.loads(guide.model_dump_json(by_alias=True))


def _ndjson(obj) -> str:
    return json.dumps(obj, ensure_ascii=False) + "\n"


@app.post("/api/generate")
async def api_generate(req: GenReq):
    try:
        guide = await orch.generate(req.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {e}")
    return _guide_json(guide)


@app.post("/api/generate/stream")
async def api_generate_stream(req: GenReq):
    """流式生成: 逐行输出 {"type":"progress",...} 进度事件，最后输出 {"type":"guide",...} 或 {"type":"error",...}"""
    queue: asyncio.Queue = asyncio.Queue()

    def on_progress(progress: int, stage: str, message: str):
        queue.put_nowait({"type": "progress", "progress": progress,
                          "stage": stage, "message": message})

    async def event_gen():
        task = asyncio.create_task(orch.generate(req.query, on_progress=on_progress))
        getter = asyncio.create_task(queue.get())
        try:
            while True:
                done, _ = await asyncio.wait({getter, task},
                                             return_when=asyncio.FIRST_COMPLETED)
                if getter in done:
                    yield _ndjson(getter.result())
                    getter = asyncio.create_task(queue.get())
                if task in done:
                    getter.cancel()
                    while not queue.empty():          # 排空剩余进度
                        yield _ndjson(queue.get_nowait())
                    exc = task.exception()
                    if exc:
                        yield _ndjson({"type": "error", "message": str(exc)})
                    else:
                        yield _ndjson({"type": "guide",
                                       "guide": _guide_json(task.result())})
                    return
        finally:
            getter.cancel()
            if not task.done():
                task.cancel()

    return StreamingResponse(event_gen(), media_type="application/x-ndjson")


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
