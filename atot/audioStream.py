#!/usr/bin/env python3
"""실시간 음성 인식 시스템"""
import queue
import sys
from openai import OpenAI
import time
from silero_vad import load_silero_vad, get_speech_timestamps
import soundfile as sf
from fastapi import UploadFile, File
import numpy as np
import sounddevice as sd
import os
from dotenv import load_dotenv

load_dotenv()  # 이 줄이 반드시 있어야 함


# OpenAI API 키 설정
api_key = os.getenv("OPENAI_API_KEY", "your-api-key")
client = OpenAI(api_key=api_key)

# 전역 VAD 모델 (싱글톤 패턴)
_vad_model = None

class AudioConfig:
    """오디오 설정 상수"""
    DEVICE = None
    SAMPLERATE = 16000
    CHANNELS = 1
    CHUNKSIZE = 64
    BATCH_SIZE = 100
    SILENCE_THRESHOLD = 3

class _VADModel:
    """내부 VAD 모델 (private)"""
    def __init__(self):
        self.model = load_silero_vad()
    
    def get_speech_timestamps(self, audio_data):
        return get_speech_timestamps(
            audio_data,
            self.model,
            return_seconds=False,
            language="ko"
        )

class _AudioStream:
    """내부 오디오 스트림 클래스 (private)"""
    def __init__(self):
        self.queue = queue.Queue()
        self.stream = None

    def init_stream(self):
        if self.stream is None:
            self.stream = sd.InputStream(
                device=AudioConfig.DEVICE,
                blocksize=AudioConfig.CHUNKSIZE,
                channels=AudioConfig.CHANNELS,
                samplerate=AudioConfig.SAMPLERATE, 
                callback=self._audio_callback
            )
            print("오디오 스트림 초기화 완료")

    def start_stream(self):
        if self.stream is not None:
            self.stream.start()
            print("오디오 스트림 시작됨")
        else:
            raise RuntimeError("스트림이 초기화되지 않았습니다.")

    def stop_stream(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            print("오디오 스트림 종료됨")

    def process_audio_batch(self, target=AudioConfig.BATCH_SIZE):
        chunks = []
        
        try:
            while len(chunks) < target:
                chunk = self.queue.get(timeout=1.0)
                chunks.append(chunk)
        except queue.Empty:
            pass
            
        return np.concatenate(chunks, axis=0).squeeze() if chunks else None
        
    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        self.queue.put(indata.copy())


class _AudioActivityDetection:
    """내부 음성 활동 감지 클래스 (private)"""
    def __init__(self, silence_threshold: int = AudioConfig.SILENCE_THRESHOLD):
        self.is_recording = False
        self.speech_buffer = []
        self.speech_id = 0
        self.stop_count = 0
        self.silence_threshold = silence_threshold

    def __call__(self, speech_detected, audio_buffer):
        has_speech = len(speech_detected) > 0
        
        if has_speech:
            if not self.is_recording:
                self.is_recording = True
                self.speech_buffer = []
                print("🎤 음성 시작")
            
            self.speech_buffer.append(audio_buffer)
            
            if self.stop_count > 0:
                print(f"음성 재감지 → 무음 카운트 리셋 ({self.stop_count} → 0)")
                self.stop_count = 0
            
        else:  # 무음
            if self.is_recording:
                zero_data = np.zeros_like(audio_buffer)
                self.speech_buffer.append(zero_data)
                self.stop_count += 1
                
                print(f"연속 무음: {self.stop_count}/{self.silence_threshold}")
                
                if self.stop_count >= self.silence_threshold:
                    speech_data = np.concatenate(self.speech_buffer, axis=0)
                    self.is_recording = False
                    self.stop_count = 0
                    self.speech_buffer = []
                    self.speech_id += 1
                    
                    print(f"🛑 연속 {self.silence_threshold}번 무음으로 종료")
                    return speech_data

        return None


def _get_vad_model():
    """VAD 모델 싱글톤 getter"""
    global _vad_model
    if _vad_model is None:
        _vad_model = _VADModel()
    return _vad_model


def _listen_and_transcribe():
    """내부 함수: 실시간 음성 수집 및 텍스트 변환"""
    vad_model = _get_vad_model()
    stream = _AudioStream()
    stream.init_stream()
    stream.start_stream()
    event_checker = _AudioActivityDetection()

    print("스트림 시작됨 - 말씀해주세요")

    try:
        while True:
            audio_data = stream.process_audio_batch()
            
            if audio_data is not None:
                speech_timestamps = vad_model.get_speech_timestamps(audio_data)
                result = event_checker(speech_timestamps, audio_data)
                
                if result is not None:
                    print(f"저장된 음성 클립 {event_checker.speech_id}, 길이: {result.shape}")
                    
                    # 임시 파일로 저장
                    sf.write("temp_audio.wav", result, samplerate=AudioConfig.SAMPLERATE)

                    # OpenAI Whisper API로 전사
                    with open("temp_audio.wav", "rb") as audio_file:
                        response = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language="ko"
                        )

                    transcript_text = response.text
                    print(f"변환된 텍스트: {transcript_text}")
                    
                    return transcript_text
            else:
                time.sleep(0.1)
                
    finally:
        stream.stop_stream()


# ========== PUBLIC API ==========

def audio2text(mode: str = "stream", wavefile: UploadFile = File(None)) -> str:
    """
    음성을 텍스트로 변환하는 통합 API
    
    Args:
        mode: "stream" (실시간 마이크 입력) 또는 "file" (파일 입력)
        wavefile: mode가 "file"일 때 필요한 오디오 파일 (UploadFile)
    
    Returns:
        str: 변환된 텍스트
    
    Raises:
        ValueError: mode가 "file"인데 wavefile이 None일 때
    """
    if mode == "stream":
        return _listen_and_transcribe()
    
    elif mode == "file":
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