import math
import os
import json
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Body, Query, WebSocket
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, Float, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import pandas as pd

# 거리 계산 함수 (Haversine formula)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c  # in kilometers

# Database setup
DATABASE_URL = "sqlite:///hospital.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database models
class Marker(Base):
    __tablename__ = "markers"
    id = Column(Integer, primary_key=True, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    layer = Column(Integer, nullable=False, default=1)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)

# Remove existing hospital.db to ensure fresh schema
if os.path.exists('hospital.db'):
    print("Removing existing hospital.db to create fresh schema")
    os.remove('hospital.db')

Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# WebSocket 클라이언트 저장
connected_clients = set()

# WebSocket 엔드포인트
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()  # 클라이언트 메시지 대기
    except:
        connected_clients.remove(websocket)

# WebSocket 메시지 브로드캐스트
async def broadcast(message: dict):
    for client in connected_clients:
        try:
            await client.send_json(message)
        except:
            connected_clients.remove(client)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Notify data change
async def notify_data_change(layer: int, db: Session, action: str):
    timestamp = str(datetime.now().timestamp())
    # 파일 기반 알림 (호환성 유지)
    with open("Kim/static/reload.txt", "w") as f:
        f.write(json.dumps({"timestamp": timestamp, "layer": int(layer), "action": action}))
    # WebSocket 알림
    await broadcast({"timestamp": timestamp, "layer": int(layer), "action": action})
    export_data_to_json(db, layer)

# Export data to JSON
def export_data_to_json(db: Session, layer: int, min_lat: float = None, max_lat: float = None, min_lon: float = None, max_lon: float = None):
    query = db.query(Marker).filter(Marker.layer == layer)
    if min_lat is not None and max_lat is not None and min_lon is not None and max_lon is not None:
        query = query.filter(Marker.lat >= min_lat, Marker.lat <= max_lat, Marker.lon >= min_lon, Marker.lon <= max_lon)
    markers = query.limit(10000).all()
    data = {
        f"markers_{layer}": [
            {"id": m.id, "lat": m.lat, "lon": m.lon, "name": m.name, "phone": m.phone}
            for m in markers
        ]
    }
    with open(f"Kim/static/data_{layer}.json", "w") as f:
        json.dump(data, f)

# Load hospital data (Japan)
def load_hospital_data_to_db_jp(db: Session, max_rows: int = 10000) -> int:
    if not os.path.exists('Kim/data_japan_1.csv'):
        print("data_japan_1.csv not found")
        return 0
    print("Starting to load hospital data")
    df = pd.read_csv('Kim/data_japan_1.csv')
    column_mapping = {
        'ID': 'hospital_id',
        '正式名称': 'hospital_name',
        '機関区分': 'type_code',
        '所在地座標（経度）': 'coord_x',
        '所在地座標（緯度）': 'coord_y',
        '案内用ホームページアドレス': 'phone'
    }
    df = df.rename(columns=column_mapping)
    print(f"Initial rows: {len(df)}")
    df = df.dropna(subset=['hospital_name', 'type_code', 'coord_x', 'coord_y', 'phone'])
    print(f"Rows after dropna: {len(df)}")
    df['type_code'] = pd.to_numeric(df['type_code'], errors='coerce').astype('Int64')
    df = df.dropna(subset=['type_code'])
    print(f"Processing {len(df)} hospitals")
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
        notify_data_change(int(layer), db, action="add")
    print(f"Finished loading {len(df)} hospitals")
    return len(df)

# Endpoints
@app.get("/")
async def serve_map():
    return FileResponse("Kim/static/index.html")

@app.get("/reload.txt")
async def get_reload():
    return FileResponse("Kim/static/reload.txt")

@app.get("/data/{layer}")
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

@app.post("/load-hospitals_jp")
async def load_hospitals_jp(db: Session = Depends(get_db)):
    count = load_hospital_data_to_db_jp(db, max_rows=10000)
    return {"message": f"Inserted {count} hospitals"}

@app.post("/nearest-hospitals")
async def get_nearest_hospitals(
    type_code: int = Body(...),
    lat: float = Body(...),
    lon: float = Body(...),
    db: Session = Depends(get_db)
):
    # 유효성 검사
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise HTTPException(status_code=400, detail="Invalid lat/lon values")
    # 마커 추가
    new_marker = Marker(lat=lat, lon=lon, layer=999)
    db.add(new_marker)
    db.commit()
    await notify_data_change(999, db, action="add")
    # 같은 타입코드 병원 목록
    hospitals = db.query(Marker).filter(Marker.layer == type_code).all()
    # 거리순 정렬
    hospitals_sorted = sorted(
        hospitals,
        key=lambda m: haversine(lat, lon, m.lat, m.lon)
    )
    nearest = hospitals_sorted[:5]
    return {
        "input": {"lat": lat, "lon": lon, "type_code": type_code},
        "nearest": [
            {"id": h.id, "lat": h.lat, "lon": h.lon, "name": h.name, "phone": h.phone}
            for h in nearest
        ]
    }

@app.delete("/confirm-marker/{marker_id}")
async def confirm_marker(marker_id: int, db: Session = Depends(get_db)):
    marker = db.query(Marker).filter(Marker.id == marker_id, Marker.layer == 999).first()
    if not marker:
        raise HTTPException(status_code=404, detail="Marker not found or not in layer 999")
    db.delete(marker)
    db.commit()
    await notify_data_change(999, db, action="delete")
    return {"message": f"Marker {marker_id} removed from layer 999"}