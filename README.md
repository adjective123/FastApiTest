# 🎙️ AI Voice Chatbot Project

FastAPI 기반 음성 AI 챗봇 시스템 - 음성 인식, AI 응답 생성, 음성 합성을 통합한 완전한 대화형 챗봇

---

## 📌 프로젝트 개요

이 프로젝트는 사용자의 음성을 인식하고 AI가 텍스트와 음성으로 응답하는 풀스택 음성 챗봇 시스템입니다.

### 🎯 주요 기능

- 🎤 **실시간 음성 인식** (Speech-to-Text)
- 🤖 **AI 기반 대화 생성** (LangChain + OpenAI)
- 🔊 **음성 합성** (Text-to-Speech, 5가지 음성 모드)
- 💬 **텍스트 채팅** 지원
- 👤 **사용자 인증** 및 **대화 내역 관리**
- 📱 **반응형 웹 인터페이스**
- 🔒 **HTTPS 지원** (외부 기기 접속 가능)
- 🎬 **GIF 애니메이션** (AI 응답 시 캐릭터 움직임)

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────┐
│  브라우저 (https://192.168.0.37:3000)             │
│  - 웹 UI (HTML/CSS/JS)                          │
│  - 음성 녹음 (WebAudio API)                       │
│  - 실시간 채팅 인터페이스                             │
└────────────────┬────────────────────────────────┘
                 │ HTTPS (마이크 접근 가능)
                 ↓
┌────────────────────────────────────────────────┐
│  front.py (포트 3000) - Frontend Server         │
│  - HTTPS 서버 (SSL/TLS)                         │
│  - 정적 파일 제공                                 │
│  - API 프록시                                    │
│  - 로그인/회원가입                                 │
└────────────────┬───────────────────────────────┘
                 │ HTTP (서버 간 통신)
                 ↓
┌────────────────────────────────────────────────┐
│  back.py (포트 5001) - Backend Server           │
│  - 중앙 제어 서버                                  │
│  - 데이터베이스 관리 (SQLite)                       │
│  - 마이크로서비스 통합                               │
│  - 사용자 데이터 관리                               │
└────┬────────┬────────┬──────────────────────────┘
     │        │        │
     ↓        ↓        ↓
┌─────────┐ ┌─────────┐ ┌─────────┐
│  ATOT   │ │  TTOT   │ │   TTS   │
│ (8000)  │ │ (8002)  │ │ (8004)  │
│ 음성→텍스트│ │ AI 대화  │ │ 텍스트→음성│
└─────────┘ └─────────┘ └─────────┘
```

---

## 📁 프로젝트 구조

```
ChatbotProject/
├── front.py                    # 프론트엔드 서버 (포트 3000, HTTPS)
├── back.py                     # 백엔드 서버 (포트 5001, HTTP)
├── get_tts.py                  # TTS 유틸리티
├── test.py                     # 통합 테스트 스크립트
├── requirements.txt            # Python 패키지 의존성
├── users.db                    # SQLite 데이터베이스
├── cert.pem                    # SSL 인증서
├── key.pem                     # SSL 개인키
│
├── static/                     # 웹 리소스
│   ├── index.html             # 메인 HTML
│   ├── scripts.js             # JavaScript (700+ 줄)
│   ├── style.css              # 스타일시트
│   ├── processor.js           # AudioWorklet 프로세서
│   ├── userdata.json          # 사용자 정보
│   ├── maicon.png             # 정지 이미지
│   ├── talk.gif               # 말하는 애니메이션
│   └── favicon.ico            # 파비콘
│
├── atot/                       # 음성 인식 서버 (포트 8000)
│   ├── audioTest/             # 오디오 스트리밍 처리
│   └── judgeTest/             # VAD + STT (Silero VAD + Whisper)
│       ├── main.py
│       ├── config.json
│       └── audio_data/        # 음성 데이터
│
├── ttot/                       # AI 대화 생성 (포트 8002)
│   ├── main.py                # FastAPI 서버
│   ├── config.py              # 설정
│   ├── services.py            # 대화 생성 로직
│   ├── rag_manager.py         # RAG (검색 증강 생성)
│   ├── memory_manager.py      # 대화 메모리 관리
│   ├── llm_manager.py         # LLM 통합
│   ├── system_prompt.json     # 시스템 프롬프트
│   ├── chat_history/          # 사용자별 대화 내역
│   └── chroma_db/             # 벡터 DB (ChromaDB)
│
└── wav_files/                  # 생성된 음성 파일
    └── {uuid}/
        └── received_audio.wav
```

---

## 🚀 서버 실행 방법

### 1️⃣ 필수 패키지 설치

```bash
pip install -r requirements.txt
```

### 2️⃣ SSL 인증서 생성 (최초 1회)

```bash
cd ChatbotProject
openssl req -x509 -newkey rsa:4096 -nodes \
  -out cert.pem \
  -keyout key.pem \
  -days 365 \
  -subj "/CN=192.168.0.37"
```

### 3️⃣ 서버 실행 (4개 터미널)

**터미널 1: Frontend 서버 (HTTPS)**

```bash
python front.py
# https://192.168.0.37:3000 또는 https://localhost:3000
```

**터미널 2: Backend 서버**

```bash
python back.py
# http://127.0.0.1:5001
```

**터미널 3: ATOT 서버 (음성 인식)**

```bash
cd atot/judgeTest
python main.py
# http://127.0.0.1:8000
```

**터미널 4: TTOT 서버 (AI 대화)**

```bash
cd ttot
python main.py
# http://127.0.0.1:8002
```

### 4️⃣ 브라우저 접속

```
https://192.168.0.37:3000
```

- ⚠️ 인증서 경고 표시 시: **"고급" → "계속 진행"** 클릭
- 🎤 마이크 권한 요청 시: **"허용"** 클릭

---

## 🔌 API 엔드포인트

### Frontend Server (front.py:3000)

#### **사용자 인증**

- `POST /api/login` - 로그인
- `POST /api/register` - 회원가입
- `GET /api/get_uuid?username={user}` - UUID 조회

#### **채팅 메시지**

- `GET /api/messages?room_id={room}` - 메시지 목록
- `POST /api/messages` - 메시지 전송 (텍스트 + AI 응답)

#### **대화 내역**

- `GET /api/conversation/{user_id}` - 전체 대화 내역 조회

#### **음성 스트리밍**

- `POST /start` - 음성 녹음 세션 시작
- `POST /ingest-chunk` - 오디오 청크 전송 (실시간 STT)

---

### Backend Server (back.py:5001)

#### **사용자 관리**

- `GET /users` - 모든 사용자 조회
- `GET /users/{uuid}` - 특정 사용자 조회
- `POST /api/logindb` - 로그인 처리 (DB 저장)

#### **텍스트 파이프라인**

- `POST /run-text-pipeline` - 텍스트 → TTOT → TTS → DB 저장
  ```json
  {
    "text": "사용자 입력 텍스트",
    "user_id": "username",
    "mode": "0"  // 0-4: 음성 모드
  }
  ```

#### **대화 내역**

- `GET /api/conversation/{user_id}` - DB에서 대화 내역 조회

#### **메모리 조회**

- `GET /memory` - 모든 사용자 대화 내역 (TTOT 서버용)

---

## 💾 데이터베이스 구조

### UserDB 테이블 (SQLite)

| 컬럼                 | 타입        | 설명                      |
| -------------------- | ----------- | ------------------------- |
| `id`               | String (PK) | 사용자 ID                 |
| `uuid`             | Integer     | 고유 식별자               |
| `room_id`          | String      | 채팅방 ID                 |
| `input_text_list`  | JSON        | 사용자 입력 텍스트 리스트 |
| `output_text_list` | JSON        | AI 응답 텍스트 리스트     |
| `input_wav_list`   | JSON        | 입력 음성 파일 경로       |
| `atot_text_list`   | JSON        | 음성→텍스트 변환 결과    |
| `ttot_text_list`   | JSON        | AI 생성 텍스트            |
| `output_wav_list`  | JSON        | 출력 음성 파일 경로       |

---

## 🎨 주요 기능 설명

### 1. 🎤 음성 녹음 및 인식

**동작 방식:**

1. 녹음 버튼 클릭
2. 마이크 권한 획득 (HTTPS 필요)
3. AudioWorklet으로 실시간 PCM 데이터 수집
4. ATOT 서버로 청크 단위 전송
5. Silero VAD로 음성 구간 감지
6. Whisper로 음성→텍스트 변환
7. **자동 녹음 중지** (음성 인식 완료 시)
8. **30초 타임아웃** (자동 중지)

### 2. 🤖 AI 응답 생성

**TTOT 서버 기능:**

- LangChain 기반 대화 생성
- OpenAI GPT 모델 사용
- RAG (검색 증강 생성) 지원
- 대화 메모리 관리
- ChromaDB 벡터 검색

### 3. 🔊 음성 합성 (TTS)

**5가지 음성 모드:**

- Mode 0: `mb.wav` (기본)
- Mode 1: `swingpark.wav`
- Mode 2: `chulsoo.wav`
- Mode 3: `jaemay.mp3`
- Mode 4: `moon_short3.wav`

### 4. 💬 중복 입력 방지

**lockUI/unlockUI 시스템:**

- AI 응답 생성 중 입력 차단
- 로딩 인디케이터 표시 ("답변 생성 중...")
- 에러 발생 시 자동 잠금 해제
- 모든 작업 완료 후 UI 복구

### 5. 🎬 GIF 애니메이션

**캐릭터 애니메이션:**

- AI 음성 재생 중: `talk.gif` (말하는 애니메이션)
- 재생 완료/일시정지: `maicon.png` (정지 이미지)
- 자동 재생 및 클릭 제어

---

## 🔒 보안 및 인증

### HTTPS 설정

- ✅ 자체 서명 SSL 인증서 (개발용)
- ✅ 마이크 접근 권한 획득 가능
- ✅ 외부 기기 접속 허용 (0.0.0.0)
- ⚠️ 실제 배포 시 Let's Encrypt 사용 권장

### 사용자 인증

- `userdata.json`에서 사용자 정보 관리
- 로그인 시 DB에 자동 생성
- UUID 기반 사용자 식별

---

## 🌐 CORS 설정

### Frontend (front.py)

```python
origins = [
    "http://localhost:3000",
    "https://localhost:3000",
    "https://192.168.0.37:3000"
]
```

### Backend (back.py)

```python
allow_origins = [
    "http://localhost:8000",   # ATOT
    "http://localhost:5001",   # Backend
    "http://localhost:8002",   # TTOT
    "http://localhost:3000",   # Frontend
    "https://192.168.0.37:3000"
]
```

---

## 🎯 사용 시나리오

### 시나리오 1: 텍스트 채팅

```
1. 로그인 (username/password)
2. 홈 화면 → "채팅 시작" 버튼
3. 텍스트 입력 후 Enter
4. AI 텍스트 응답 + 음성 응답 재생
5. 대화 내역 DB 저장
```

### 시나리오 2: 음성 대화

```
1. 로그인
2. 채팅 화면 → 녹음 버튼 클릭 🎙️
3. 말하기 (예: "오늘 날씨 어때?")
4. 음성 인식 자동 완료 (녹음 자동 중지)
5. AI 텍스트 응답 + 음성 응답
6. 캐릭터 GIF 애니메이션 재생
7. 대화 내역 저장
```

---

## 📊 포트 정보

| 서버               | 포트 | 프로토콜 | 역할          |
| ------------------ | ---- | -------- | ------------- |
| **Frontend** | 3000 | HTTPS    | 웹 인터페이스 |
| **Backend**  | 5001 | HTTP     | 중앙 제어     |
| **ATOT**     | 8000 | HTTP     | 음성→텍스트  |
| **TTOT**     | 8002 | HTTP     | AI 대화 생성  |
| **TTS**      | 8004 | HTTP     | 텍스트→음성  |

---

## 🛠️ 주요 라이브러리

### Backend

- `fastapi` - 웹 프레임워크
- `uvicorn` - ASGI 서버
- `sqlalchemy` - ORM
- `httpx` - 비동기 HTTP 클라이언트

### AI/ML

- `langchain` - LLM 프레임워크
- `openai` - OpenAI API
- `chromadb` - 벡터 데이터베이스
- `torch` - PyTorch (Whisper)

### 음성 처리

- `silero-vad` - Voice Activity Detection
- `librosa` - 오디오 분석
- `soundfile` - 오디오 파일 처리
- `torchaudio` - 오디오 ML

---

## 🐛 문제 해결

### 1. 마이크 접근 오류

**문제:**

```
녹음을 시작할 수 없습니다: Cannot read properties of undefined (reading 'getUserMedia')
```

**해결:**

- ✅ HTTPS로 접속 (`https://192.168.0.37:3000`)
- ✅ Chrome 플래그 설정 (`chrome://flags/#unsafely-treat-insecure-origin-as-secure`)

### 2. 서버 연결 실패

**문제:**

```
❌ 판단 서버 /start 통신 에러
```

**해결:**

```bash
# ATOT 서버 실행 확인
cd atot/judgeTest
python main.py
```

### 3. TTS 생성 실패

**문제:**

```
⚠️ TTS 서버에서 빈 데이터를 받았습니다
```

**해결:**

- `get_tts.py`의 TTS 서버 URL 확인
- TTS 모델 파일 존재 확인

### 4. SSL 인증서 오류

**문제:**

```
[SSL: CERTIFICATE_VERIFY_FAILED]
```

**해결:**

- 브라우저에서 "고급" → "계속 진행" 클릭
- 또는 Let's Encrypt 정식 인증서 발급

---

## 📝 환경 변수 (선택사항)

`.env` 파일 생성:

```bash
OPENAI_API_KEY=sk-...
SSL_KEYFILE=./key.pem
SSL_CERTFILE=./cert.pem
```

---

## 🔗 관련 문서

- [ATOT README](atot/judgeTest/README.md) - 음성 인식 서버
- [TTOT README](ttot/README.md) - AI 대화 생성 서버
- [Frontend README](atot/audioTest/README.md) - 스트리밍 처리

---

## 🎓 기술 스택

**Frontend:**

- HTML5 / CSS3 / JavaScript (ES6+)
- WebAudio API
- AudioWorklet
- Fetch API

**Backend:**

- Python 3.10+
- FastAPI
- SQLAlchemy
- Pydantic

**AI/ML:**

- LangChain
- OpenAI GPT
- Whisper (OpenAI)
- Silero VAD

**Infrastructure:**

- HTTPS (SSL/TLS)
- SQLite
- ChromaDB

---

## 📄 라이센스

내부 프로젝트용

---

## 👥 개발자

- Frontend: `front.py` (382 lines)
- Backend: `back.py` (622 lines)
- JavaScript: `scripts.js` (700+ lines)

---

## 🎉 완성된 기능

- ✅ 음성 인식 (실시간 스트리밍)
- ✅ AI 대화 생성 (LangChain + OpenAI)
- ✅ 음성 합성 (5가지 모드)
- ✅ 텍스트 채팅
- ✅ 사용자 인증
- ✅ 대화 내역 관리
- ✅ 중복 입력 방지
- ✅ 음성 인식 후 자동 녹음 중지
- ✅ 30초 녹음 타임아웃
- ✅ GIF 애니메이션
- ✅ HTTPS 지원
- ✅ 외부 기기 접속
- ✅ 반응형 UI

---

**🚀 프로젝트 실행:**

```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. 인증서 생성 (최초 1회)
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 -subj "/CN=192.168.0.37"

# 3. 서버 실행 (4개 터미널)
python front.py          # 터미널 1
uvicorn back:app --port 5001           # 터미널 2
cd atot/judgeTest && uvicorn main:app --port 8000  # 터미널 3
cd ttot && uvicorn main:app --port 8002            # 터미널 4

# 4. 브라우저 접속
# https://192.168.0.37:3000
```
