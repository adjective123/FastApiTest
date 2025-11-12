# main.py

# !uvicorn main:app --reload --port 5000
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO
import httpx

app = FastAPI()

@app.get('/')
async def read_root():
    return {'message' : "This is the Backend Server"}

@app.post('/atot/')
async def post_atot():
    """
    atot 서버에서 생성된 텍스트만 중간 서버로 불러와서 반환.
    """
    try:
        async with httpx.AsyncClient() as client:
            payload = {'mode': 'audio'}
            response = await client.post(
                'http://localhost:8000/run-model',  # atot 서버의 엔드포인트
                data=payload,
                timeout=10.0
            )

            if response.status_code != 200:
                return {"error": f"atot 서버 오류: {response.status_code}"}

            try:
                result = response.json()
            except Exception as e:
                return {"error": f"응답 JSON 파싱 실패: {str(e)}"}

            # 텍스트만 추출해서 반환 (result 구조에 따라 조정)
            # 일반적으로 result["result"]에 텍스트가 있음
            atot_text = result.get("result")
            return {"atot_text": atot_text}  # 텍스트만 반환

    except httpx.RequestError as e:  # 연결 에러
        return {"error": f"atot 서버에 연결할 수 없습니다: {str(e)}"}
    except Exception as e:  # 기타 에러
        return {"error": f"알 수 없는 오류: {str(e)}"}
    
@app.post('/ttot/')
async def post_ttot():
    """
    ttot 서버에서 생성된 텍스트만 중간 서버로 불러와서 반환.
    """
    try:
        async with httpx.AsyncClient() as client:
            payload = {'mode': 'audio'}
            response = await client.post(
                'http://localhost:8001/run-model',  # ttot 서버의 엔드포인트
                data=payload,
                timeout=10.0
            )

            if response.status_code != 200:
                return {"error": f"ttot 서버 오류: {response.status_code}"}

            try:
                result = response.json()
            except Exception as e:
                return {"error": f"응답 JSON 파싱 실패: {str(e)}"}

            # 텍스트만 추출해서 반환 (result 구조에 따라 조정)
            # 일반적으로 result["result"]에 텍스트가 있음
            ttot_text = result.get("result")
            return {"ttot_text": ttot_text}  # 텍스트만 반환

    except httpx.RequestError as e:  # 연결 에러
        return {"error": f"atot 서버에 연결할 수 없습니다: {str(e)}"}
    except Exception as e:  # 기타 에러
        return {"error": f"알 수 없는 오류: {str(e)}"}
"""
@app.post('/ttoa/')
async def post_ttoa():
    """
    # ttoa 서버에서 생성된 wav 파일만 중간 서버로 불러와서 반환.
    """
    try:
        async with httpx.AsyncClient() as client:
            payload = {'mode': 'audio'}
            response = await client.post(
                'http://localhost:8002/run-model',  # ttoa 서버의 엔드포인트
                data=payload,
                timeout=30.0
            )

            if response.status_code != 200:
                return {"error": f"ttoa 서버 오류: {response.status_code}"}

            try:
                # 응답이 바이너리(wav) 파일이라고 가정
                wav_content = response.content
            except Exception as e:
                return {"error": f"응답 처리 실패: {str(e)}"}

            return StreamingResponse(BytesIO(wav_content), media_type="audio/wav")

    except httpx.RequestError as e:  # 연결 에러
        return {"error": f"ttoa 서버에 연결할 수 없습니다: {str(e)}"}
    except Exception as e:  # 기타 에러
        return {"error": f"알 수 없는 오류: {str(e)}"}
# """
