#!/usr/bin/env python3
"""
판단 서버 (Judge Server)
청크를 받아서 VAD 처리하고 status 반환
"""
import librosa

from uuid import uuid4
import asyncio
import dataclasses
import shutil
from openai import OpenAI
import time
from silero_vad import load_silero_vad, get_speech_timestamps
import soundfile as sf
import numpy as np
import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, Form, Response
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import Dict
from fastapi.middleware.cors import CORSMiddleware
import json
from collections import deque

active_sessions = deque(maxlen=100)

load_dotenv()

# ========== 설정 클래스 ==========
@dataclasses.dataclass
class AudioConfig:
    """오디오 설정"""
    SAMPLERATE: int = 16000
    SILENCE_THRESHOLD: int = 3
    EXIT_THRESHOLD: int = 10
    GAIN: float = 3.0
    VAD_THRESHOLD: float = 0.2
    WHISPER_MODEL: str = "whisper-1"
    WHISPER_LANGUAGE: str = "ko"


@dataclasses.dataclass
class ServerConfig:
    """서버 설정"""
    HOST: str = "127.0.0.1"
    # HOST: str = "192.168.0.37"
    PORT: int = 8000


@dataclasses.dataclass
class CORSConfig:
    """CORS 설정"""
    ALLOW_ORIGINS: list = dataclasses.field(default_factory=lambda: ["*"])
    ALLOW_CREDENTIALS: bool = True
    ALLOW_METHODS: list = dataclasses.field(default_factory=lambda: ["*"])
    ALLOW_HEADERS: list = dataclasses.field(default_factory=lambda: ["*"])


@dataclasses.dataclass
class PathConfig:
    """경로 설정"""
    SESSIONS_DIR: str = "sessions_b"
    INBOX_DIR: str = "inbox"
    TEMP_FILE_PREFIX: str = "temp_audio_"


@dataclasses.dataclass
class VADConfig:
    """VAD 모델 설정"""
    MONITORING: bool = False


# ========== Config 로더 ==========
def load_config(config_path: str = "config.json"):
    """JSON 설정 파일 로드"""
    config_file = Path(config_path)
    
    if config_file.exists():
        print(f"✅ 설정 파일 로드: {config_path}")
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    else:
        print(f"⚠️  설정 파일 없음. 기본값 사용: {config_path}")
        config_data = {}
    
    # AudioConfig
    audio_conf = config_data.get("audio", {})
    audio_config = AudioConfig(
        SAMPLERATE=audio_conf.get("samplerate", 16000),
        SILENCE_THRESHOLD=audio_conf.get("silence_threshold", 3),
        EXIT_THRESHOLD=audio_conf.get("exit_threshold", 10),
        GAIN=audio_conf.get("gain", 3.0),
        VAD_THRESHOLD=audio_conf.get("vad_threshold", 0.2),
        WHISPER_MODEL=audio_conf.get("whisper_model", "whisper-1"),
        WHISPER_LANGUAGE=audio_conf.get("whisper_language", "ko")
    )
    
    # ServerConfig
    server_conf = config_data.get("server", {})
    server_config = ServerConfig(
        HOST=server_conf.get("host", "127.0.0.1"),
        PORT=server_conf.get("port", 8000)
    )
    
    # CORSConfig
    cors_conf = config_data.get("cors", {})
    cors_config = CORSConfig(
        ALLOW_ORIGINS=cors_conf.get("allow_origins", ["*"]),
        ALLOW_CREDENTIALS=cors_conf.get("allow_credentials", True),
        ALLOW_METHODS=cors_conf.get("allow_methods", ["*"]),
        ALLOW_HEADERS=cors_conf.get("allow_headers", ["*"])
    )
    
    # PathConfig
    path_conf = config_data.get("paths", {})
    path_config = PathConfig(
        SESSIONS_DIR=path_conf.get("sessions_dir", "sessions_b"),
        INBOX_DIR=path_conf.get("inbox_dir", "inbox"),
        TEMP_FILE_PREFIX=path_conf.get("temp_file_prefix", "temp_audio_")
    )
    
    # VADConfig
    vad_conf = config_data.get("vad", {})
    vad_config = VADConfig(
        MONITORING=vad_conf.get("monitoring", False)
    )
    
    return audio_config, server_config, cors_config, path_config, vad_config


# ========== 설정 로드 ==========
AUDIO_CONFIG, SERVER_CONFIG, CORS_CONFIG, PATH_CONFIG, VAD_CONFIG = load_config()

# FastAPI 앱
app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_CONFIG.ALLOW_ORIGINS,
    allow_credentials=CORS_CONFIG.ALLOW_CREDENTIALS,
    allow_methods=CORS_CONFIG.ALLOW_METHODS,
    allow_headers=CORS_CONFIG.ALLOW_HEADERS,
)

# 경로 설정
BASE = Path(__file__).parent
SESS_BASE = BASE / PATH_CONFIG.SESSIONS_DIR
SESS_BASE.mkdir(exist_ok=True)
INBOX = BASE / PATH_CONFIG.INBOX_DIR
INBOX.mkdir(exist_ok=True)

# OpenAI API 키 설정
api_key = os.getenv("OPENAI_API_KEY", "your-api-key")
client = OpenAI(api_key=api_key)


# ========== VAD 모델 ==========
class VADModel:
    """VAD 모델 래퍼 클래스"""
    def __init__(self, audio_config: AudioConfig, vad_config: VADConfig) -> None:
        self.model = load_silero_vad()
        self.SAMPLERATE = audio_config.SAMPLERATE
        self.VAD_THRESHOLD = audio_config.VAD_THRESHOLD
        self.monitoring = vad_config.MONITORING

    def get_speech_timestamps(self, audio_data) -> list:
        """오디오 데이터에서 음성 구간의 타임스탬프를 반환"""
        if self.monitoring:
            print(f"[VAD] audio_data type: {type(audio_data)}")
            print(f"[VAD] audio_data dtype: {audio_data.dtype}")
            print(f"[VAD] audio_data shape: {audio_data.shape}")
            print(f"[VAD] audio_data range: [{audio_data.min():.4f}, {audio_data.max():.4f}]")
  
        return get_speech_timestamps(
            audio_data,
            self.model,
            threshold=self.VAD_THRESHOLD,
            sampling_rate=self.SAMPLERATE,
        )


# ========== 음성 활동 감지 ==========
class _AudioActivityDetection:
    """음성 활동 감지 클래스"""
    def __init__(self, audio_config: AudioConfig):
        self.is_recording = False
        self.speech_buffer = []
        self.stop_count = 0
        self.silence_threshold = audio_config.SILENCE_THRESHOLD
        self.exit_threshold = audio_config.EXIT_THRESHOLD

    def resetStream(self):
        """스트림 상태 초기화"""
        self.is_recording = False
        self.speech_buffer = []
        self.stop_count = 0
        return {"audio": None, "status": "Reset"}

    def __call__(self, speech_detected: list, audio_buffer: np.array) -> dict:
        """음성 데이터에서 화자 활동을 감지"""
        has_speech = len(speech_detected) > 0
        user_status = "Silent"
        user_audio = None
        
        if has_speech:
            if not self.is_recording:
                self.is_recording = True
                self.stop_count = 0
                self.speech_buffer = []
                user_status = "Speech"
                print("🎤 음성 시작")
            else:
                user_status = "Speech"
            
            self.speech_buffer.append(audio_buffer)
            
            if self.stop_count > 0:
                print(f"음성 재감지 → 무음 카운트 리셋 ({self.stop_count} → 0)")
                self.stop_count = 0
            
        else:  # 무음
            if self.is_recording:
                zero_data = np.zeros_like(audio_buffer)
                self.speech_buffer.append(zero_data)
                self.stop_count += 1
                user_status = "Speech"
                
                print(f"연속 무음: {self.stop_count}/{self.silence_threshold}")
                
                if self.stop_count >= self.silence_threshold:
                    speech_data = np.concatenate(self.speech_buffer, axis=0)
                    self.is_recording = False
                    self.stop_count = 0
                    self.speech_buffer = []
                    user_audio = speech_data
                    user_status = "Finished"
                    print("✅ 음성 종료")
                    
            else:
                self.stop_count += 1
                if self.stop_count >= self.exit_threshold:
                    print(f"❌ 연속 {self.exit_threshold}번 무음으로 시스템 종료")
                    user_audio = None
                    user_status = "Error"
                else:
                    user_status = "Silent"

        return {"audio": user_audio, "status": user_status}


# 세션 상태 및 VAD 모델 초기화
session_states: Dict[str, _AudioActivityDetection] = {}
_vad_model = VADModel(AUDIO_CONFIG, VAD_CONFIG)


# ========== 핵심 함수: 오디오 청크 처리 ==========
async def process_audio_chunk(session_id: str, audio_data, reset: bool = False) -> dict:
    """실시간 오디오 청취 및 텍스트 변환"""
    vad_model = _vad_model
    audio_data = librosa.resample(audio_data, orig_sr=48000, target_sr=16000)

    if session_id not in session_states:
        session_states[session_id] = _AudioActivityDetection(AUDIO_CONFIG)

    event_checker = session_states[session_id]    
    
    result_status = None
    transcript_text = None

    if reset:
        result = event_checker.resetStream()
        return {"status": result["status"], "text": None}

    if audio_data is not None:
        speech_timestamps = vad_model.get_speech_timestamps(audio_data)
        result = event_checker(speech_timestamps, audio_data)
        
        result_status = result["status"]
                
        if result["audio"] is not None:
            # 임시 파일 이름 생성
            temp_file_name = f"{PATH_CONFIG.TEMP_FILE_PREFIX}{session_id}_{time.time()}.wav"
            
            # 파일 쓰기
            await asyncio.to_thread(
                sf.write, 
                temp_file_name, 
                result["audio"], 
                AUDIO_CONFIG.SAMPLERATE
            )
            
            # STT 호출
            def transcribe_sync():
                with open(temp_file_name, "rb") as audio_file:
                    return client.audio.transcriptions.create(
                        model=AUDIO_CONFIG.WHISPER_MODEL,
                        file=audio_file,
                        language=AUDIO_CONFIG.WHISPER_LANGUAGE
                    )

            response = await asyncio.to_thread(transcribe_sync)
            transcript_text = response.text
            
            # 임시 파일 삭제
                
            os.makedirs("audio_data", exist_ok=True)
            save_path = f"audio_data/{session_id}_{time.time()}.wav"
            await asyncio.to_thread(shutil.copy, temp_file_name, save_path)            
            await asyncio.to_thread(os.remove, temp_file_name)
                        
            print(f"📝 인식된 텍스트: {transcript_text}")

        elif result["status"] in ["Error", "Speech", "Silent", "Reset"]:
            transcript_text = None

    else:
        result_status = "silent"
        transcript_text = None
        
    if result_status in ["Finished", "Error"]:
        print(f"세션 {session_id} 상태 정리.")
        if session_id in session_states:
            del session_states[session_id]
                    
    return {"status": result_status, "text": transcript_text}


# ========== FastAPI 라우트 ==========
@app.post("/start")
def start():
    """새 세션 시작 (API 호환성 유지)"""
    sid = str(uuid4())
    active_sessions.append(sid)
    return {"sessionId": sid}


@app.post("/ingest-chunk")
async def ingest_chunk(
    sessionId: str = Form(...),
    chunk: UploadFile = Form(...),
    mode: str = Form("chunk")  # "chunk" 또는 "file"
):
    """청크/파일 수신 → VAD 처리 또는 직접 전사 → 응답 반환"""
    #함수 시작전에 무조껀 session ID 중복검사를 중복이면 에러로 반환함
    if sessionId not in active_sessions:
        return JSONResponse({
            "status": "Error",
            "text": None,
            "detail": "Invalid sessionId. Call /start first."
        }, status_code=400)    
    
    try:
        chunk_data = await chunk.read()
        print(f"📥 [판단] 세션: {sessionId[:8]}... | 모드: {mode} | 크기: {len(chunk_data)} bytes")
        
        # ========== 파일 모드: 바로 Whisper 전사 ==========
        if mode == "file":
            temp_path = f"{PATH_CONFIG.TEMP_FILE_PREFIX}{sessionId}_{time.time()}.wav"
            
            with open(temp_path, "wb") as f:
                f.write(chunk_data)
            
            def transcribe_sync():
                with open(temp_path, "rb") as audio_file:
                    return client.audio.transcriptions.create(
                        model=AUDIO_CONFIG.WHISPER_MODEL,
                        file=audio_file,
                        language=AUDIO_CONFIG.WHISPER_LANGUAGE
                    )
            
            response = await asyncio.to_thread(transcribe_sync)
            await asyncio.to_thread(os.remove, temp_path)
            
            print(f"📝 [파일모드] 인식된 텍스트: {response.text}")
            
            return JSONResponse({
                "status": "Finished",
                "text": response.text
            }, status_code=200)
        
        # ========== 청크 모드: VAD 처리 ==========
        else:
            audio_array = np.frombuffer(chunk_data, dtype=np.int16)
            audio_data = audio_array.astype(np.float32) / 32768.0
            
            print(f"🔄 [판단] 샘플 수: {len(audio_data)} | 범위: [{audio_data.min():.3f}, {audio_data.max():.3f}]")
            
            audio_data = audio_data * AUDIO_CONFIG.GAIN
            result = await process_audio_chunk(sessionId, audio_data)
            
            print(f"🎯 [판단] VAD 결과: {result['status']}")
            
            if result["status"] == "Error":
                return JSONResponse({
                    "status": "Error",
                    "text": None
                }, status_code=500)
            elif result["status"] == "Speech":
                return JSONResponse({
                    "status": "Speech",
                    "text": None
                }, status_code=200)
            
            elif result["status"] == "Finished":
                return JSONResponse({
                    "status": "Finished",
                    "text": result["text"]
                }, status_code=200)
            
            else: #Silent
                return JSONResponse({
                    "status": "Silent",
                    "text": None
                }, status_code=200)

    except Exception as e:
        print(f"❌ 에러: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse({
            "status": "Error",
            "text": None,
            "detail": str(e)
        }, status_code=500)

# ========== CLI 모드 ==========
if __name__ == '__main__':
    import uvicorn
    print(f"🚀 판단 서버 시작: {SERVER_CONFIG.HOST}:{SERVER_CONFIG.PORT}")
    uvicorn.run(app, host=SERVER_CONFIG.HOST, port=SERVER_CONFIG.PORT)