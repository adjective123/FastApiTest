from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uuid
import os

from typing import Optional
import model

# ✅ 당신의 audioStream 모듈 import
from audioStream import audio2text

app = FastAPI()

# 정적 파일 및 템플릿 경로 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
# 업로드 경로
UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def keep_only_this_file(latest_path: Path):
    """새로 업로드시 latest_path를 제외한 업로드 폴더 내 모든 파일을 삭제"""
    for p in UPLOAD_DIR.iterdir():
        try:
            if p.is_file() and p.resolve() != latest_path.resolve():
                p.unlink(missing_ok=True)
        except Exception:
            # 삭제 실패는 앱 동작에 치명적이지 않으므로 무시
            pass

def get_latest_audio_path() -> Optional[Path]:
    files = [p for p in UPLOAD_DIR.iterdir() if p.is_file()]
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]

@app.get("/", response_class=HTMLResponse)  #최초 설정
async def read_root(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "submitted_text": None,
            "audio_url": None
        }
    )

@app.post("/submit", response_class=HTMLResponse)
async def submit(
    request: Request,
    user_input: str = Form(None),
    audio_file: UploadFile = File(None)
):
    audio_url = None

    # 오디오 파일이 있으면 저장
    if audio_file and audio_file.filename:
        # MIME 체크
        if not (audio_file.content_type or "").startswith("audio/"):
            raise HTTPException(status_code=400, detail="오디오 파일만 업로드할 수 있습니다.")

        # 고유 파일명 생성
        suffix = Path(audio_file.filename).suffix
        safe_name = f"{uuid.uuid4().hex}{suffix}"
        save_path = UPLOAD_DIR / safe_name

        # 파일 저장
        with save_path.open("wb") as f:
            f.write(await audio_file.read())

        keep_only_this_file(save_path)

        audio_url = f"/static/uploads/{safe_name}"
    else:
        pass

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "submitted_text": user_input,
            "audio_url": audio_url
        }
    )

@app.post("/run-model")
async def run_model_endpoint(
        mode: str = Form(...),  # "audio" 또는 "text"
        user_input: Optional[str] = Form(None)  # text일 때만 전달됨
):
    try:
        if mode == "audio":
            latest = get_latest_audio_path()
            if not latest:
                return JSONResponse({"ok": False, "error": "오디오가 없습니다."}, status_code=400)
            result = model.run_modelaudio2text(mode="file", wavefile=str(latest))            return JSONResponse({"ok": True, "picked": {"picked": "audio"}, "result": result})

        # mode == "text"
        text = (user_input or "").strip()
        if not text:
            return JSONResponse({"ok": False, "error": "텍스트가 없습니다."}, status_code=400)
        result = model.run_model(user_text=text, audio_path=None)
        return JSONResponse({"ok": True, "picked": {"picked": "text", "text": text}, "result": result})

    except Exception as e:
        return JSONResponse({"ok": False, "error": f"서버 내부 오류: {str(e)}"}, status_code=500)