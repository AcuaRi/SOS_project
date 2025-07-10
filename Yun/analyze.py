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
from fastapi.staticfiles import StaticFiles

from geminiapi import get_symptom_guide_from_gemini
from fastapi.responses import JSONResponse
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
analyze_app.mount("/templates", StaticFiles(directory="templates"), name="templates")
templates = Jinja2Templates(directory="templates")

# 프롬프트,과목 코드 리스트 경로 
prompt_path = "c:\\Users\\dbswodyd\\Desktop\\Team project\\analyze_prompt.json"
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

#증상분석 - stt 호출 
@analyze_app.post("/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    stt_text = ""

    if audio_bytes:
        client = speech.SpeechClient()
        recognition_audio = speech.RecognitionAudio(content=audio_bytes)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code="ko-KR"
        )

        response = client.recognize(config=config, audio=recognition_audio)
        for result in response.results:
            stt_text += result.alternatives[0].transcript

    return JSONResponse(content={"stt_text": stt_text})

# 증상분석 - chat 페이지 열기
@analyze_app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

# 증상분석 - 사용자의 증상 분석
@analyze_app.post("/analyze", response_class=HTMLResponse)
async def analyze_symptom(
    request: Request,
    symptom: str = Form(""),
    image: UploadFile = File(None),
    audio: UploadFile = File(None),
    latitude: str = Form(None),
    longitude: str = Form(None)
):

    final_symptom = symptom

    # print(f"[사용자 입력 symptom]: {symptom}")
    # print(f"[STT 결과]: {stt_text}")
    if not final_symptom:
        return HTMLResponse(content="증상 텍스트 또는 음성 파일을 입력해 주세요.", status_code=400)

    image_data = None
    if image is not None:
        contents = await image.read()
        if contents:
            image_data = Image.open(io.BytesIO(contents))

    full_prompt = f"{base_prompt}\n\n사용자 증상: {final_symptom}"

    # Gemini 오류 대비용 try-except 추가
    try:
        if image_data:
            response = model.generate_content([full_prompt, image_data])
        else:
            response = model.generate_content([full_prompt])
        json_format = response.text
    except Exception as e:
        print("Gemini API 오류:", e)
        reply_message = "⚠️ 증상 분석 중 오류가 발생했습니다."
        return JSONResponse(content={"reply": reply_message})  

    match = re.search(r"\{[\s\S]*?\}", json_format)
    parsed = None
    if match:
        try:
            json_text = match.group()
            parsed = json.loads(json_text)
            try:
                lat_value = round(float(latitude), 6) if latitude else None
                lng_value = round(float(longitude), 6) if longitude else None
            except ValueError:
                lat_value = None
                lng_value = None

            parsed["위치"] = {
                "latitude": lat_value,
                "longitude": lng_value
            }

            if "진료과목 코드" in parsed:
                try:
                    parsed["진료과목 코드"] = int(parsed["진료과목 코드"])
                except ValueError:
                    pass

            #json파일 생성         
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"static/result_{timestamp}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=4)

            disease_name = parsed.get("의심 질환", final_symptom)
            guide_text = get_symptom_guide_from_gemini(disease_name)
            reply_message = guide_text

        except json.JSONDecodeError:
            reply_message = "Error : 분석된 JSON 형식을 읽을 수 없습니다."
    else:
        reply_message = "Error : 분석된 JSON 형식을 찾지 못했어요."

    return JSONResponse(content={"reply": reply_message})  #  항상 stt_text 포함 응답



