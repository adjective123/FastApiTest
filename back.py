# main.py - Backend Server
# !uvicorn main:app --reload --port 5001

from fastapi import FastAPI, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from datetime import datetime
import time
from typing import List, Optional
from sqlalchemy import create_engine, Column, String, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import json
from pathlib import Path
import os

import get_tts  # 파인튜닝된 tts 서버
# import audiotest_api.judgeTest.tts_test as tts_test  # openai tts 서버

app = FastAPI()

# FRONT_BASE_URL = "http://localhost:3000"
FRONT_BASE_URL = "https://192.168.0.37:3000"
BACK_BASE_URL = "http://localhost:5001"
# BACK_BASE_URL = "https://192.168.0.37:5001"
ATOT_BASE_URL = "http://localhost:8000"
# ATOT_BASE_URL = "https://192.168.0.37:8000"
TTOT_BASE_URL = "http://localhost:8002"
# TTOT_BASE_URL = "https://192.168.0.37:8002"
TTS_BASE_URL = "http://localhost:8004"
# TTS_BASE_URL = "https://192.168.0.37:8004"

# ✅ CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",  # atot 서버
        "http://127.0.0.1:8000",
        "https://192.168.0.37:8000",
        "http://localhost:5001",  # back.py 서버
        "http://127.0.0.1:5001",
        "https://192.168.0.37:5001",
        "http://localhost:8002",  # ttot 서버
        "http://127.0.0.1:8002",
        "https://192.168.0.37:8002",
        "http://localhost:3000",  # 클라이언트 서버
        "http://127.0.0.1:3000",
        "https://192.168.0.37:3000",
        "http://localhost:8004",  # tts 서버
        "http://127.0.0.1:8004",
        "https://192.168.0.37:8004"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== userdata.json 로드 =====
def load_userdata():
    """
    userdata.json 파일을 읽어서 리스트로 반환
    
    Returns:
        list: [{"id": "test", "pwd": "1234", "uuid": 4880911345}, ...]
    """
    try:
        with open("static/userdata.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"✅ userdata.json 로드 성공: {len(data)}명의 사용자")
            return data
    except FileNotFoundError:
        print("❌ static/userdata.json 파일을 찾을 수 없습니다.")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        return []
    except Exception as e:
        print(f"❌ 알 수 없는 오류: {e}")
        return []

USER_DATA = load_userdata()

if USER_DATA:
    print("📋 로드된 사용자 목록:")
    for users in USER_DATA:
        print(USER_DATA[users]['id'], USER_DATA[users]['uuid'])
        # for user in users:
            # print(user)

def get_user_by_id(user_id: str):
    """ID로 사용자 찾기"""
    for user in USER_DATA:
        if user["id"] == user_id:
            return user
    return None

def get_user_by_uuid(uuid: int):
    """UUID로 사용자 찾기"""
    for user in USER_DATA:
        if user["uuid"] == uuid:
            return user
    return None

def authenticate_user(user_id: str, password: str):
    """사용자 인증"""
    for user in USER_DATA:
        if USER_DATA[user]["id"] == user_id and USER_DATA[user]["pwd"] == password:
            return user
    return None

# 공유할 전역 변수
class SharedData:
    input_text = None
    output_text = None
    atot_text = None      # ATOT 변환 결과
    input_wav = None      # 입력 오디오 경로
    ttot_text = None      # TTOT 생성 결과
    uuid = None           # 현재 처리 중인 사용자 UUID

SQLALCHEMY_DATABASE_URL = 'sqlite:///./users.db'
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserDB(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True, index=True, unique=True)
    uuid = Column(Integer, index=True)
    room_id = Column(String, index=True)
    input_text_list = Column(JSON, index=True)       # 텍스트 입력 (채팅)
    output_text_list = Column(JSON, index=True)      # 텍스트 출력 (답변)
    input_wav_list = Column(JSON, index=True)        # 오디오 입력 경로
    atot_text_list = Column(JSON, index=True)        # ATOT 변환 결과
    ttot_text_list = Column(JSON, index=True)        # TTOT 생성 결과
    output_wav_list = Column(JSON, index=True)       # 오디오 출력 경로

class UserData(BaseModel):
    id: str
    uuid: int
    room_id: str
    input_text_list: Optional[List[Optional[str]]] = []
    output_text_list: Optional[List[Optional[str]]] = []
    output_wav_list: Optional[List[Optional[str]]] = []
    
    class Config:
        from_attributes = True

class IncomingMessage(BaseModel):
    message_id: int
    room_id: str
    text: str
    client_type: str

class ProcessedResult(BaseModel):
    message_id: int
    processed_text: str

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# back.py에 추가 (line 113 이전에 추가)

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict] = None

# back.py line 152
@app.post("/api/logindb", response_model=LoginResponse)
async def authenticate_login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    로그인 엔드포인트 (클라이언트에서 직접 호출)
    - userdata.json에서 인증
    - 인증 성공 시 해당 사용자만 DB에 저장
    """
    username = payload.username
    password = payload.password
    # 1️⃣ userdata.json에서 사용자 찾기
    user_info = authenticate_user(username, password)
    # user_info = USER_DATA[username]
    
    if not user_info:
        return LoginResponse(
            success=False,
            message="아이디 또는 비밀번호가 올바르지 않습니다."
        )
    
    db_user = db.query(UserDB).filter(UserDB.uuid == USER_DATA[username]["uuid"]).first()
    print(db_user)
    
    if not db_user:
        db_user = UserDB(
            id=USER_DATA[username]["id"],
            uuid=USER_DATA[username]["uuid"],
            room_id=username,
            input_text_list=[],
            output_text_list=[],
            input_wav_list=[],
            atot_text_list=[],
            ttot_text_list=[],
            output_wav_list=[]
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        print(f"✅ 로그인으로 새 사용자 생성: {user_info['id']} (UUID: {user_info['uuid']})")
        
    # 4️⃣ 응답 반환
    return LoginResponse(
        success=True,
        message="로그인 성공",
        user={
            "id": db_user.id,
            "uuid": db_user.uuid,
            "room_id": db_user.room_id,
            "input_text_list": db_user.input_text_list or [],
            "output_text_list": db_user.output_text_list or [],
            "input_wav_list": db_user.input_wav_list or [],
            "atot_text_list": db_user.atot_text_list or [],
            "ttot_text_list": db_user.ttot_text_list or [],
            "output_wav_list": db_user.output_wav_list or []
        }
    )

# ==============================
# 💬 대화 내역 조회 API
# ==============================
class ConversationItem(BaseModel):
    type: str  # "input" or "output"
    text: str
    index: int

class ConversationResponse(BaseModel):
    user_id: str
    conversation: List[ConversationItem]

@app.get("/api/conversation/{user_id}", response_model=ConversationResponse)
async def get_conversation(user_id: str, db: Session = Depends(get_db)):
    """
    DB에서 사용자의 전체 대화 내역을 조회
    Returns:
        - input_text_list와 output_text_list를 순서대로 합친 대화 내역
    """
    print(f"📚 대화 내역 조회 요청: {user_id}")
    
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    
    if not user:
        # 사용자가 없으면 빈 대화 내역 반환
        print(f"⚠️ 사용자 {user_id} 없음 - 빈 대화 내역 반환")
        return ConversationResponse(
            user_id=user_id,
            conversation=[]
        )
    
    # input_text_list와 output_text_list를 순서대로 합치기
    input_list = user.input_text_list if user.input_text_list else []
    output_list = user.output_text_list if user.output_text_list else []
    
    print(f"📥 입력 메시지: {len(input_list)}개")
    print(f"📤 출력 메시지: {len(output_list)}개")
    
    conversation = []
    max_len = max(len(input_list), len(output_list))
    
    for i in range(max_len):
        # 입력 텍스트
        if i < len(input_list) and input_list[i]:
            conversation.append({
                "type": "input",
                "text": input_list[i],
                "index": i
            })
        
        # 출력 텍스트 (AI 응답)
        if i < len(output_list) and output_list[i]:
            conversation.append({
                "type": "output",
                "text": output_list[i],
                "index": i
            })
    
    print(f"✅ 총 {len(conversation)}개 대화 항목 반환")
    return ConversationResponse(
        user_id=user_id,
        conversation=conversation
    )

@app.post("/process", response_model=ProcessedResult)
async def process_message(msg: IncomingMessage):
    # 텍스트 받은 후 처리 (예시는 그냥 대문자로 바꾸기)
    processed = msg.text
    SharedData.input_text = processed
    SharedData.room_id = msg.room_id

    # 나중에는 여기서
    # - 모델 호출
    # - 전처리 작업
    # - 등등
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{TTOT_BASE_URL}/generate", json={
                "text": processed,
                "user_id": "test",
                "use_rag": True,
                "use_memory": True
            })
            response.raise_for_status()
            data = response.json()
            processed_text = data.get("response")
            SharedData.output_text = processed_text
            
    except httpx.RequestError as e:
        return {"error": f"ttot 서버에 연결할 수 없습니다: {str(e)}"}
    except Exception as e:
        return {"error": f"알 수 없는 오류: {str(e)}"}

    return ProcessedResult(
        message_id=msg.message_id,
        processed_text=processed_text,
    )

@app.get('/users', response_model=List[UserData])
async def get_users(db: Session=Depends(get_db)):
    """모든 사용자 조회"""
    try:
        users = db.query(UserDB).all()
        # None 값을 빈 리스트로 안전하게 변환
        for user in users:
            user.id = user.id or ""
            user.uuid = user.uuid or 0
            user.room_id = user.room_id or "default"
            user.input_text_list = user.input_text_list or []
            user.output_text_list = user.output_text_list or []
        return users
    except Exception as e:
        print(f"❌ /users 엔드포인트 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"사용자 조회 실패: {str(e)}")

@app.get('/users/{uuid}', response_model=UserData)
async def get_user(uuid: int, db: Session=Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.uuid==uuid).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get('/users/{uuid}/input')
async def upload_input(uuid: int, db: Session=Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.uuid==uuid).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user.uuid, "input_text": user.input_text_list}
  
@app.get('/users/{uuid}/output')
async def get_user_output(uuid: int, db: Session=Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.uuid==uuid).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user.uuid, "output_text": user.output_text_list}

voice_name_dict = {"0": "mb.wav", "1": "swingpark.wav", "2": "chulsoo.wav", "3": "jaemay.mp3", "4": "moon_short3.wav"}

# ✅ 텍스트 기반 파이프라인 (ATOT 없이 텍스트 → TTOT → DB 저장)
@app.post("/run-text-pipeline")
async def run_text_pipeline(
    text: str = Form(...),
    user_id: str = Form(...),
    mode: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    텍스트 기반 파이프라인 (front에서 채팅 메시지 처리용)
    1. 사용자가 입력한 텍스트 받기
    2. TTOT 서버에서 텍스트→텍스트 생성
    3. DB에 저장
    
    Args:
        text: 사용자 입력 텍스트
        user_id: 사용자 ID
    """
    result = {
        "step1_input": None,
        "step2_ttot": None,
        "success": False,
        "errors": []
    }
    
    print("\n" + "="*60)
    print(f"🚀 텍스트 파이프라인 시작 (사용자: {user_id})")
    print(f"📝 입력 텍스트: {text}")
    print("="*60)
    
    # ====== STEP 1: 입력 텍스트 저장 ======
    SharedData.input_text = text
    result["step1_input"] = {
        "success": True,
        "text": text
    }
    
    # ====== STEP 2: TTOT (텍스트→텍스트) ======
    print("\n🤖 TTOT 서버 호출 중...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            ttot_response = await client.post(
                f"{TTOT_BASE_URL}/generate",
                json={
                    "text": text,
                    "user_id": user_id,
                    "use_rag": True,
                    "use_memory": True
                }
            )
            ttot_response.raise_for_status()
            ttot_data = ttot_response.json()
            
            SharedData.output_text = ttot_data.get("response")
            
            result["step2_ttot"] = {
                "success": True,
                "ttot_text": SharedData.output_text
            }
            print(f"✅ TTOT 완료: {SharedData.output_text}")
            
    except Exception as e:
        error_msg = f"TTOT 실패: {str(e)}"
        print(f"❌ {error_msg}")
        result["errors"].append(error_msg)
        result["step2_ttot"] = {"success": False, "error": error_msg}
        return result

    # ====== STEP 3: TTS (텍스트→음성) ======
    print("\n🎵 TTS 서버 호출 중...")

    output_filename = None
    tts_success = False
    tts_error = None

    try:
        wav_file_data = get_tts.get_tts_audio(SharedData.output_text, language='ko', voice_name=voice_name_dict[mode])  # 파인튜닝된 tts 서버
        '''  # openai tts 서버
        async with httpx.AsyncClient(timeout=30.0) as client:
            tts_response = await client.post(
                f"{TTS_BASE_URL}/generate-speech/",
                json={"request_text": SharedData.output_text},
                headers={"Content-Type": "application/json"}
            )
            tts_response.raise_for_status()
            wav_file_data = tts_response.content
        # '''
        
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            # 사용자가 없으면 자동 생성
            print(f"⚠️ User {user_id}가 없어서 자동 생성합니다...")
            
            # userdata.json에서 uuid 가져오기 시도
            import json
            from pathlib import Path as PathLib
            userdata_path = PathLib("static/userdata.json")
            user_uuid = None
            
            if userdata_path.exists():
                try:
                    with open(userdata_path, "r", encoding="utf-8") as f:
                        user_data_list = json.load(f)
                        for user_data in user_data_list:
                            if user_data == user_id:
                                user_uuid = user_data_list[user_data]["uuid"]
                                break
                except Exception as e:
                    print(f"⚠️ userdata.json 읽기 실패: {e}")
            
            # userdata.json에 없으면 uuid 자동 생성
            if user_uuid is None:
                user_uuid = abs(hash(user_id)) % (10**10)
                print(f"⚠️ userdata.json에 없어서 uuid 자동 생성: {user_uuid}")
            
            # DB에 새 사용자 생성
            new_user = UserDB(
                id=user_id,
                uuid=user_uuid,
                room_id="default",
                input_text_list=[],
                output_text_list=[],
                input_wav_list=[],
                atot_text_list=[],
                ttot_text_list=[],
                output_wav_list=[]
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user = new_user
            print(f"✅ User {user_id} 생성 완료 (UUID: {user_uuid})")
        
        if wav_file_data and len(wav_file_data) > 0:
            PATH = Path(f"./wav_files/{user.uuid}")
            if not PATH.exists():
                os.makedirs(PATH)
                
            output_filename = f"{PATH}/received_audio.wav"
            
            with open(output_filename, 'wb') as f:
                # if os.path.exists(output_filename):
                #     os.remove(output_filename)
                f.write(wav_file_data)
            tts_success = True
            print(f"✅ TTS 성공: {output_filename}, 크기: {len(wav_file_data)} bytes")
        else:
            tts_error = "TTS 서버에서 빈 데이터를 받았습니다"
            print(f"⚠️ {tts_error}")
            
    except httpx.ConnectError as e:
        tts_error = f"TTS 서버 연결 실패 (port 8004 확인): {str(e)}"
        print(f"❌ {tts_error}")
    except httpx.HTTPStatusError as e:
        tts_error = f"TTS API 오류 (상태: {e.response.status_code})"
        print(f"❌ {tts_error}")
    except Exception as e:
        tts_error = f"TTS 오류: {str(e)}"
        print(f"❌ {tts_error}")

    result["step3_tts"] = {
        "success": tts_success,
        "output_wav": output_filename,
        "tts_error": tts_error
    }

    # ====== STEP 4: DB 저장 ======
    print("\n💾 DB 저장 중...")
    
    # 사용자 조회
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        error_msg = f"User {user_id}를 찾을 수 없습니다"
        print(f"❌ {error_msg}")
        result["errors"].append(error_msg)
        return result
    
    # DB에 저장
    user.input_text_list = (user.input_text_list or []) + [SharedData.input_text or ""]
    user.output_text_list = (user.output_text_list or []) + [SharedData.output_text or ""]
    
    # output_wav 저장
    if output_filename:
        user.output_wav_list = (user.output_wav_list or []) + [output_filename]
    else:
        user.output_wav_list = (user.output_wav_list or []) + [None]
    
    db.commit()
    db.refresh(user)
    
    result["success"] = True
    result["user_id"] = user_id
    result["final_data"] = {
        "input_text": SharedData.input_text,
        "output_text": SharedData.output_text,
        "output_wav": output_filename
    }
    
    print("\n" + "="*60)
    print("✅ 텍스트 파이프라인 완료!")
    print("="*60)
    
    return result

@app.get("/memory")
async def get_users():
    user_dict = {}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACK_BASE_URL}/users")
            response.raise_for_status()
            data = response.json()
            
            for user in data:
                user_dict[user["uuid"]] = {
                    "uuid": user["uuid"],
                    "input_text_list": user["input_text_list"],
                    "output_text_list": user["output_text_list"]
                }
            
            return user_dict

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Backend 서버 연결 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알 수 없는 오류: {str(e)}")

# 클라이언트에서 호출 순서:
# 방법 1 (기존): 
#   1. GET /atot -> 2. GET /ttot -> 3. POST /process-audio
# 방법 2 (새로운, 추천):
#   1. ATOT 서버에서 POST /run-model 실행
#   2. POST /run-full-pipeline (모든 단계 자동 처리)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("back:app", host="127.0.0.1", port=5001, reload=True)  # 5000 → 5001 (macOS AirPlay 충돌 방지)

'''
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0",              # 외부 접속 허용
        port=5001,
        ssl_keyfile="./key.pem",     # 🔑 개인키 파일 경로
        ssl_certfile="./cert.pem"    # 📜 인증서 파일 경로
    )
# '''