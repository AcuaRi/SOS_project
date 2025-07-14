# /home/SoS/SOS_project/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from Yun.analyze_router import router as analyze_router   # 윤재용 기능 호출
from Shin.guide_router import router as guide_router  # 신은총 기능 호출

app = FastAPI(title="SOS Project API")

BASE = Path(__file__).resolve().parent
app.mount("/web", StaticFiles(directory=BASE / "web", html=True), name="web")
app.include_router(analyze_router)
app.include_router(guide_router)

@app.get("/ping")
async def ping():
    return {"status": "ok"}
