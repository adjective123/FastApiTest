# Backend Server (main.py)

FastAPI 기반 백엔드 서버 - 마이크로서비스 통합 관리 및 데이터베이스 관리

## 📌 서버 개요

포트: **5000**  
실행 명령어: `uvicorn main:app --reload --port 5000`

이 서버는 다음 마이크로서비스들을 통합 관리하는 중앙 백엔드 역할을 합니다:
- **ATOT 서버** (port 8000): Audio to Text - 음성→텍스트 변환
- **TTOT 서버** (port 8002): Text to Text - 텍스트 생성/변환
- **TTS 서버** (port 8004): Text to Speech - 텍스트→음성 변환

---

## 🗂️ 데이터베이스 구조

### SQLite Database: `users.db`

**UserDB 테이블:**
```python
- id: Integer (Primary Key) - 사용자 ID
- input_wav_list: JSON - 입력 음성 파일 경로 리스트
- atot_text_list: JSON - ATOT 결과 텍스트 리스트
- ttot_text_list: JSON - TTOT 생성 텍스트 리스트
- output_wav_list: JSON - 출력 음성 파일 경로 리스트
```

### SharedData (전역 공유 데이터)
```python
- user_id: 현재 처리 중인 사용자 ID
- input_wav: 입력 음성 파일 경로
- atot_text: ATOT 변환 결과 텍스트
- ttot_text: TTOT 생성 결과 텍스트
```

---

## 🔗 API 엔드포인트

### 1. 기본 엔드포인트

#### `GET /`
서버 상태 확인 및 사용자 조회/생성

**응답:**
```json
{
  "message": "This is the Backend Server",
  "user": {
    "id": 10,
    "input_wav_list": [],
    "atot_text_list": [],
    "ttot_text_list": [],
    "output_wav_list": []
  }
}
```

#### `GET /users`
모든 사용자 조회

**응답:** UserData 리스트

#### `GET /users/{user_id}`
특정 사용자 조회

**파라미터:**
- `user_id`: 사용자 ID (int)

---

### 2. 마이크로서비스 연동

#### `GET /atot`
ATOT 서버에서 음성→텍스트 변환 결과 가져오기

**동작:**
- ATOT 서버 (`http://127.0.0.1:8000/run-model`) 호출
- 결과를 SharedData에 저장

**응답:**
```json
{
  "user_id": 10,
  "input_wav": "/static/uploads/abc123.wav",
  "atot_text": "변환된 텍스트"
}
```

#### `GET /ttot`
TTOT 서버에서 텍스트→텍스트 생성 결과 가져오기

**동작:**
- TTOT 서버 (`http://127.0.0.1:8002/generate`) 호출
- 결과를 SharedData에 저장

**응답:**
```json
{
  "user_id": 10,
  "ttot_text": "생성된 응답 텍스트"
}
```

#### `POST /process-audio`
저장된 데이터를 사용해 TTS 처리 및 DB 저장

**동작:**
1. SharedData의 ttot_text를 TTS 서버로 전송
2. 생성된 음성 파일을 `received_audio.wav`로 저장
3. 모든 데이터를 DB에 저장

**응답 (성공시):**
```json
{
  "user_id": 10,
  "input_wav": "/static/uploads/abc123.wav",
  "atot_text": "변환된 텍스트",
  "ttot_text": "생성된 응답",
  "output_wav": "received_audio.wav",
  "output_wav_list": ["received_audio.wav"],
  "tts_success": true,
  "message": "✅ 성공! TTS 오디오를 'received_audio.wav'로 저장했습니다."
}
```

**응답 (TTS 실패시):**
```json
{
  "user_id": 10,
  "input_wav": "/static/uploads/abc123.wav",
  "atot_text": "변환된 텍스트",
  "ttot_text": "생성된 응답",
  "output_wav": null,
  "output_wav_list": [null],
  "tts_success": false,
  "message": "⚠️ 데이터는 저장했지만 TTS 생성 실패",
  "tts_error": "TTS 서버 연결 실패 (port 8004가 실행 중인지 확인)"
}
```

---

### 3. 통합 파이프라인 (권장)

#### `POST /run-full-pipeline`
전체 파이프라인을 한 번에 실행 (모든 단계 자동화)

**동작 순서:**
1. **STEP 1**: ATOT 서버에서 음성→텍스트 변환
2. **STEP 2**: TTOT 서버에서 텍스트→텍스트 생성
3. **STEP 3**: TTS 서버에서 음성 생성 + DB 저장

**응답:**
```json
{
  "step1_atot": {
    "success": true,
    "user_id": 10,
    "input_wav": "/static/uploads/abc123.wav",
    "atot_text": "변환된 텍스트"
  },
  "step2_ttot": {
    "success": true,
    "user_id": 10,
    "ttot_text": "생성된 응답"
  },
  "step3_tts": {
    "success": true,
    "output_wav": "received_audio.wav",
    "tts_error": null
  },
  "success": true,
  "user_id": 10,
  "final_data": {
    "input_wav": "/static/uploads/abc123.wav",
    "atot_text": "변환된 텍스트",
    "ttot_text": "생성된 응답",
    "output_wav": "received_audio.wav"
  },
  "errors": []
}
```

---

## 🚀 사용법

### 방법 1: 단계별 실행 (기존 방식)

```python
# 1단계: ATOT 결과 가져오기
GET http://127.0.0.1:5000/atot

# 2단계: TTOT 결과 가져오기
GET http://127.0.0.1:5000/ttot

# 3단계: TTS 처리 및 저장
POST http://127.0.0.1:5000/process-audio
```

### 방법 2: 통합 파이프라인 (권장)

```python
# 1. ATOT 서버에서 먼저 음성/텍스트 입력
POST http://127.0.0.1:8000/run-model

# 2. 백엔드에서 전체 파이프라인 실행
POST http://127.0.0.1:5000/run-full-pipeline
```

---

## ⚙️ 설정

### 사용자 ID 설정
```python
USER_ID = 10  # 기본 사용자 ID (필요시 변경 가능)
```

### CORS 설정
다음 origin들이 허용됩니다:
- `http://localhost:8000` (ATOT 서버)
- `http://localhost:5000` (Backend 서버)
- `http://localhost:8002` (TTOT 서버)

### 서버 포트 정보
| 서버 | 포트 | 역할 |
|------|------|------|
| Backend | 5000 | 중앙 관리 서버 |
| ATOT | 8000 | 음성→텍스트 |
| TTOT | 8002 | 텍스트→텍스트 |
| TTS | 8004 | 텍스트→음성 |

---

## 🔧 에러 처리

### TTS 실패 처리
- TTS 서버 연결 실패 시에도 데이터는 DB에 저장됨
- `output_wav`는 `null`로 저장
- 에러 메시지는 응답에 포함됨

### 타임아웃 설정
- HTTP 요청 타임아웃: **30초**
```python
async with httpx.AsyncClient(timeout=30.0) as client:
    ...
```

---

## 📦 필수 라이브러리

```bash
pip install fastapi uvicorn httpx sqlalchemy pydantic
```

---

## 🐛 문제 해결

### 1. 서버 연결 실패
```
❌ atot 서버에 연결할 수 없습니다
```
**해결:** ATOT 서버가 실행 중인지 확인 (`uvicorn atot.main:app --reload --port 8000`)

### 2. TTS 연결 실패
```
❌ TTS 서버 연결 실패 (port 8004가 실행 중인지 확인)
```
**해결:** TTS 서버가 실행 중인지 확인

### 3. User not found
```
❌ User not found
```
**해결:** 먼저 `GET /` 엔드포인트를 호출하여 사용자 생성

### 4. DB 오류
```
❌ 서버 오류: ...
```
**해결:** `users.db` 파일 권한 확인 또는 삭제 후 재생성

---

## 📝 로그 예시

```
✅ 새 사용자 생성: ID=10
🚀 전체 파이프라인 시작
1️⃣  ATOT 서버 호출 중...
✅ ATOT 완료: 변환된 텍스트
2️⃣  TTOT 서버 호출 중...
✅ TTOT 완료: 생성된 응답
3️⃣  TTS 처리 및 DB 저장 중...
✅ TTS 성공: received_audio.wav, 크기: 12345 bytes
✅ 전체 파이프라인 완료!
```

---

## 🔗 관련 파일

- `atot/main.py` - ATOT 서버 (음성→텍스트)
- `ttot/main.py` - TTOT 서버 (텍스트→텍스트)
- `audiotest_api/judgeTest/tts_test.py` - TTS 관련 테스트
- `test.py` - 통합 테스트 스크립트
- `users.db` - SQLite 데이터베이스 파일

---

## 📄 라이센스

내부 프로젝트용

