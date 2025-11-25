# RAG 기반 어르신 말동무 챗봇 서버 🤖👵

어르신들을 위한 따뜻하고 친근한 말동무 챗봇 서버입니다.  
RAG (Retrieval-Augmented Generation)와 대화 메모리 기능을 갖춘 모듈화된 LLM 서버입니다.

## 📋 주요 기능

- ✅ **RAG (문서 검색 기반 응답)**: 벡터 DB를 활용한 정확한 정보 제공
- 💬 **대화 메모리**: 사용자별 대화 기록 저장 및 컨텍스트 유지 (최근 15개 대화)
- 🤖 **GPT-4o-mini**: 빠르고 경제적인 최신 모델 사용
- 👵 **어르신 특화**: 친근하고 이해하기 쉬운 대화 스타일
- 📚 **문서 관리**: 동적 문서 추가/검색/삭제
- 🔧 **모듈화 설계**: 각 기능이 독립적인 모듈로 분리
- 📝 **JSON 기반 설정**: 외부 서버와의 원활한 소통
- 🌐 **RESTful API**: FastAPI 기반의 깔끔한 API

## 🏗️ 프로젝트 구조

```
프로젝트/
├── config.py              # 설정 관리 (JSON 로드)
├── config.json            # ⭐ 서버 설정 (JSON 형식)
├── services.py            # ⭐ 비즈니스 로직 (내부 처리)
├── main.py                # ⭐ API 엔드포인트 (외부 통신)
├── prompts.py             # 시스템 프롬프트 관리
├── llm_manager.py         # LLM 모델 관리
├── rag_manager.py         # RAG 관리
├── memory_manager.py      # 대화 메모리 관리
├── models.py              # API 모델 정의
├── app_initializer.py     # 서버 초기화
├── client_test.py         # 테스트 클라이언트
├── .env                   # 환경 변수 (API 키)  # github 업로드 XX
├── system_prompt.json     # ⭐ 시스템 프롬프트 설정 (어르신 특화)
└── requirements.txt       # 의존성 패키지
```

### ⭐ 아키텍처

```
┌─────────────────────────────────────┐
│  main.py (API 엔드포인트)            │ ← 외부 서버와 통신
├─────────────────────────────────────┤
│  services.py (비즈니스 로직)         │ ← 내부 처리
├─────────────────────────────────────┤
│  Managers (llm, rag, memory 등)     │ ← 핵심 기능
├─────────────────────────────────────┤
│  config.json + .env (설정)          │ ← 설정 관리
└─────────────────────────────────────┘
```

## ⚙️ 설치 및 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 OpenAI API 키를 입력합니다:

```env
# OpenAI API Key
OPENAI_API_KEY=your-actual-api-key-here
```

### 3. 설정 파일 확인

`config.json` 파일에서 서버 설정을 확인합니다:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8002
  },
  "model": {
    "llm_model": "gpt-4o-mini",
    "embedding_model": "text-embedding-3-small"
  },
  "memory": {
    "k": 15
  }
}
```

### 4. 서버 실행

```bash
python main.py
```

서버가 `http://localhost:8002`에서 실행됩니다.

## 🚀 사용 방법

### API 엔드포인트

#### 1. 대화 생성
```bash
POST /generate
```

**요청 예시:**
```python
import requests

response = requests.post("http://localhost:8002/generate", json={
    "text": "안녕하세요",
    "user_id": "user123",
    "use_rag": True,
    "use_memory": True
})

print(response.json())
```

#### 2. 문서 추가
```bash
POST /documents/add
```

#### 3. 대화 기록 조회
```bash
GET /memory/{user_id}
```

#### 4. 서버 통계
```bash
GET /stats
```

#### 5. 헬스체크
```bash
GET /health
```

### 테스트 클라이언트 실행

```bash
python client_test.py
```

## 📝 설정 파일 (config.json)

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8002,
    "title": "RAG-based LLM Server",
    "description": "모듈화된 RAG 기반 LLM 서버",
    "version": "3.3.0"
  },
  "model": {
    "llm_model": "gpt-4o-mini",
    "embedding_model": "text-embedding-3-small"
  },
  "llm_parameters": {
    "temperature": 0.7,
    "max_tokens": 300
  },
  "paths": {
    "chroma_persist_dir": "./chroma_db",
    "memory_dir": "./chat_history",
    "system_prompt_file": "./system_prompt.json"
  },
  "memory": {
    "k": 15,
    "description": "최근 15개 대화만 기억"
  },
  "rag": {
    "chunk_size": 500,
    "chunk_overlap": 50,
    "retriever_k": 3,
    "description": "검색 시 상위 3개 문서 반환"
  }
}
```

## 🎯 시스템 프롬프트 특징

어르신 대화에 최적화된 프롬프트 (`system_prompt.json`):

### 핵심 특징:
- ✅ **적극적 대화**: "오늘 뭐 하셨어요?", "잘 주무셨어요?" 먼저 질문
- ✅ **간단한 질문**: 한 번에 하나씩, 네/아니오로 답할 수 있게
- ✅ **칭찬과 격려**: "잘하셨어요", "대단하세요" 자주 사용
- ✅ **쉬운 언어**: 구체적이고 익숙한 단어 (TV, 밥, 산책 등)
- ✅ **경청과 요약**: 어르신 말씀을 듣고 이해한 내용 피드백
- ✅ **긍정적 태도**: 항상 따뜻하고 공감하는 톤
- ✅ **한국 문화 이해**: "진지 드셨어요?", 명절, 효도 등

### 피하는 것:
- ❌ "궁금한 점 말씀해주세요" (수동적)
- ❌ 복잡한 선택지 제시
- ❌ 어려운 전문용어
- ❌ 한 번에 여러 질문

`system_prompt.json` 파일에서 수정 가능합니다.

## 💰 예상 비용 (GPT-4o-mini)

**10명이 각각 10번 대화 (총 100대화):**
- 입력: ~275,000 토큰
- 출력: ~30,000 토큰
- **총 비용: 약 $0.06 (80원)**

매우 경제적입니다! 🎉

**모델별 비교:**
| 모델 | 100대화 비용 | 속도 |
|------|-------------|------|
| GPT-3.5-turbo | ~200원 | 빠름 |
| GPT-4o-mini | ~80원 | 더 빠름 ⚡ |

## 🔒 보안 주의사항

- ⚠️ **`.env` 파일을 절대 Git에 커밋하지 마세요!**
- ⚠️ **API 키를 코드에 직접 작성하지 마세요!**
- ✅ `.gitignore`에 다음 항목이 포함되어 있는지 확인:
  ```
  .env
  *.pyc
  __pycache__/
  venv/
  chroma_db/
  chat_history/
  ```

## 🔄 변경 이력

### v3.3.0 (2024-11-18)
- 🤖 **모델 변경**: gpt-3.5-turbo → gpt-4o-mini (더 빠르고 경제적)
- 💬 **시스템 프롬프트 대폭 개선** (어르신 대화 특화)
  - 적극적 대화 유도 ("오늘 뭐 하셨어요?")
  - 칭찬과 격려 강화
  - 한 번에 하나씩 질문
  - 경청과 피드백 추가
  - 쉬운 언어와 구체적 사물 사용
- 📝 **대화 메모리 증가**: 5개 → 15개
- ⚡ 성능 최적화 및 비용 절감 (200원 → 80원)

### v3.2.0 (2024-11-11)
- ✨ JSON 기반 설정으로 변경 (`config.json`)
- ✨ 비즈니스 로직을 `services.py`로 분리
- ✨ API 엔드포인트와 내부 로직 명확히 분리
- ✨ 서버 설정 조회 API 추가 (`GET /config`)
- 🔧 CORS 설정을 JSON으로 관리

### v3.1.0
- 환경변수 기반 설정 (`.env`)
- 모듈화된 구조

## 🐛 문제 해결

### config.json 오류
```
FileNotFoundError: config.json 파일을 찾을 수 없습니다!
```
→ 프로젝트 루트에 `config.json` 파일이 있는지 확인하세요.

### API 키 오류
```
ValueError: OPENAI_API_KEY가 설정되지 않았습니다!
```
→ `.env` 파일에 올바른 API 키를 설정했는지 확인하세요.

### 포트 충돌
```
OSError: [Errno 48] Address already in use
```
→ `config.json`에서 `server.port`를 다른 번호로 변경하세요.

### 시스템 프롬프트 변경이 반영 안 됨
→ `system_prompt.json` 파일 저장 후 **서버를 재시작**해야 합니다.

## 🚀 향후 계획

- [ ] 스트리밍 응답 지원 (TTS 연동 최적화)
- [ ] 실시간 정보 조회 (날씨 API 등)
- [ ] 음성 인식 통합
- [ ] 대화 분석 대시보드

## 📄 라이선스

이 프로젝트는 개인/교육 목적으로 자유롭게 사용 가능합니다.

## 👥 기여

버그 리포트나 기능 제안은 환영합니다!

---

**Made with ❤️ for 어르신들**
