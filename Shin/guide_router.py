# Shin/guide_router.py
"""
sym_log 에 저장된 JSON(증상·질환·위험도·진료과목 …)을 읽어
Google Gemini 를 이용해 ‘6줄 이내 한국어 행동 가이드’를 만들어 돌려주는 라우터
"""
from fastapi import APIRouter, HTTPException
from Yun.db import SessionLocal, SymLog          
from dotenv import load_dotenv
load_dotenv("/home/SoS/SOS_project/.env")        # GOOGLE_API_KEY 로드

import os, json, google.generativeai as genai

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL = genai.GenerativeModel("gemini-1.5-flash")      

router = APIRouter(prefix="/guide", tags=["Guide"])

ANSWER_INSTR = [
    "당신은 ‘AI 응급 대응 어시스턴트’입니다. 공식 진단·처방은 하지 마세요.",
    "답변은 정중한 한국어(존댓말)로 6줄(문단) 이내로 요약하십시오.",
    "응급 징후(호흡곤란·흉통·의식 저하·경련·39℃ 이상 고열·대량 출혈 등)가 있으면 **119 연락** 또는 **응급실** 방문을 가장 먼저 권고하십시오.",
    "위급하지 않다면 ▶ 1) 안심 ▶ 2) 자가 조치 ▶ 3) 경과 관찰 ▶ 4) 병원 방문 시점 순으로 안내하십시오.",
    "약 성분명은 구체적으로 언급하지 말고 ‘전문의 상담 후 적절한 약물 사용’이라고 표현하십시오.",
    "마지막 문장은 항상 ‘빠른 쾌유를 빕니다.’로 끝맺으십시오."
]

FALLBACK = "증상 악화 시 **응급실** 방문을 포함해 전문의 상담을 권장합니다.\n빠른 쾌유를 빕니다."

@router.get("/{rec_id}")
def get_guide(rec_id: int):
    """
    ▸ 클라이언트:   GET /guide/29
    ▸ 반환 형식:   {"risk":"심각","dis":"심근경색 가능성","guide":"…"}
    """
    db = SessionLocal()
    row = db.get(SymLog, rec_id)
    if not row:
        db.close()
        raise HTTPException(404, "record not found")

    # 이미 가이드가 만들어져 있으면 바로 반환
    guide = row.raw.get("가이드")
    if not guide or guide.strip() == "필요 시 전문의 상담을 권장합니다.":
        prompt = "\n".join(ANSWER_INSTR) + \
                 "\n\n[증상 정보]\n" + json.dumps(row.raw, ensure_ascii=False)

        try:
            res = MODEL.generate_content(
                    prompt, generation_config={"temperature": 0.4})
            guide = res.text.strip()
        except Exception as e:
            # 로그만 남기고 예비 문구 사용
            print("Gemini ERROR:", e)
            guide = FALLBACK

        # 한 번 만든 가이드는 sym_log.raw 에 캐시
        row.raw["가이드"] = guide
        db.add(row); db.commit()

    risk_value = row.risk.value
    dis_value = row.dis

    db.close()
    return {
        "risk":  risk_value,   # Enum → “낮음·중간·높음·심각”
        "dis":   dis_value,
        "guide": guide
    }
