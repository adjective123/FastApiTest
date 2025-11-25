# main.py - ATOT Server
# !uvicorn atot.main:app --reload --host 1.20.15.20

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uuid
import os
from typing import Optional
import httpx
import subprocess  # 추가
import sys  # 추가

import model

app = FastAPI()

app.state.user_id = None
app.state.result = None

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
        async with httpx.AsyncClient() as client:
            response = await client.get("http://127.0.0.1:5000/")
            response.raise_for_status()
            data = response.json()
            app.state.user_id = data.get("user", {}).get("id")
            
            if not app.state.user_id:
                raise HTTPException(status_code=400, detail="User not found")
        if mode == "audio":
            latest = get_latest_audio_path()
            if not app.state.user_id:
                return JSONResponse({"user_id": app.state.user_id, "ok": False, "error": "오디오가 없습니다."}, status_code=400)
            app.state.result = model.run_model(user_text=None, audio_path=str(latest))
            return JSONResponse({"user_id": app.state.user_id, "ok": True, "picked": {"picked": "audio"}, "result": app.state.result})

        # mode == "text"
        text = (user_input or "").strip()
        if not text:
            return JSONResponse({"user_id": app.state.user_id, "ok": False, "error": "텍스트가 없습니다."}, status_code=400)
        app.state.result = model.run_model(user_text=text, audio_path=None)
        return JSONResponse({"user_id": app.state.user_id, "ok": True, "picked": {"picked": "text", "text": text}, "result": app.state.result})

    except Exception as e:
        return JSONResponse({"ok": False, "error": f"서버 내부 오류: {str(e)}"}, status_code=500)

@app.get("/run-model")
async def get_run_model():
    try:
        return JSONResponse({"user_id": app.state.user_id, "ok": True, "result": app.state.result})
    except Exception as e:
        return JSONResponse({"user_id": app.state.user_id, "ok": False, "error": f"서버 내부 오류: {str(e)}"}, status_code=500)
# ''' 엔드포인트 추가
@app.post("/run-test")
async def run_test_script():
    """
    FastAPITest/test.py 스크립트를 실행하는 엔드포인트
    모델 실행 버튼을 누르면 자동으로 test.py가 실행됩니다.
    """
    try:
        # test.py 경로 설정 (atot 폴더에서 상위 폴더로 이동)
        test_py_path = Path(__file__).parent.parent / "test.py"
        
        if not test_py_path.exists():
            return JSONResponse(
                {
                    "user_id": app.state.user_id,
                    "ok": False, 
                    "error": f"test.py를 찾을 수 없습니다. 경로: {test_py_path}"
                },
                status_code=404
            )
        
        print(f"[ATOT] test.py 실행 시작: {test_py_path}")
        
        # Python 스크립트 실행 (결과를 기다림)
        process = subprocess.run(
            [sys.executable, str(test_py_path)],
            capture_output=True,
            text=True,
            cwd=test_py_path.parent,  # FastAPITest 폴더에서 실행
            timeout=60  # 60초 타임아웃
        )
        
        print(f"[ATOT] test.py 실행 완료 (return code: {process.returncode})")
        
        if process.returncode == 0:
            return JSONResponse({
                "ok": True,
                "message": "✅ test.py 실행 완료",
                "output": process.stdout,
                "user_id": app.state.user_id,
                "result_available": app.state.result is not None
            })
        else:
            return JSONResponse({
                "user_id": app.state.user_id,
                "ok": False,
                "error": "test.py 실행 중 오류 발생",
                "stderr": process.stderr,
                "stdout": process.stdout,
                "return_code": process.returncode
            }, status_code=500)
            
    except subprocess.TimeoutExpired:
        print("[ATOT] test.py 실행 시간 초과")
        return JSONResponse({
            "ok": False,
            "error": "⏱️ test.py 실행 시간 초과 (60초)"
        }, status_code=408)
    except Exception as e:
        print(f"[ATOT] test.py 실행 오류: {str(e)}")
        return JSONResponse({
            "ok": False,
            "error": f"서버 내부 오류: {str(e)}"
        }, status_code=500)
# '''

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)  # host = 서버IP