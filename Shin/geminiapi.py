import os, json, google.generativeai as genai
from google.generativeai.types import GenerationConfig

#  API 키
genai.configure(api_key=os.getenv("GOOGLE_GEMINI_API_KEY", ""))

BASE_PROMPT = "\n".join(
    json.load(open("prompt.json", encoding="utf-8"))
        .get("answer_instructions", [])
)

model = genai.GenerativeModel(
    model_name="models/gemini-1.5-flash",
    system_instruction=BASE_PROMPT,
    generation_config=GenerationConfig(
        max_output_tokens=512,
        temperature=0.2,
        top_p=0.9
    )
)

def get_symptom_guide_from_gemini(symptom_text: str) -> str:
    """사용자 증상 → 한국어 6줄 가이드"""
    try:
        res = model.generate_content(symptom_text)   
        return res.text
    except Exception as e:
        print("[ERROR] Gemini:", e)
        return f"죄송합니다. 서버 오류가 발생했습니다. ({e})"
# 연결확인용변경