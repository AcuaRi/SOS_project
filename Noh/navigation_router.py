# routers
from fastapi import APIRouter, Request, Form, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import (create_engine, Column, BigInteger, String, SmallInteger, DECIMAL, Enum, JSON, TIMESTAMP, func)
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from login import schemas, crud, auth, models
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from decimal import Decimal
from Yun.db import SessionLocal as get_db_session 
from dotenv import load_dotenv
import mysql.connector
import bcrypt
import jwt
from datetime import datetime, timedelta
import os, re, enum

load_dotenv("/home/SoS/SOS_project/Noh/.env")

# 환경설정
SECRET_KEY = os.getenv("SECRET_KEY", "your_default_key")
ALGORITHM = "HS256"

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="sos_user",
        password="SosPass123!",
        database="sos"
    )

# def get_user_id_from_token(token: str):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         return payload["user_id"]
#     except Exception:
#         raise HTTPException(status_code=401, detail="Invalid token")

# def is_valid_email(email):
#     pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
#     return re.match(pattern, email) is not None

router = APIRouter(prefix="/navigation", tags=["navigation"])

# =========== 회원가입 ===========

# @router.post("/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
# def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
#     db_user = crud.get_user_by_email(db, email=user.email)
#     if db_user:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
#     new_user = crud.create_user(db=db, user=user)
#     return new_user

# # =========== 로그인 ==============
# @router.post("/auth/login")
# def login_user(user: schemas.UserLogin, db: Session = Depends(get_db)):
#     db_user = crud.get_user_by_email(db, email=user.email)
#     if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

#     # JWT 발급
#     payload = {
#         "user_id": db_user.id,
#         "email": db_user.email
#     }
#     access_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
#     return {"access_token": access_token, "token_type": "bearer"}

# # =========== 내 정보 ==============
# @router.get("/me")
# async def get_my_info(request: Request):
#     auth = request.headers.get("Authorization", "")
#     if not auth.startswith("Bearer "): raise HTTPException(status_code=401, detail="인증 정보 없음")
#     token = auth.replace("Bearer ", "")
#     payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#     return {"user_id": payload["user_id"], "email": payload["email"]}

# ========== 위치 저장/조회 ==========

class LocationModel(BaseModel):
    email: str
    lat: Decimal
    lng: Decimal

    
@router.post("/sos_location")
async def save_location(location: LocationModel, request: Request):
    # auth = request.headers.get("Authorization", "")
    #if not auth.startswith("Bearer "): raise HTTPException(status_code=401, detail="인증 정보 없음")
    #token = auth.replace("Bearer ", "")
    #user_id = get_user_id_from_token(token)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sos_location (email, lat, lng) VALUES (%s, %s, %s)", (location.email, location.lat, location.lng))
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True}

@router.get("/location/{user_id}")
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
@router.delete("/location")
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
    from_email: str
    to_email: str

@router.post("/friend_request")
async def send_friend_request(data: FriendRequestModel, request: Request):
    #auth = request.headers.get("Authorization", "")
    #if not auth.startswith("Bearer "): raise HTTPException(status_code=401, detail="인증 정보 없음")
    #token = auth.replace("Bearer ", "")
    #from_user_id = get_user_id_from_token(token)
    text = data.from_email.strip().lower()
    from_email = text.replace('"', '').replace('\\', '')
    print(from_email)
    #from_email = data.from_email.strip().lower()
    to_email = data.to_email.strip().lower()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email=%s", (to_email,))
    to_row = cursor.fetchone()
    if not to_row:
        cursor.close()
        conn.close()
        return {"success": False, "msg": "해당 이메일 사용자가 없습니다."}
    to_user_id = to_row[0]
    if to_user_id == data.from_email:
        cursor.close()
        conn.close()
        return {"success": False, "msg": "자기 자신에게 친구 요청 불가"}
    cursor.execute("SELECT * FROM sos_friends WHERE email=%s AND friends1=%s", (from_email, to_email))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return {"success": False, "msg": "이미 친구입니다."}
    cursor.execute("SELECT * FROM friends_requests WHERE email=%s AND friends1=%s AND status='0'", (from_email, to_email))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return {"success": False, "msg": "이미 요청을 보냈습니다."}
    cursor.execute(
        "INSERT INTO friends_requests (email, friends1, status) VALUES (%s, %s, '0')",
        (from_email, to_email)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return {"success": True}

# ========== 받은 친구 요청 목록 ===========
class FriendListModel(BaseModel):
    from_email: str
    
@router.post("/friend_requests")
async def get_friend_requests(data: FriendListModel, request: Request):
    # auth = request.headers.get("Authorization", "")
    # if not auth.startswith("Bearer "): raise HTTPException(status_code=401, detail="인증 정보 없음")
    # token = auth.replace("Bearer ", "")
    # user_id = get_user_id_from_token(token)
    text = data.from_email.strip().lower()
    from_email = text.replace('"', '').replace('\\', '')
    print(data.from_email)
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        select * from sos.friends_requests where friends1 = %s
        """,
        [from_email]
    )
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    print(result)
    return result

# ========== 친구 요청 수락/거절 ===========
class FriendRequestRespondModel(BaseModel):
    from_id: int
    accept: bool

@router.post("/friend_request/respond")
async def respond_friend_request(data: FriendRequestRespondModel, request: Request):
    # auth = request.headers.get("Authorization", "")
    # if not auth.startswith("Bearer "): raise HTTPException(status_code=401, detail="인증 정보 없음")
    # token = auth.replace("Bearer ", "")
    # user_id = get_user_id_from_token(token)
    from_user_id = data.from_id
    accept = data.accept
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT email FROM friend_requests WHERE from_user_id=%s AND to_user_id=%s AND status='0'",
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
@router.get("/friends")
async def get_friends(request: Request):
    # auth = request.headers.get("Authorization", "")
    # if not auth.startswith("Bearer "): raise HTTPException(status_code=401, detail="인증 정보 없음")
    # token = auth.replace("Bearer ", "")
    # user_id = get_user_id_from_token(token)
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT u.id, u.email FROM friends f JOIN users u ON f.friend_user_id = u.id WHERE f.user_id=%s", (user_id,)
    )
    friends = cursor.fetchall()
    cursor.close()
    conn.close()
    return friends

# ======== 알림(위치 요청) =========
class Notification(BaseModel):
    to_user_id: int
    from_user_id: int
    email: str
    type: str

# ========== 알림 생성 ===========
@router.post("/notify")
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

# ========== 알림 조회 ==========
@router.get("/notifications")
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
    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "from_id": row["from_user_id"],
            "email": row["email"],
            "timestamp": int(row["timestamp"].timestamp()*1000) if row["timestamp"] else None
        })
    return result
