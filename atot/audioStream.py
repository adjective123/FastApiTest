#!/usr/bin/env python3
"""실시간 음성 인식 시스템"""
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()  # 이 줄이 반드시 있어야 함

# OpenAI API 키 설정
api_key = os.getenv("OPENAI_API_KEY", "your-api-key")
if api_key == "your-api-key":
    raise ValueError("OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인해주세요.")
client = OpenAI(api_key=api_key)


# ========== PUBLIC API ==========

def audio2text(mode: str = "stream",
               wavefile: str = None) -> str:
    """
    음성을 텍스트로 변환하는 통합 API, 해당 함수를 통해서 로컬 스트리밍 또는
    파일 업로드 방식으로 음성 인식을 수행할 수 있습니다.
    
    Args:
        mode: "stream" (실시간 마이크 입력) 또는 "file" (파일 입력)
        wavefile: mode가 "file"일 때 필요한 오디오 파일 (UploadFile)
    
    Returns:
        str: 변환된 텍스트
    
    Raises:
        ValueError: mode가 "file"인데 wavefile이 None일 때
    """
    if mode == "file":
        if wavefile is None:
            raise ValueError("mode='file'일 때는 wavefile을 입력해주세요.")
        
        try:
            # OpenAI Whisper API로 직접 전사
            with open(wavefile, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ko"
                )
            
            return response.text
        
        except Exception as e:
            print(f"파일 전사 중 오류 발생: {e}")
            return ""
    
    else:
        raise ValueError(f"지원하지 않는 mode: {mode}. 'stream' 또는 'file'을 사용하세요.")


if __name__ == '__main__':
    # CLI 모드: 실시간 음성 인식
    text = audio2text(mode="file", wavefile="temp_audio.wav")
    print(f"\n최종 결과: {text}")