from fastapi import FastAPI, Request, Form, HTTPException, status, Depends, Body
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import (
    create_engine, Column, BigInteger, String, SmallInteger, 
    DECIMAL, Enum, JSON, TIMESTAMP, func    
)
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os, enum
import mysql.connector
import bcrypt
import jwt
from datetime import datetime, timedelta

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# 환경설정
SECRET_KEY = os.getenv("SECRET_KEY", "your_default_key")
ALGORITHM = "HS256"

app = FastAPI()

# 정적 파일 경로 등록
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

def get_db():
    return mysql.connector.connect(
        host="localhost", user="root", password="Nohjinc12!!", database="sos_navigation"
    )

def get_user_id_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["user_id"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

def is_valid_email(email):
    import re
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

# ========== 회원가입 ==============
@app.post("/signUp")
async def signUp(email: str = Form(...), password: str = Form(...)):
    if not email or not password:
        return {"success": False, "msg": "이메일과 비밀번호를 모두 입력하세요."}
    if not is_valid_email(email):
        return {"success": False, "msg": "이메일 형식이 올바르지 않습니다."}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return {"success": False, "msg": "이미 가입된 이메일입니다."}
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, hashed_pw))
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True, "msg": "회원가입 성공!"}

# ========== 로그인 ==============
@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    if not email or not password:
        return {"success": False, "msg": "이메일과 비밀번호를 모두 입력하세요."}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password FROM users WHERE email=%s", (email,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return {"success": False, "msg": "존재하지 않는 이메일입니다."}
    user_id, hashed_pw = row
    if bcrypt.checkpw(password.encode("utf-8"), hashed_pw.encode("utf-8")):
        token = jwt.encode({"user_id": user_id, "email": email, "exp": datetime.utcnow() + timedelta(hours=24)}, SECRET_KEY, algorithm=ALGORITHM)
        cursor.close()
        conn.close()
        return {"success": True, "msg": "로그인 성공!", "token": token}
    else:
        cursor.close()
        conn.close()
        return {"success": False, "msg": "비밀번호가 일치하지 않습니다."}

# ========== 내 정보 ==============
@app.get("/me")
async def get_my_info(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "): raise HTTPException(status_code=401, detail="인증 정보 없음")
    token = auth.replace("Bearer ", "")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return {"user_id": payload["user_id"], "email": payload["email"]}

# ========== 위치 저장/조회 ===========
class Location(BaseModel):
    lat: float
    lng: float

@app.post("/location")
async def save_location(location: Location, request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "): raise HTTPException(status_code=401, detail="인증 정보 없음")
    token = auth.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO locations (user_id, lat, lng) VALUES (%s, %s, %s)", (user_id, location.lat, location.lng))
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True}

@app.get("/location/{user_id}")
async def get_location(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT lat, lng FROM locations WHERE user_id=%s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return {"lat": row[0], "lng": row[1]}
    return JSONResponse({"msg": "위치 없음"}, status_code=404)

# ========== 위치 삭제(공유 중지) =============

@app.delete("/location")
async def delete_location(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "): 
        raise HTTPException(status_code=401, detail="인증 정보 없음")
    token = auth.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM locations WHERE user_id=%s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True, "msg": "위치 정보가 삭제되었습니다."}

# ========== 친구 요청(이메일 기반) =============
class FriendRequestModel(BaseModel):
    email: str

@app.post("/friend_request")
async def send_friend_request(data: FriendRequestModel, request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "): raise HTTPException(status_code=401, detail="인증 정보 없음")
    token = auth.replace("Bearer ", "")
    from_user_id = get_user_id_from_token(token)
    email = data.email.strip().lower()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
    to_row = cursor.fetchone()
    if not to_row:
        cursor.close()
        conn.close()
        return {"success": False, "msg": "해당 이메일 사용자가 없습니다."}
    to_user_id = to_row[0]
    if to_user_id == from_user_id:
        cursor.close()
        conn.close()
        return {"success": False, "msg": "자기 자신에게 친구 요청 불가"}
    cursor.execute("SELECT * FROM friends WHERE user_id=%s AND friend_user_id=%s", (from_user_id, to_user_id))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return {"success": False, "msg": "이미 친구입니다."}
    cursor.execute("SELECT * FROM friend_requests WHERE from_user_id=%s AND to_user_id=%s AND status='pending'", (from_user_id, to_user_id))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return {"success": False, "msg": "이미 요청을 보냈습니다."}
    cursor.execute(
        "INSERT INTO friend_requests (from_user_id, to_user_id, status, created_at) VALUES (%s, %s, 'pending', %s)",
        (from_user_id, to_user_id, datetime.now())
    )
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True}

# ========== 받은 친구 요청 목록 ===========
@app.get("/friend_requests")
async def get_friend_requests(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "): raise HTTPException(status_code=401, detail="인증 정보 없음")
    token = auth.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT fr.id, fr.from_user_id, u.email
        FROM friend_requests fr
        JOIN users u ON fr.from_user_id = u.id
        WHERE fr.to_user_id = %s AND fr.status = 'pending'
        """,
        (user_id,)
    )
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

# ========== 친구 요청 수락/거절 ===========
class FriendRequestRespondModel(BaseModel):
    from_id: int
    accept: bool

@app.post("/friend_request/respond")
async def respond_friend_request(data: FriendRequestRespondModel, request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "): raise HTTPException(status_code=401, detail="인증 정보 없음")
    token = auth.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    from_user_id = data.from_id
    accept = data.accept
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM friend_requests WHERE from_user_id=%s AND to_user_id=%s AND status='pending'",
        (from_user_id, user_id)
    )
    req = cursor.fetchone()
    if not req:
        cursor.close()
        conn.close()
        return {"success": False, "msg": "친구 요청이 없습니다."}
    if accept:
        cursor.execute("INSERT IGNORE INTO friends (user_id, friend_user_id) VALUES (%s, %s)", (user_id, from_user_id))
        cursor.execute("INSERT IGNORE INTO friends (user_id, friend_user_id) VALUES (%s, %s)", (from_user_id, user_id))
        cursor.execute(
            "UPDATE friend_requests SET status='accepted' WHERE from_user_id=%s AND to_user_id=%s",
            (from_user_id, user_id)
        )
    else:
        cursor.execute(
            "UPDATE friend_requests SET status='denied' WHERE from_user_id=%s AND to_user_id=%s",
            (from_user_id, user_id)
        )
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True}

# ============ 친구 목록 =============
@app.get("/friends")
async def get_friends(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "): raise HTTPException(status_code=401, detail="인증 정보 없음")
    token = auth.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT u.id, u.email FROM friends f JOIN users u ON f.friend_user_id = u.id WHERE f.user_id=%s", (user_id,)
    )
    friends = cursor.fetchall()
    cursor.close()
    conn.close()
    return friends

# ========== 알림(위치 요청) ===========
class Notification(BaseModel):
    to_user_id: int
    from_user_id: int
    email: str
    type: str

# 알림 생성
@app.post("/notify")
async def notify(n: Notification, request: Request):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notifications (to_user_id, from_user_id, email, type, timestamp) VALUES (%s, %s, %s, %s, %s)",
        (n.to_user_id, n.from_user_id, n.email, n.type, datetime.now())
    )
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True}

# 알림 조회
@app.get("/notifications")
async def get_notifications(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "): raise HTTPException(status_code=401, detail="인증 정보 없음")
    token = auth.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, from_user_id, email, timestamp FROM notifications WHERE to_user_id=%s ORDER BY timestamp DESC LIMIT 30", (user_id,)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    # [{id, from_id, email, timestamp}]
    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "from_id": row["from_user_id"],
            "email": row["email"],
            "timestamp": int(row["timestamp"].timestamp()*1000) if row["timestamp"] else None
        })
    return result
