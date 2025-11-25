#!/usr/bin/env python3
"""실시간 음성 인식 시스템"""
import dataclasses
import queue
import sys
from librosa import stream
from openai import OpenAI
import time
from silero_vad import load_silero_vad, get_speech_timestamps
import soundfile as sf
import numpy as np
import sounddevice as sd
import os
from dotenv import load_dotenv

load_dotenv()  # 이 줄이 반드시 있어야 함


# OpenAI API 키 설정
api_key = os.getenv("OPENAI_API_KEY", "your-api-key")
client = OpenAI(api_key=api_key)

@dataclasses.dataclass
class AudioConfig:
    """오디오 설정 상수"""
    SAMPLERATE = 16000
    SILENCE_THRESHOLD = 3
    EXIT_THRESHOLD = 10


class VADModel:
    """
    음성을 감지하는 VAD 모델 래퍼 클래스 (private)
    생성하면 동시에 VAD 모델을 로드합니다.
    
    Attributes:
        model: 로드된 VAD 모델
    """
    def __init__(self,monitoring = False)-> None:
        self.model = load_silero_vad()
        self.SAMPLERATE = AudioConfig.SAMPLERATE
        self.monitoring = monitoring

    """
    오디오 데이터에서 음성 구간의 타임스탬프를 반환합니다.
    
    Args:
        audio_data (np.array): 오디오 신호 배열

    Returns:
        list: 감지된 음성 구간의 타임스탬프 리스트
    """    
    def get_speech_timestamps(self, audio_data)->list:
        if self.monitoring:
            print(f"[VAD] audio_data type: {type(audio_data)}")
            print(f"[VAD] audio_data dtype: {audio_data.dtype}")
            print(f"[VAD] audio_data shape: {audio_data.shape}")
            print(f"[VAD] audio_data range: [{audio_data.min():.4f}, {audio_data.max():.4f}]")
  
        return get_speech_timestamps(
            audio_data,
            self.model,
            sampling_rate = self.SAMPLERATE,
        )



class _AudioActivityDetection:
    """
    음성 데이터를 읽어 와서 화자가 대화를 하고 있는지 감시
    Status
    - 1. Silent: 무음 상태
    - 2. Speech: 음성 감지 상태
    - 3. Finished: 음성 녹음 종료 상태
    - 4. Error: 연속 무음으로 인한 시스템 종료 상태
    - 5. Reset: 스트림 상태 초기화 상태
    
    Attributes:
        is_recording:  현재 녹음중인 여부로 최초로 음성이 감지되면 True로 변경되고,
                       연속으로 무음이 silence_threshold번 감지되면 False로 변경됩니다.
        speech_buffer: 녹음된 음성 데이터를 저장하는 버퍼  
        stop_count: 연속 무음 카운트
        silence_threshold: 연속 무음으로 간주하는 임계값
        exit_threshold: 연속 무음으로 간주하여 시스템 종료하는 임계값
    
    Methods:
        resetStream(): 스트림 상태 초기화
        __call__(speech_detected, audio_buffer): 음성 데이터에서 화자 활동을 감지하고 녹음 시작/종료를 제어

    """
    def __init__(self, 
                 silence_threshold: int = AudioConfig.SILENCE_THRESHOLD,
                 exit_threshold: int = AudioConfig.EXIT_THRESHOLD):
        self.is_recording = False
        self.speech_buffer = []
        self.stop_count = 0
        self.silence_threshold = silence_threshold
        self.exit_threshold = exit_threshold

    def resetStream(self):
        """스트림 상태 초기화"""
        self.is_recording = False
        self.speech_buffer = []
        self.stop_count = 0
        return {"audio": None, "status": "Reset"}

    def __call__(self, 
                 speech_detected: list,
                 audio_buffer: np.array) -> dict:
        """
        음성 데이터에서 화자 활동을 감지하고 녹음 시작/종료를 제어합니다.

        Args:
            speech_detected (list): 감지된 음성 구간의 타임스탬프 리스트
            audio_buffer (np.array): 현재 오디오 버퍼 데이터
        Returns:
            np.array or None: 녹음이 종료되었을 때 완성된 음성 데이터 배열, 
                                그렇지 않으면 None, 최종 웨이브 파일이 생성되기 전까지 반환을 None으로함         
        """
        has_speech = len(speech_detected) > 0
        user_status = "Silent" #없으면 Silent, 강제 종료되면 Error로 전송
        user_audio = None
        
        
        if has_speech:
            if not self.is_recording:
                self.is_recording = True
                self.stop_count = 0
                self.speech_buffer = []
                user_status = "Speech"
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
                user_status = "Speech" #무음이어도 녹음중이니 Speech로 전송
                
                print(f"연속 무음: {self.stop_count}/{self.silence_threshold}")
                
                if self.stop_count >= self.silence_threshold:
                    speech_data = np.concatenate(self.speech_buffer, axis=0)
                    self.is_recording = False
                    self.stop_count = 0
                    self.speech_buffer = []
                    user_audio = speech_data
                    user_status = "Finished"
                    
            else:
                self.stop_count += 1
                if self.stop_count >= self.exit_threshold:
                    print(f"❌ 연속 {self.exit_threshold}번 무음으로 시스템 종료")
                    user_audio = None
                    user_status = "Error"
                else:
                    user_status = "Silent"


        return {"audio": user_audio, "status": user_status}

_event_checker = _AudioActivityDetection()
_vad_model = VADModel(monitoring=False)

def process_audio_chunk(audio_data,
                        reset:bool=False)-> dict:
    """
    실시간 오디오 청취 및 텍스트 변환 내부 함수
    
    Status
    - 1. Silent: 무음 상태
    - 2. Speech: 음성 감지 상태
    - 3. Finished: 음성 녹음 종료 상태
    - 4. Error: 연속 무음으로 인한 시스템 종료 상태
    - 5. Reset: 스트림 상태 초기화 상태
    
    Args:
        audio_data (np.array): 오디오 신호 배열
        reset (bool): 스트림 상태 초기화 여부
    Returns:
        dict: {
            "status": "Silent" | "Speech" | "Finished" | "Error" | "Reset", 
            "text": 변환된 텍스트 또는 None
        }
    """
    event_checker = _event_checker  
    vad_model = _vad_model
    
    result_status = None
    transcript_text = None

    if reset:
        result = event_checker.resetStream()
        return {"status": result["status"], "text": None}

    if audio_data is not None:
        speech_timestamps = vad_model.get_speech_timestamps(audio_data)
        result = event_checker(speech_timestamps, audio_data)
                
        if result["status"] == "Finished":
            # 임시 파일로 저장
            sf.write("temp_audio.wav", result["audio"], samplerate=AudioConfig.SAMPLERATE)

            # OpenAI Whisper API로 전사
            with open("temp_audio.wav", "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ko"
                )

            result_status = result["status"]
            transcript_text = response.text

        elif result["status"] == "Error":
            result_status = result["status"]
            transcript_text = None

        elif result["status"] in ["Speech", "Silent"]:
            result_status = result["status"]
            transcript_text = None

        elif result["status"] == "Reset":
            result_status = result["status"]
            transcript_text = None
                    
    return {"status": result_status, "text": transcript_text}   
                


# ========== PUBLIC API ==========


if __name__ == '__main__':
    # CLI 모드: 실시간 음성 인식
    result = process_audio_chunk(audio_data=None, reset=True)
    print(f"\n최종 결과: {result}")