import pandas as pd
from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Integer, Float, String, create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
import json
import os
from datetime import datetime
from fastapi import HTTPException
from fastapi import Query
from fastapi import Body
import math

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

# Layer colors
LAYER_COLORS = {
    1: 'blue', 2: 'red', 3: 'green', 4: 'orange', 5: 'purple',
    6: 'brown', 7: 'pink', 8: 'gray', 9: 'black', 10: 'cyan',
    29: 'yellow', 31: 'darkgreen'
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Notify data change
def notify_data_change(layer: int, db: Session):
    with open("Kim/static/reload.txt", "w") as f:
        f.write(json.dumps({"timestamp": datetime.now().timestamp(), "layer": int(layer)}))  # Ensure int
    export_data_to_json(db, layer)


# Load hospital data (limited to 10000 rows, all type codes)
def load_hospital_data_to_db(db: Session, max_rows: int = 10000) -> int:
    if not os.path.exists('Kim/data.xlsx'):
        print("data.xlsx not found")
        return 0
    print("Starting to load hospital data")
    df = pd.read_excel('Kim/data.xlsx')
    column_mapping = {
        '암호화요양기호': 'hospital_id',
        '요양기관명': 'hospital_name',
        '종별코드': 'type_code',
        '좌표(X)': 'coord_x',
        '좌표(Y)': 'coord_y',
        '전화번호': 'phone'
    }
    df = df.rename(columns=column_mapping)
    print(f"Initial rows: {len(df)}")
    df = df.dropna(subset=['hospital_name', 'type_code', 'coord_x', 'coord_y', 'phone'])
    print(f"Rows after dropna: {len(df)}")
    df['type_code'] = pd.to_numeric(df['type_code'], errors='coerce').astype('Int64')
    df = df.dropna(subset=['type_code'])

    # Limit to max_rows
    #df = df.head(max_rows)

    print(f"Processing {len(df)} hospitals")
    db.query(Marker).delete()
    db.commit()
    for _, row in df.iterrows():
        marker = Marker(
            lat=row['coord_y'],
            lon=row['coord_x'],
            layer=int(row['type_code']),  # Convert Int64 to int
            name=row['hospital_name'],
            phone=str(row['phone']) if pd.notna(row['phone']) else None
        )
        db.add(marker)
    db.commit()
    for layer in df['type_code'].unique():
        notify_data_change(int(layer), db)  # Convert Int64 to int
    print(f"Finished loading {len(df)} hospitals")
    return len(df)

# Load hospital data (limited to 10000 rows, all type codes)
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

    # Limit to max_rows
    #df = df.head(max_rows)

    print(f"Processing {len(df)} hospitals")
    db.query(Marker).delete()
    db.commit()
    for _, row in df.iterrows():
        marker = Marker(
            lat=row['coord_y'],
            lon=row['coord_x'],
            layer=int(row['type_code']),  # Convert Int64 to int
            name=row['hospital_name'],
            phone=str(row['phone']) if pd.notna(row['phone']) else None
        )
        db.add(marker)
    db.commit()
    for layer in df['type_code'].unique():
        notify_data_change(int(layer), db)  # Convert Int64 to int
    print(f"Finished loading {len(df)} hospitals")
    return len(df)

# Export data to JSON
def export_data_to_json(db: Session, layer: int, min_lat: float = None, max_lat: float = None, min_lon: float = None, max_lon: float = None):
    query = db.query(Marker).filter(Marker.layer == layer)
    if min_lat is not None and max_lat is not None and min_lon is not None and max_lon is not None:
        query = query.filter(Marker.lat >= min_lat, Marker.lat <= max_lat, Marker.lon >= min_lon, Marker.lon <= max_lon)
    markers = query.limit(5000).all()  # 최대 1000개로 제한
    data = {
        f"markers_{layer}": [
            {"id": m.id, "lat": m.lat, "lon": m.lon, "name": m.name, "phone": m.phone}
            for m in markers
        ]
    }
    with open(f"Kim/static/data_{layer}.json", "w") as f:
        json.dump(data, f)


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


@app.post("/load-hospitals")
async def load_hospitals(db: Session = Depends(get_db)):
    count = load_hospital_data_to_db(db, max_rows=10000)
    return {"message": f"Inserted {count} hospitals"}

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
    # 마커 누적 저장 (기존 999 레이어 삭제 생략)
    new_marker = Marker(lat=lat, lon=lon, layer=999)
    db.add(new_marker)
    db.commit()
    notify_data_change(999, db)

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
    notify_data_change(999, db)
    return {"message": f"Marker {marker_id} removed from layer 999"}

