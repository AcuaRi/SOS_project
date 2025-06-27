#김종환
import pandas as pd
from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Integer, Float, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import json
import os
from datetime import datetime
from fastapi import HTTPException

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
DATABASE_URL = "sqlite:///map.db"
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


class PathPoint(Base):
    __tablename__ = "paths"
    id = Column(Integer, primary_key=True, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    layer = Column(Integer, nullable=False, default=1)


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
    with open("static/reload.txt", "w") as f:
        f.write(json.dumps({"timestamp": datetime.now().timestamp(), "layer": int(layer)}))  # Ensure int
    export_data_to_json(db, layer)


# Load hospital data (limited to 1000 rows or specific type_codes)
def load_hospital_data_to_db(db: Session, max_rows: int = 1000, type_codes: list = [1, 29]) -> int:
    if not os.path.exists('data.xlsx'):
        print("data.xlsx not found")
        return 0
    print("Starting to load hospital data")
    df = pd.read_excel('data.xlsx')
    column_mapping = {
        '암호화요양기호': 'hospital_id',
        '요양기관명': 'hospital_name',
        '종별코드': 'type_code',
        '좌표(X)': 'coord_x',
        '좌표(Y)': 'coord_y'
    }
    df = df.rename(columns=column_mapping)
    df = df.dropna(subset=['hospital_name', 'type_code', 'coord_x', 'coord_y'])
    df['type_code'] = pd.to_numeric(df['type_code'], errors='coerce').astype('Int64')
    df = df.dropna(subset=['type_code'])

    # Filter by type_codes and limit rows
    df = df[df['type_code'].isin(type_codes)].head(max_rows)

    print(f"Processing {len(df)} hospitals")
    db.query(Marker).delete()
    db.commit()
    for _, row in df.iterrows():
        marker = Marker(
            lat=row['coord_y'],
            lon=row['coord_x'],
            layer=int(row['type_code']),  # Convert Int64 to int
            name=row['hospital_name']
        )
        db.add(marker)
    db.commit()
    for layer in df['type_code'].unique():
        notify_data_change(int(layer), db)  # Convert Int64 to int
    print(f"Finished loading {len(df)} hospitals")
    return len(df)


# Export data to JSON
def export_data_to_json(db: Session, layer: int):
    data = {
        f"markers_{layer}": [
            {"id": m.id, "lat": m.lat, "lon": m.lon, "name": m.name}
            for m in db.query(Marker).filter(Marker.layer == layer).all()
        ],
        f"paths_{layer}": [
            {"id": p.id, "lat": p.lat, "lon": p.lon}
            for p in db.query(PathPoint).filter(PathPoint.layer == layer).all()
        ]
    }
    with open(f"static/data_{layer}.json", "w") as f:
        json.dump(data, f)


# Endpoints
@app.get("/")
async def serve_map():
    return FileResponse("static/index.html")


@app.get("/reload.txt")
async def get_reload():
    return FileResponse("static/reload.txt")


@app.get("/data/{layer}")
async def get_data(layer: int):
    return FileResponse(f"static/data_{layer}.json")


@app.post("/load-hospitals")
async def load_hospitals(db: Session = Depends(get_db)):
    count = load_hospital_data_to_db(db, max_rows=1000, type_codes=[1, 29])
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
            {"id": h.id, "lat": h.lat, "lon": h.lon, "name": h.name}
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


'''
### 2. 실행 순서
1. **app.py 업데이트**:
   - 위 코드를 `app.py`에 덮어씌우거나, `load_hospital_data_to_db`와 `notify_data_change` 함수만 수정:
     ```bash
     nano app.py
     ```
     - 수정 후 저장 (`Ctrl+O`, `Enter`, `Ctrl+X`).

2. **서버 재실행**:
   - 기존 서버 종료:
     ```bash
     lsof -i :8000
     kill -9 <PID>
     ```
   - 서버 시작:
     ```bash
     uvicorn app:app --host 0.0.0.0 --port 8000
     ```
   - 출력 확인:
     ```
     INFO:     Started server process [XXXXX]
     INFO:     Waiting for application startup.
     INFO:     Application startup complete.
     INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
     ```

3. **병원 데이터 로드**:
   - 데이터 로드 호출:
     ```bash
     curl -X POST http://localhost:8000/load-hospitals
     ```
   - 예상 로그:
     ```
     Starting to load hospital data
     Processing 307 hospitals
     Finished loading 307 hospitals
     ```
   - 예상 응답:
     ```json
     {"message":"Inserted 307 hospitals"}
     ```

4. **파일 생성 확인**:
   - 생성된 파일 확인:
     ```bash
     ls map.db static/reload.txt static/data_*.json
     ```
     - 기대: `map.db`, `static/reload.txt`, `static/data_1.json`, `static/data_29.json`
   - `data_1.json` 내용:
     ```bash
     cat static/data_1.json
     ```
   - `reload.txt` 내용:
     ```bash
     cat static/reload.txt
     ```

5. **지도 확인**:
   - 브라우저에서 `http://localhost:8000` 접속.
   - Leaflet 지도와 드롭다운 표시 확인.
   - Layer 1, Layer 29 선택 시 마커 표시 확인.

6. **데이터 갱신 테스트**:
   - 테스트 마커 추가:
     ```python
     # test.py
     from app import add_marker, CoordWithLayer, get_db
     db = next(get_db())
     add_marker(CoordWithLayer(lat=37.5, lon=127.0, layer=1, name="Test Marker"), db)
     ```
     ```bash
     python test.py
     ```
   - `data_1.json` 갱신 확인:
     ```bash
     cat static/data_1.json
     ```
   - 브라우저에서 약 5초 내로 Layer 1에 새 마커 표시 확인.

### 3. 추가 디버깅
- **로그 확인**:
  - `/load-hospitals` 호출 후 터미널 로그 확인.
  - 브라우저 개발자 도구 (`Cmd + Option + J`)에서 `/data/1` 요청 상태 확인 (`200 OK` 기대).
- **데이터 확인**:
  - `data.xlsx`의 `종별코드` 확인:
    ```bash
    python -c "import pandas as pd; print(pd.read_excel('data.xlsx')['종별코드'].unique())"
    ```
    - `1`, `29`가 없으면 `type_codes=[...]`를 조정 (예: 실제 존재하는 코드로).
- **성능 문제**:
  - 307행은 적당하지만, 여전히 느리면 `max_rows` 감소:
    ```python
    count = load_hospital_data_to_db(db, max_rows=100, type_codes=[1, 29])
    ```
  - 또는 지역 필터 추가:
    ```python
    df = df[df['hospital_name'].str.contains('서울', na=False)].head(max_rows)
    ```

### 4. 추가 요청
- **데이터 제한**: `max_rows` 더 줄이거나 다른 `종별코드` 추가?
- **UI 기능**: 마커 추가/삭제 버튼 추가?
- **로그**: 더 자세한 로그 필요?
- **문제 지속**: 추가 오류 로그 또는 `data.xlsx`의 첫 5행 공유:
  ```bash
  python -c "import pandas as pd; print(pd.read_excel('data.xlsx').head())"
  ```
'''
#노진철

#신은총

#윤재용

#이석원