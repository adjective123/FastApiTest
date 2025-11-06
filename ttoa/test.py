# test.py
from typing import Optional, Dict

def passthrough(user_text: Optional[str], audio_path: Optional[str]) -> Dict[str, Optional[str]]:
    """
    model.py에서 넘겨준 텍스트/오디오를 그대로 반환.
    실제 모델 연동 지점 이곳을 활용해서 수정.
    텍스트 = user_text
    오디오 경로 = audio_path
    """
    if user_text == "test":
        audio_path = "static/uploads/test.wav"

    return {
        "user_text": None,
        "audio_path": audio_path,
    }