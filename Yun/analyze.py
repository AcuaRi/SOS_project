from fastapi import FastAPI, Form, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import google.generativeai as genai
import json
import re
from PIL import Image
import io
import datetime
from dotenv import load_dotenv
import os
from google.cloud import speech
# uvicorn analyze:analyze_app --reload

# 환경 설정
load_dotenv(dotenv_path="c:\\Users\\dbswodyd\\Desktop\\Team project\\API_key.env")
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("models/gemini-1.5-flash")

# Google STT 인증
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "c:\\Users\\dbswodyd\\Desktop\\study\\Python\\coding\\stt_key.json"

# FastAPI 앱 정의
analyze_app = FastAPI()

# 정적 파일 및 템플릿 설정
analyze_app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 프롬프트,과목 코드 리스트 경로 
prompt_path = "c:\\Users\\dbswodyd\\Desktop\\Team project\\prompt.json"
subject_path = "c:\\Users\\dbswodyd\\Desktop\\Team project\\subject_list.txt"

with open(prompt_path, "r", encoding="utf-8") as p:
    prompt_data = json.load(p)
with open(subject_path, "r", encoding="utf-8") as f:
    subject_list = f.read()

analysis_prompt_lines = [
    line if "진료과목 리스트는 별도 파일에서 불러옴" not in line else f"진료과목 리스트:\n{subject_list}"
    for line in prompt_data["analysis_prompt"]
]

base_prompt = "\n".join(analysis_prompt_lines)

# print(base_prompt)

@analyze_app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})

@analyze_app.post("/analyze", response_class=HTMLResponse)
async def analyze_symptom(
    request: Request,
    symptom: str = Form(""),  # 기본값 "" (없을 수도 있으니까)
    image: UploadFile = File(None),
    audio: UploadFile = File(None),  # audio 입력 추가
    latitude: str = Form(None),
    longitude: str = Form(None)
):
    stt_text = ""

    # ====== Google STT 처리 ======
    if audio is not None:
        audio_bytes = await audio.read()
        
        if audio_bytes:
            client = speech.SpeechClient()
            recognition_audio = speech.RecognitionAudio(content=audio_bytes)

            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=48000, 
                language_code="ko-KR"
            )

            response = client.recognize(config=config, audio=recognition_audio)

            # 결과 추출
            for result in response.results:
                stt_text = result.alternatives[0].transcript
                # print(f"[STT 결과] {stt_text}")

    # 최종 symptom 텍스트 결정 1순위-입력창 2순위-stt(input이 2개인 경우)
    final_symptom = symptom if symptom else stt_text
    if not final_symptom:
        return HTMLResponse(content="증상 텍스트 또는 음성 파일을 입력해 주세요.", status_code=400)

    # ====== 이미지 처리 ======
    image_data = None
    if image is not None:
        contents = await image.read()
    if contents:
        image_data = Image.open(io.BytesIO(contents))

    # ====== 프롬프트 구성 ======
    full_prompt = f"{base_prompt}\n\n사용자 증상: {final_symptom}"

    # Gemini API 호출
    if image_data:
        response = model.generate_content([full_prompt, image_data])
    else:
        response = model.generate_content([full_prompt])

    json_format = response.text

    # ====== JSON 결과 파싱 및 저장 ======
    match = re.search(r"\{[\s\S]*?\}", json_format)
    parsed = None
    if match:
        try:
            json_text = match.group()
            parsed = json.loads(json_text)
            #6자리로 만드는 거 
            # try:
            #     lat_value = round(float(latitude), 6) if latitude else None
            #     lng_value = round(float(longitude), 6) if longitude else None
            # except ValueError:
            #     lat_value = None
            #     lng_value = None

            parsed["위치"] = {
                "latitude": latitude,  # lat_value
                "longitude": longitude  # lng_value
            }  # 위치정보 추가 
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"static/result_{timestamp}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=4)
        except json.JSONDecodeError:
            parsed = None

    # ====== 결과 화면 반환 ======
    return templates.TemplateResponse(
        "result_page.html",
        {
            "request": request,
            "json_format": json_format,
            "parsed": parsed,
            "final_symptom": final_symptom,
            "stt_text": stt_text,  # STT
            "symptom_input": symptom  # 입력창
        }
    )



