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
    """
    음성을 감지하는 VAD 모델 래퍼 클래스 (private)
    생성하면 동시에 VAD 모델을 로드합니다.
    
    Attributes:
        model: 로드된 VAD 모델
    """
    def __init__(self)-> None:
        self.model = load_silero_vad()

    """
    오디오 데이터에서 음성 구간의 타임스탬프를 반환합니다.
    
    Args:
        audio_data (np.array): 오디오 신호 배열

    Returns:
        list: 감지된 음성 구간의 타임스탬프 리스트
    """    
    def get_speech_timestamps(self, audio_data)->list:

        print(f"[VAD] audio_data type: {type(audio_data)}")
        print(f"[VAD] audio_data dtype: {audio_data.dtype}")
        print(f"[VAD] audio_data shape: {audio_data.shape}")
        print(f"[VAD] audio_data range: [{audio_data.min():.4f}, {audio_data.max():.4f}]")
  
        return get_speech_timestamps(
            audio_data,
            self.model,
        )

class _AudioStream:
    """
    음성을 실시간으로 수집하는 오디오 스트림 클래스 (private)
    chunk 단위로 오디오 데이터를 큐에 저장합니다.

    추후 프론트엔드와 협의해서 실시간으로 청크를 받아들인다고 하면 필요없는 클래스
    
    Attributes:
        queue:  오디오 청크를 저장하는 큐
        stream: 사운드디바이스 입력 스트림
    """
    def __init__(self)-> None:
        self.queue = queue.Queue()
        self.stream = None


    def init_stream(self):
        """
        input 스트림 초기화

        """        
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
        """
        input 스트림 시작으로 사전에 초기화 필요

        Raises:
            RuntimeError: 스트림이 초기화되지 않았을 때
        """
        if self.stream is not None:
            self.stream.start()
            print("오디오 스트림 시작됨")
        else:
            raise RuntimeError("스트림이 초기화되지 않았습니다.")



    def stop_stream(self):
        """
        input 스트림 종료

        """
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            print("오디오 스트림 종료됨")
        elif self.stream is None:
            print("스트림이 이미 종료되었거나 초기화되지 않았습니다.")

    def process_audio_batch(self, 
                            target=AudioConfig.BATCH_SIZE):
        """
        chunk 단위로 오디오 데이터를 수집하여 하나의 배열로 반환

        Args:
            target (int): 수집할 청크의 개수, 총 샘플의 개수는 입력단위로 받는 샘플수 * target 으로 계산
        Returns:
            np.array: 수집된 오디오 신호 배열

        """    
        chunks = []
        
        try:
            while len(chunks) < target:
                chunk = self.queue.get(timeout=1.0)
                chunks.append(chunk)
        except queue.Empty:
            pass
            
        return np.concatenate(chunks, axis=0).squeeze() if chunks else None
        
    def _audio_callback(self, indata, frames, time, status):
        """
        오디오 스트림 콜백 함수, 스트림 클래스의 큐에 오디오 청크를 저장합니다.

        Args:
            indata (np.array): 입력 오디오 데이터   
            frames (int): 프레임 수
            time: 타임 정보
            status: 상태 정보
        Returns:
            None

        """            
        
        if status:
            print(status, file=sys.stderr)
        self.queue.put(indata.copy())


class _AudioActivityDetection:
    """
    음성 데이터를 읽어 와서 화자가 대화를 하고 있는지 감시
    
    Attributes:
        is_recording:  현재 녹음중인 여부로 최초로 음성이 감지되면 True로 변경되고,
                       연속으로 무음이 silence_threshold번 감지되면 False로 변경됩니다.
        speech_buffer: 녹음된 음성 데이터를 저장하는 버퍼  
        stop_count: 연속 무음 카운트
        silence_threshold: 연속 무음으로 간주하는 임계값
    """
    def __init__(self, silence_threshold: int = AudioConfig.SILENCE_THRESHOLD):
        self.is_recording = False
        self.speech_buffer = []
        self.stop_count = 0
        self.silence_threshold = silence_threshold


    def __call__(self, 
                 speech_detected: list,
                 audio_buffer: np.array) -> np.array:
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
                    
                    print(f"🛑 연속 {self.silence_threshold}번 무음으로 종료")
                    return speech_data

        return None


def _get_vad_model():
    """
    전역 VAD 모델 싱글톤 인스턴스를 반환하는 내부 함수

    Returns:
        _VADModel: VAD 모델 인스턴스
    """
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


    while True:
            audio_data = stream.process_audio_batch()
            print(f"오디오 데이터 수신: {audio_data.shape if audio_data is not None else None}")
            print(audio_data)
            
            if audio_data is not None:
                speech_timestamps = vad_model.get_speech_timestamps(audio_data)
                print(f"감지된 음성 구간: {speech_timestamps}")

                result = event_checker(speech_timestamps, audio_data)
                print("이벤트 체크 완료")
                
                if result is not None:
                    
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