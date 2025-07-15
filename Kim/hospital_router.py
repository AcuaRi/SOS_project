from fastapi import APIRouter, Depends, HTTPException, Body, Query, WebSocket, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, Float, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import pandas as pd
import math, json, os, asyncio

router = APIRouter(prefix="/hospital", tags=["Map"])

# 거리 계산 함수
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Database 설정
DATABASE_URL = "sqlite:///hospital.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Marker(Base):
    __tablename__ = "markers"
    id = Column(Integer, primary_key=True, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    layer = Column(Integer, nullable=False, default=1)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)

if os.path.exists('hospital.db'):
    print("Removing existing hospital.db to create fresh schema")
    os.remove('hospital.db')

Base.metadata.create_all(bind=engine)

connected_clients = set()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        connected_clients.remove(websocket)

async def broadcast(message: dict):
    for client in connected_clients.copy():
        try:
            await client.send_json(message)
        except:
            connected_clients.remove(client)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def notify_data_change(layer: int, db: Session, action: str):
    timestamp = str(datetime.now().timestamp())
    with open("Kim/static/reload.txt", "w") as f:
        f.write(json.dumps({"timestamp": timestamp, "layer": int(layer), "action": action}))
    await broadcast({"timestamp": timestamp, "layer": int(layer), "action": action})
    export_data_to_json(db, layer)

def export_data_to_json(db: Session, layer: int, min_lat=None, max_lat=None, min_lon=None, max_lon=None):
    query = db.query(Marker).filter(Marker.layer == layer)
    if None not in (min_lat, max_lat, min_lon, max_lon):
        query = query.filter(Marker.lat >= min_lat, Marker.lat <= max_lat,
                             Marker.lon >= min_lon, Marker.lon <= max_lon)
    markers = query.limit(10000).all()
    data = {
        f"markers_{layer}": [
            {"id": m.id, "lat": m.lat, "lon": m.lon, "name": m.name, "phone": m.phone}
            for m in markers
        ]
    }
    with open(f"Kim/static/data_{layer}.json", "w") as f:
        json.dump(data, f)

def load_hospital_data_to_db_jp(db: Session, max_rows: int = 10000) -> int:
    if not os.path.exists('Kim/data_japan_1.csv'):
        print("data_japan_1.csv not found")
        return 0
    df = pd.read_csv('Kim/data_japan_1.csv')
    df = df.rename(columns={
        'ID': 'hospital_id',
        '正式名称': 'hospital_name',
        '機関区分': 'type_code',
        '所在地座標（経度）': 'coord_x',
        '所在地座標（緯度）': 'coord_y',
        '案内用ホームページアドレス': 'phone'
    }).dropna(subset=['hospital_name', 'type_code', 'coord_x', 'coord_y', 'phone'])
    df['type_code'] = pd.to_numeric(df['type_code'], errors='coerce').astype('Int64')
    df = df.dropna(subset=['type_code'])

    db.query(Marker).delete()
    db.commit()

    for _, row in df.iterrows():
        marker = Marker(
            lat=row['coord_y'],
            lon=row['coord_x'],
            layer=int(row['type_code']),
            name=row['hospital_name'],
            phone=str(row['phone']) if pd.notna(row['phone']) else None
        )
        db.add(marker)
    db.commit()
    for layer in df['type_code'].unique():
        if layer != 999:  # 레이어 999는 사용자 요청 마커로, 초기 로드 시 알림 제외
            asyncio.create_task(notify_data_change(int(layer), db, action="add"))
    return len(df)

# Jinja2 템플릿 설정
templates = Jinja2Templates(directory="Kim/templates")

# ────────────────────── 라우터 엔드포인트 ──────────────────────

@router.get("/")
async def serve_map():
    return FileResponse("Kim/static/index_new.html")

@router.get("/user-map", response_class=HTMLResponse)
async def serve_user_map(request: Request):
    return templates.TemplateResponse("user_map.html", {"request": request})

@router.get("/reload.txt")
async def get_reload():
    return FileResponse("Kim/static/reload.txt")

@router.get("/data/{layer}")
async def get_data(
    layer: int,
    min_lat: float = Query(None),
    max_lat: float = Query(None),
    min_lon: float = Query(None),
    max_lon: float = Query(None),
    db: Session = Depends(get_db)
):
    export_data_to_json(db, layer, min_lat, max_lat, min_lon, max_lon)
    return FileResponse(f"Kim/static/data_{layer}.json")

@router.get("/marker/{marker_id}")
async def get_marker(marker_id: int, db: Session = Depends(get_db)):
    marker = db.query(Marker).filter(Marker.id == marker_id, Marker.layer == 999).first()
    if not marker:
        raise HTTPException(status_code=404, detail="Marker not found or not in layer 999")
    return {
        "id": marker.id,
        "lat": marker.lat,
        "lon": marker.lon,
        "name": marker.name,
        "phone": marker.phone,
        "type_code": 1  # 기본 type_code, 필요 시 동적 설정 가능
    }

@router.post("/load-hospitals_jp")
async def load_hospitals_jp(db: Session = Depends(get_db)):
    count = load_hospital_data_to_db_jp(db)
    return {"message": f"Inserted {count} hospitals"}

@router.post("/nearest-hospitals")
async def get_nearest_hospitals(
    type_code: int = Body(...),
    lat: float = Body(...),
    lon: float = Body(...),
    name: str = Body(...),
    phone: str = Body(...),
    db: Session = Depends(get_db)
):
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise HTTPException(status_code=400, detail="Invalid lat/lon values")

    new_marker = Marker(lat=lat, lon=lon, layer=999, name=name, phone=phone)
    db.add(new_marker)
    db.commit()
    await notify_data_change(999, db, action="add")

    hospitals = db.query(Marker).filter(Marker.layer == type_code).all()
    hospitals_sorted = sorted(hospitals, key=lambda m: haversine(lat, lon, m.lat, m.lon))
    nearest = hospitals_sorted[:5]

    return {
        "marker_id": new_marker.id,
        "input": {
            "lat": 35.6762,
            "lon": 139.6503,
            "type_code": 1,
            "name": "User",
            "phone": "123-456-7890"
        },
        "nearest": [
            {"id": h.id, "lat": h.lat, "lon": h.lon, "name": h.name, "phone": h.phone}
            for h in nearest
        ]
    }

@router.delete("/confirm-marker/{marker_id}")
async def confirm_marker(marker_id: int, db: Session = Depends(get_db)):
    marker = db.query(Marker).filter(Marker.id == marker_id, Marker.layer == 999).first()
    if not marker:
        raise HTTPException(status_code=404, detail="Marker not found or not in layer 999")
    db.delete(marker)
    db.commit()
    await notify_data_change(999, db, action="delete")
    return {"message": f"Marker {marker_id} removed from layer 999"}