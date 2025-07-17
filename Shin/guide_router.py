# Shin/guide_router.py – 
"""
SymLog に保存された JSON（症状・疑われる疾患・危険度・診療科 …）を読み込み、
Google Gemini を用いて「6行以内の日本語アドバイス」を生成するルーター。
"""
from fastapi import APIRouter, HTTPException
from Yun.db import SessionLocal, SymLog
from dotenv import load_dotenv
load_dotenv("/home/SoS/SOS_project/.env")  # GOOGLE_API_KEY 

import os, json, google.generativeai as genai

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL = genai.GenerativeModel("gemini-1.5-flash")

router = APIRouter(prefix="/guide", tags=["Guide"])

ANSWER_INSTR = [
    "あなたは\u300cAI緊急対応アシスタント\u300dです。正式な診断や処方は行わないでください。",
    "回答は丁寧な日本語で最大6行にまとめてください。",
    "呼吸困難・胸痛・意識障害・けいれん・39℃以上の高熱・大量出血などの緊急兆候がある場合は、まず119に通報または救急外来の受診を強く勧めてください。",
    "緊急度が低い場合は ➡ ①安心させる ➡ ②自宅での対処 ➡ ③経過観察 ➡ ④受診のタイミング の順で案内してください。",
    "薬剤名を個別に列挙せず、\u300c専門医に相談した上で適切な薬を使用する\u300dと記載してください。",
    "最後の文は必ず\u300c早い回復をお祈りしております。\u300dで締めくくってください。"
]

FALLBACK = "症状が悪化した場合は\n救急外来の受診を含め、専門医への相談をお勧めします。\n早い回復をお祈りしております。"

@router.get("/{rec_id}")
def get_guide(rec_id: int):
    """GET /guide/29 → {"risk":"重篤","dis":"心筋梗塞の可能性","guide":"…"}"""
    db = SessionLocal()
    row = db.get(SymLog, rec_id)
    if not row:
        db.close()
        raise HTTPException(404, "record not found")

    
    guide = row.raw.get("ガイド")
    if not guide or guide.strip() == "必要に応じて専門医にご相談ください。":
        prompt = "\n".join(ANSWER_INSTR) + "\n\n【症状情報】\n" + json.dumps(row.raw, ensure_ascii=False)
        try:
            res = MODEL.generate_content(prompt, generation_config={"temperature": 0.4})
            guide = res.text.strip()
        except Exception as e:
            print("Gemini ERROR:", e)
            guide = FALLBACK
        
        row.raw["ガイド"] = guide
        db.add(row); db.commit()

    risk_val = row.risk.value  # '낮음/중간/높음/심각' 
    dis_val  = row.dis
    db.close()
    return {"risk": risk_val, "dis": dis_val, "guide": guide}
