from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from Yun.analyze_router import router as analyze_router
from Shin.guide_router import router as guide_router
from Kim.hospital_router import router as hospital_router
from Noh.navigation_router import router as navigation_router
from login.login_router import router as login_router

app = FastAPI(title="SOS Project API")

BASE = Path(__file__).resolve().parent

app.mount("/web", StaticFiles(directory=BASE / "web", html=True), name="web")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

app.include_router(analyze_router)
app.include_router(guide_router)
app.include_router(hospital_router)
app.include_router(navigation_router)
app.include_router(login_router)

@app.get("/ping")
async def ping():
    return {"status": "ok"}
