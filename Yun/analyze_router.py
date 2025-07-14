"""
Yun/analyze_router.py   —   증상 분석 + DB 저장 + STT + 결과 파일
"""

from __future__ import annotations
from typing import Optional
import io, json, os, re, datetime, logging

from fastapi import APIRouter, Form, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from PIL import Image
import google.generativeai as genai
from google.cloud import speech
from pathlib import Path
from dotenv import load_dotenv
import os, logging

# ── DB 모델 ──────────────────────────────────────────
from .db import SessionLocal, SymLog, Risk          # ★ 중요

BASE = Path(__file__).resolve().parents[1]          # /home/SoS/SOS_project
load_dotenv(BASE / ".env", override=True)

log = logging.getLogger("uvicorn.error")
key_head = (os.getenv("GOOGLE_API_KEY") or "EMPTY")[:6]   
log.warning("KEY 앞 6글자 ⇒ %s", key_head)

# ── Gemini 초기화 ────────────────────────────────────
log = logging.getLogger("uvicorn.error")
API_KEY = os.getenv("GOOGLE_API_KEY", "")
if not API_KEY:
    log.error("GOOGLE_API_KEY 가 비어 있습니다 — .env 확인")
genai.configure(api_key=API_KEY)
GEMINI = genai.GenerativeModel("models/gemini-1.5-flash")

try:
    genai.configure(api_key=API_KEY)
    GEMINI = genai.GenerativeModel("models/gemini-1.5-flash")
except Exception as e:
    log.error("Gemini 초기화 실패 → %s", e)       # ★ 추가
    raise


# ── STT 서비스 계정 ──────────────────────────────────
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS", "/home/SoS/keys/stt.json"
)

# ── 프롬프트·과목 리스트 ─────────────────────────────
PROMPT_JSON = json.loads((BASE / "assets" / "analyze_prompt.json").read_text("utf-8"))
SUBJECT_LIST = (BASE / "assets" / "subject_list.txt").read_text("utf-8")
BASE_PROMPT = "\n".join(
    line if "불러옴" not in line else f"진료과목 리스트:\n{SUBJECT_LIST}"
    for line in PROMPT_JSON["analysis_prompt"]
)

router = APIRouter(prefix="/analyze", tags=["Analyze"])
templates = Jinja2Templates(directory=BASE / "web")

# ─────────────────────────────────────────────────────
@router.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@router.post("/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    data = await audio.read()
    stt_text = ""
    if data:
        client = speech.SpeechClient()
        cfg = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code="ko-KR",
        )
        res = client.recognize(config=cfg, audio=speech.RecognitionAudio(content=data))
        stt_text = "".join(r.alternatives[0].transcript for r in res.results)
    return {"stt_text": stt_text}

# ── 메인 분석 엔드포인트 ─────────────────────────────
@router.post("", response_class=JSONResponse)
async def analyze(
    symptom: str = Form(""),
    image: UploadFile | None = File(None),
    latitude: str | None = Form(None),
    longitude: str | None = Form(None),
    uid: int = Form(0),
):
    symptom = symptom.strip()
    if not symptom:
        raise HTTPException(400, "증상 텍스트를 입력하세요.")

    # 1) 이미지 읽기(선택)
    img: Optional[Image.Image] = None
    if image and image.filename and image.content_type.startswith("image/"):
        try:
            img = Image.open(io.BytesIO(await image.read()))
        except Exception:
            pass

    # 2) Gemini 호출
    prompt = f"{BASE_PROMPT}\n\n사용자 증상: {symptom}"
    try:
        res = GEMINI.generate_content([prompt, img] if img else [prompt])
        parsed = json.loads(re.search(r"\{[\s\S]*?\}", res.text).group())
    except Exception as e:
        log.error("Gemini 오류 → %s", e)
        parsed = {}

    # 3) 파싱 실패 시 예비 값
    if not parsed:
        parsed = {
            "의심 질환": "원인 미상",
            "위험도": "알수",
            "진료과목 코드": "0",
            "진료과목 명칭": "일반",
        }

    # 위치 부여
    if latitude and longitude:
        parsed["위치"] = {"latitude": latitude, "longitude": longitude}

    # 4) DB INSERT
    risk_raw = parsed.get("위험도", "알수").replace(" ", "")
    risk_map = {"낮음": "낮음", "중간": "중간", "높음": "높음",
                "심각": "심각", "알수": "알수", "알수없음": "알수"}
    risk_clean = risk_map.get(risk_raw, "알수")

    dcode_raw = str(parsed.get("진료과목 코드", "0")).strip()
    dcode = int(dcode_raw) if dcode_raw.isdigit() else 0

    db = SessionLocal()
    row = SymLog(
        uid=uid,
        sym=symptom,
        dis=parsed.get("의심 질환"),
        risk=Risk(risk_clean),
        dcode=dcode,
        dname=parsed.get("진료과목 명칭"),
        lat=float(latitude) if latitude else None,
        lng=float(longitude) if longitude else None,
        raw=parsed,
    )
    db.add(row); db.commit(); record_id = row.id; db.close()

    # 5) 결과 JSON 파일 저장
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    (BASE / "web" / "result").mkdir(exist_ok=True)
    with open(BASE / "web" / "result" / f"result_{ts}.json", "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    guide = parsed.get("가이드", "필요 시 전문의 상담을 권장합니다.")
    return {"record_id": record_id, "reply": guide}
