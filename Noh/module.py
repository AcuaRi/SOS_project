from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from dotenv import load_dotenv
import os

import time
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime


# .env 로드
load_dotenv()

app = FastAPI()

templates = Jinja2Templates(directory="templates")

timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

# static 폴더 연결
app.mount("/static", StaticFiles(directory="static"), name="static")

# Firebase 초기화
cred_path = os.getenv("FIREBASE_CRED_PATH")
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.getenv("FIREBASE_DB_URL")
    })

def get_firebase_config():
    return {
        "apiKey": os.getenv("FIREBASE_API_KEY"),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
        "databaseURL": os.getenv("FIREBASE_DB_URL"),
        "projectId": os.getenv("FIREBASE_PROJECT_ID"),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
        "messagingSenderId": os.getenv("FIREBASE_SENDER_ID"),
        "appId": os.getenv("FIREBASE_APP_ID")
    }

def write_danger(uid, level, source="anonymous"):
    db.reference(f"danger_reports/{uid}").push({
        "danger": level,
        "from": source,
        "timestamp": time.time()
    })

@app.get("/", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {
        "request": request,
        "firebase_Config": get_firebase_config()
    })

@app.get("/button", response_class=HTMLResponse)
async def button(request: Request):
    return templates.TemplateResponse("button.html", {
        "request": request,
        "firebase_Config": get_firebase_config(),
        "url_for": request.url_for  # 핵심: 템플릿에서 url_for 사용 가능하게 넘김
    })

@app.get("/test1", response_class=HTMLResponse)
async def test1(request: Request):
    return templates.TemplateResponse("index1.html", {
        "request": request,
        "firebase_Config": get_firebase_config()
    })

@app.get("/signUp", response_class=HTMLResponse)
async def signUp(request: Request):
    return templates.TemplateResponse("signUp.html", {
        "request": request,
        "firebase_Config": get_firebase_config(),
        "url_for": request.url_for
    })

@app.get("/test2", response_class=HTMLResponse)
async def test2(request: Request):
    return templates.TemplateResponse("index2.html", {
        "request": request,
        "firebase_Config": get_firebase_config()
    })

@app.get("/add_friend", response_class=HTMLResponse)
async def add_friend(request: Request):
    return templates.TemplateResponse("add_friend.html", {
        "request": request,
        "firebase_Config": get_firebase_config()
    })

@app.get("/notifications", response_class=HTMLResponse)
async def notifications(request: Request):
    return templates.TemplateResponse("notifications.html", {
        "request": request,
        "firebase_Config": get_firebase_config()
    })

@app.get("/danger_data")
async def get_danger_data():
    return FileResponse("danger.json", media_type="application/json")

# 데이터를 받는 엔드 포인트
@app.post("/upload")
async def upload_data(request: Request):
    data = await request.json()
    
    uid = data.get("uid")
    danger_level = data.get("dangerLevel")
    symptoms = data.get("symptoms")

    # Firebase 경로
    ref = db.reference(f"users/{uid}/reports/{timestamp}")
    ref.set({
        "symptoms": symptoms,
        "dangerLevel": danger_level
    })


    return {"result": "ok", "stored": data}