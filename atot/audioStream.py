#!/usr/bin/env python3
"""Plot the live microphone signal(s) with matplotlib.

Matplotlib and NumPy have to be installed.

"""
import argparse
from dataclasses import dataclass
import queue
import sys
from openai import OpenAI
import time
from silero_vad import load_silero_vad, read_audio, get_speech_timestamps
import soundfile as sf

from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import numpy as np
import sounddevice as sd

client = OpenAI(api_key="")

@dataclass
class audioArgs:
    device: int = None
    samplerate: int = 16000 # 
    channels: int = 1  # 1 for 'mono' or 2 for 'stereo'
    chunksize: int = 64
    batch_size : int = 100
    audiomin_threshold : float = 0.4  # 연속 무음 감지 임계값

class AudioStream:
    def __init__(self):
        self.Queue = queue.Queue()
        self.stream = None

    def init_stream(self):
        if self.stream is None:
            self.stream = sd.InputStream(
                device= audioArgs().device,
                blocksize=audioArgs.chunksize,
                channels=audioArgs.channels,
                samplerate=audioArgs.samplerate, 
                callback=self.audio_callback)
            print("오디오 스트림 초기화 완료")
        else:
            print("오디오 스트림이 이미 초기화되어 있습니다.")

    def start_stream(self):
        if self.stream is not None:
            self.stream.start()
            print("오디오 스트림 시작됨")
        else:
            print("스트림이 초기화되지 않았습니다. 먼저 init_stream()을 호출하세요.")

    def stop_stream(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            print("오디오 스트림 종료됨")
        else:
            print("종료할 스트림이 없습니다.")

    def process_audio_batch(self,target = audioArgs.batch_size):
        chunks = []
        
        while len(chunks) < target:
            # 큐에서 하나씩 가져와서 버퍼에 추가
            chunk = self.Queue.get(timeout=1.0)
            chunks.append(chunk)
            
        if chunks:
            return np.concatenate(chunks, axis=0).squeeze()
        else:
            return None     
        
    def audio_callback(self,indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        # Fancy indexing with mapping creates a (necessary!) copy:
        self.Queue.put(indata.copy())



class AudioActivityDetection:
    def __init__(self, silence_threshold: int = 3):
        self.is_recording = False
        self.speech_buffer = []
        self.speech_id = 0
        self.prev_status = "nonspeech"
        self.stop_count = 0
        self.silence_threshold = silence_threshold

    def __call__(self, time_checker, buffers):
        self.current_status = len(time_checker) > 0
        
        if self.current_status:  # 음성 감지됨
            if not self.is_recording:
                self.is_recording = True
                self.speech_buffer = []
                print("🎤 음성 시작")
            
            self.speech_buffer.append(buffers)
            
            # ✅ 음성이 감지되면 무음 카운트 리셋!
            if self.stop_count > 0:
                print(f"음성 재감지 → 무음 카운트 리셋 ({self.stop_count} → 0)")
                self.stop_count = 0
            
            self.prev_status = "speech"
            
        else:  # 무음
            if self.is_recording:
                zero_data = np.zeros_like(buffers)
                self.speech_buffer.append(zero_data)
                
                # ✅ 연속 무음만 카운트
                self.stop_count += 1
                self.prev_status = "nonspeech"
                
                print(f"연속 무음: {self.stop_count}/{self.silence_threshold}")
                
                if self.stop_count >= self.silence_threshold:
                    speech_data = np.concatenate(self.speech_buffer, axis=0)
                    self.is_recording = False
                    self.stop_count = 0
                    self.speech_buffer = []
                    
                    print(f"🛑 연속 {self.silence_threshold}번 무음으로 종료")
                    return speech_data

        return None

def listen_and_transcribe():
    """음성을 수집하고 텍스트로 변환하는 함수"""
    model = load_silero_vad()
    
    stream = AudioStream()
    stream.init_stream()
    stream.start_stream()
    event_checker = AudioActivityDetection()

    print("스트림 시작됨 - 말씀해주세요")

    while True:
        audio_data = stream.process_audio_batch(target=audioArgs.batch_size)
        if audio_data is not None:
            print(f"배치 크기: {audio_data.shape}")
            
            speech_timestamps = get_speech_timestamps(
                audio_data,
                model,
                return_seconds=False,
            )
            print(f"음성 구간: {speech_timestamps}")
            result = event_checker(
                speech_timestamps,
                audio_data
            )
            if result is not None:
                print(f"저장된 음성 클립 {event_checker.speech_id}, 길이: {result.shape}")
                sf.write("temp_audio.wav", result, samplerate=audioArgs.samplerate)

                with open("temp_audio.wav", "rb") as audio_file:
                    response = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="ko"
                    )

                transcript_text = response.text
                print(f"변환된 텍스트: {transcript_text}")
                
                # 스트림 멈추고 텍스트 반환
                stream.stop_stream()
                return transcript_text

        else:
            print("배치 수집 실패")
            time.sleep(0.1)

if __name__ == '__main__':
    text = listen_and_transcribe()
    print(f"\n최종 결과: {text}")