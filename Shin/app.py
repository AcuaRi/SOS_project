"""
app.py
- Flask 서버: 프런트 HTML 제공 + 증상 텍스트를 받아 Gemini API 가이드 반환
- geminiapi.py 의 get_symptom_guide_from_gemini() 함수를 호출해 사용
"""

from flask import Flask, request, jsonify, send_from_directory
import os, google.generativeai as genai
from geminiapi import get_symptom_guide_from_gemini   # ← AI 가이드 함수

app = Flask(__name__)

#  API 키 설정
API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("환경변수 GOOGLE_GEMINI_API_KEY 가 없습니다.")
genai.configure(api_key=API_KEY)

#라우트 
@app.route("/")                          # GET /
def index():
    """첫 화면: input.html 반환"""
    return send_from_directory(".", "input.html")

@app.route("/get_symptom_guide", methods=["POST"])     # POST /get_symptom_guide
def guide():
    """증상 텍스트를 받아 Gemini 가이드 JSON 반환"""
    data = request.get_json(force=True)
    symptom = (data.get("symptom_text") or "").strip()
    if not symptom:
        return jsonify(success=False, error="No symptom text provided."), 400

    answer = get_symptom_guide_from_gemini(symptom)
    return jsonify(success=True, symptom=symptom, guide=answer)

# 로컬서버 실행
if __name__ == "__main__":
    app.run(debug=True)

    