# model.py
from pathlib import Path
from typing import Optional, Dict, Any

import test  # ← 패스스루 모듈

def run_model(user_text: Optional[str], audio_path: Optional[str]) -> Dict[str, Any]:
    """
    - user_text: 최근 제출된 텍스트(없을 수 있음)
    - audio_path: 최근 업로드된 오디오 파일 경로(없을 수 있음)
    """

    # 1) test.py에 위임
    inputs = test.passthrough(user_text=user_text, audio_path=audio_path)
    user_text = inputs.get("user_text")
    audio_path = inputs.get("audio_path")

    # 2) 원래 로직대로 JSON 구성
    info: Dict[str, Any] = {}

    # 텍스트 정보
    info["received_text"] = user_text or ""

    # 오디오 정보
    if audio_path:
        p = Path(audio_path)
        if p.exists():
            info["audio_found"] = True
            info["audio_name"] = p.name
            info["audio_size_bytes"] = p.stat().st_size

            # ✅ 웹에서 재생 가능한 URL 추가
            rel = str(p).replace("\\", "/")
            if "static/" in rel:
                rel = rel.split("static/", 1)[1]
            info["audio_url"] = f"/static/{rel}"

            info["note"] = "오디오 파일이 감지되어 처리 대상으로 전달했습니다."
        else:
            info["audio_found"] = False
            info["note"] = "경로는 있으나 파일이 존재하지 않습니다."
    else:
        info["audio_found"] = False
        info["note"] = "텍스트를 처리했습니다."

    return {"status": "processed", "details": info}
