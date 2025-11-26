import requests
import json
import time

def get_tts_audio(text_to_speak, language='ko', temperature=0.3, voice_name='mb.wav'):
    """
    FastAPI TTS 서버에 텍스트를 보내고 .wav 파일 데이터를 반환합니다.
    """
    
    # 1. TTS 서버의 IP 주소와 엔드포인트
    #    (TTS 서버와 중간 서버가 같은 장비에 있다면 '127.0.0.1' 사용)
    # tts_server_url = "http://192.168.0.42:8000//generate-speech/"  # <--- TTS 서버 IP로 변경
    tts_server_url = "https://webpage-eating-belly-reduction.trycloudflare.com//generate-speech/"  # <--- TTS 서버 IP로 변경

    print(f"voice_name: {voice_name}")
    # 2. 요청 본문 (main.py의 TTSRequest 모델과 일치하는 딕셔너리)
    payload = {
        "text": text_to_speak,
        "language_id": language,
        "temperature": temperature,
        "audio_prompt_filename": voice_name,   # "swingpark.wav", "chulsoo.wav", "mb.wav", "jaemay.mp3", "moon_short3.wav" 
        # Pydantic 모델에 정의된 다른 파라미터들도 추가할 수 있습니다.
        "repetition_penalty": 3.5
    }
    
    # 3. 요청 헤더
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"TTS 서버({tts_server_url})에 요청 전송 중...")
    start_time = time.time()
    
    try:
        # 4. POST 요청 실행
        #    requests.post의 'json=' 파라미터는 자동으로
        #    - 데이터를 JSON 문자열로 변환
        #    - 'Content-Type: application/json' 헤더를 설정
        response = requests.post(tts_server_url, json=payload)
        
        end_time = time.time()
        print(f"응답 수신 완료. 소요 시간: {end_time - start_time:.2f}초")
        
        # 5. 응답 코드 확인
        if response.status_code == 200:
            # 6. 성공: 응답이 오디오 파일인지 확인
            if 'audio/wav' in response.headers.get('Content-Type', ''):
                # 성공! response.content에 원시 .wav 파일 바이트(bytes)가 들어있습니다.
                print("성공: .wav 파일 데이터 수신 완료.")
                return response.content  # <-- 이것이 .wav 파일 데이터입니다.
            else:
                # 200 코드를 받았지만 오디오가 아닌 경우 (드문 경우)
                print(f"오류: 200 OK를 받았지만 오디오 파일이 아닙니다. 응답: {response.text}")
                return None
        else:
            # 7. 실패: 서버가 JSON 오류 메시지를 반환
            print(f"TTS 서버 오류. 상태 코드: {response.status_code}")
            error_details = response.json() # 오류 내용을 JSON으로 파싱
            print(f"오류 내용: {error_details.get('error', '알 수 없는 오류')}")
            return None
            
    except requests.exceptions.RequestException as e:
        # 네트워크 오류 (예: TTS 서버가 꺼져 있음)
        print(f"TTS 서버 연결 실패: {e}")
        return None