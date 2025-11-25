# 🔧 RAG/메모리 문제 해결 가이드

## 🎯 문제 요약

**증상:**
- `use_rag=False, use_memory=False` → ✅ 정상 작동
- `use_rag=True` 또는 `use_memory=True` → ❌ 오류 발생

**오류 메시지:**
```
HTTPSConnectionPool(host='openaipublic.blob.core.windows.net', port=443): 
Max retries exceeded with url: /encodings/cl100k_base.tiktoken
```

---

## 🔍 원인 분석

### 1. tiktoken이란?
- OpenAI의 토큰 계산 라이브러리
- 텍스트를 토큰으로 변환하는 인코딩 파일이 필요
- 최초 실행 시 인터넷에서 인코딩 파일 다운로드 시도

### 2. 왜 RAG/메모리에서만 문제가 발생하나?

| 기능 | tiktoken 필요 여부 | 이유 |
|------|-------------------|------|
| **단순 채팅** | ❌ 불필요 | OpenAI API만 호출 |
| **RAG (문서 검색)** | ✅ 필요 | 텍스트 분할 시 토큰 계산 |
| **메모리 (대화 기록)** | ✅ 필요 | 대화 저장 시 토큰 계산 |

### 3. 네트워크 환경 문제
- 현재 환경의 프록시가 `openaipublic.blob.core.windows.net` 접근 차단
- tiktoken 인코딩 파일 다운로드 불가능
- RAG와 메모리 기능 사용 불가

---

## ✅ 해결 방법

### 방법 1: 단순 채팅만 사용 (현재 작동 중) ✅

**설정:**
```python
{
    "text": "질문",
    "user_id": "user123",
    "use_rag": false,      # RAG 비활성화
    "use_memory": false    # 메모리 비활성화
}
```

**장점:**
- ✅ 현재 환경에서 정상 작동
- ✅ 빠른 응답 속도
- ✅ 네트워크 문제 없음

**단점:**
- ❌ 문서 검색 불가
- ❌ 대화 맥락 유지 안 됨
- ❌ 이전 대화 기억 안 함

**적합한 상황:**
- 간단한 질문-응답
- 일회성 대화
- 테스트 및 디버깅

---

### 방법 2: tiktoken 캐시 수동 설치

**절차:**

1. **다른 환경에서 tiktoken 캐시 다운로드**
   ```bash
   # 인터넷 연결이 가능한 PC에서
   python3 -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"
   ```

2. **캐시 디렉토리 찾기**
   ```bash
   # ~/.cache/tiktoken/ 또는 %USERPROFILE%\.cache\tiktoken\
   ls ~/.cache/tiktoken/
   ```

3. **캐시 파일 복사**
   ```bash
   # 캐시 파일을 현재 서버로 복사
   scp -r ~/.cache/tiktoken/ user@server:~/.cache/
   ```

4. **서버에서 확인**
   ```bash
   ls ~/.cache/tiktoken/
   # 9b5ad71b2ce5302211f9c61530b329a4922fc6a4 같은 파일이 있어야 함
   ```

5. **서버 재시작**
   ```bash
   python3 main.py
   ```

---

### 방법 3: 라우터 서버 측에서 기능 분리

**권장 접근:**

```python
# 라우터 서버 코드 예시

def call_llm_server(text, user_id, conversation_type):
    """LLM 서버 호출"""
    
    if conversation_type == "simple":
        # 간단한 질문 → RAG/메모리 없이
        payload = {
            "text": text,
            "user_id": user_id,
            "use_rag": False,
            "use_memory": False
        }
    
    elif conversation_type == "personal":
        # 개인 맞춤 대화 → 메모리만 사용 (RAG 불가)
        payload = {
            "text": text,
            "user_id": user_id,
            "use_rag": False,
            "use_memory": False  # 현재는 False로 (나중에 True)
        }
    
    elif conversation_type == "knowledge":
        # 지식 기반 응답 → RAG 사용 (현재 불가)
        payload = {
            "text": text,
            "user_id": user_id,
            "use_rag": False,  # 현재는 False로 (나중에 True)
            "use_memory": False
        }
    
    response = requests.post(
        "http://llm-server:8002/generate",
        json=payload
    )
    
    return response.json()
```

---

### 방법 4: 대체 임베딩 모델 사용 (고급)

**HuggingFace 모델로 변경 (tiktoken 불필요):**

```python
# rag_manager.py 수정
from langchain_community.embeddings import HuggingFaceEmbeddings

def _initialize_embeddings(self):
    """임베딩 모델 초기화 (HuggingFace 사용)"""
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={'device': 'cpu'}
    )
    return embeddings
```

**장점:**
- ✅ tiktoken 불필요
- ✅ 오프라인 작동 가능
- ✅ 무료

**단점:**
- ❌ OpenAI 임베딩보다 성능 떨어짐
- ❌ 모델 다운로드 필요 (최초 1회)
- ❌ 메모리 사용량 증가

---

## 🎯 현재 권장 사항

### 단기 해결책 (현재 사용)

**1. 단순 채팅만 사용**
```python
# client_test.py
payload = {
    "text": "질문",
    "user_id": "test_user",
    "use_rag": False,    # ← False로 설정
    "use_memory": False  # ← False로 설정
}
```

**장점:**
- ✅ 지금 당장 작동
- ✅ 수정 불필요
- ✅ 안정적

---

### 중기 해결책 (배포 환경)

**1. 운영 서버 배포 시**
- 운영 서버는 인터넷 접근 가능하도록 설정
- tiktoken 자동 다운로드 허용
- RAG/메모리 기능 정상 작동

**2. 네트워크 설정 변경**
```bash
# openaipublic.blob.core.windows.net 화이트리스트 추가
```

---

### 장기 해결책 (최적화)

**1. HuggingFace 임베딩으로 전환**
- 네트워크 의존성 제거
- 오프라인 작동 가능

**2. 자체 벡터 DB 구축**
- 사전에 문서 임베딩 완료
- 서버는 검색만 수행

---

## 📊 기능별 작동 상태

| 기능 | 현재 상태 | tiktoken 필요 | 대안 |
|------|----------|--------------|------|
| **단순 채팅** | ✅ 작동 | ❌ 불필요 | - |
| **문서 추가** | ❌ 불가 | ✅ 필요 | HuggingFace 임베딩 |
| **문서 검색** | ❌ 불가 | ✅ 필요 | HuggingFace 임베딩 |
| **RAG 채팅** | ❌ 불가 | ✅ 필요 | HuggingFace 임베딩 |
| **대화 메모리** | ❌ 불가 | ✅ 필요 | tiktoken 캐시 설치 |
| **헬스체크** | ✅ 작동 | ❌ 불필요 | - |
| **서버 통계** | ✅ 작동 | ❌ 불필요 | - |

---

## 🔧 테스트 방법

### ✅ 작동하는 테스트

```bash
# 1. 헬스체크
curl http://localhost:8002/health

# 2. 단순 채팅 (use_rag=false, use_memory=false)
curl -X POST http://localhost:8002/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "안녕하세요",
    "user_id": "test",
    "use_rag": false,
    "use_memory": false
  }'

# 3. 서버 통계
curl http://localhost:8002/stats

# 4. 설정 조회
curl http://localhost:8002/config
```

### ❌ 현재 불가능한 테스트

```bash
# 1. 문서 추가 (tiktoken 필요)
curl -X POST http://localhost:8002/documents/add \
  -H "Content-Type: application/json" \
  -d '{"content": "..."}'

# 2. RAG 채팅 (tiktoken 필요)
curl -X POST http://localhost:8002/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "질문",
    "use_rag": true  # ← 불가능
  }'

# 3. 메모리 포함 채팅 (tiktoken 필요)
curl -X POST http://localhost:8002/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "질문",
    "use_memory": true  # ← 불가능
  }'
```

---

## 💡 결론

**현재 상황:**
- ✅ LLM 서버는 정상 작동
- ✅ 기본 채팅 기능 완벽
- ❌ RAG/메모리는 네트워크 제한으로 불가

**단기 대응:**
- `use_rag=False, use_memory=False` 사용
- 단순 질문-응답 서비스 제공

**배포 시 해결:**
- 운영 서버에서는 자동 해결
- 인터넷 접근 가능한 환경이면 OK

**장기 개선:**
- HuggingFace 임베딩 도입 고려
- 네트워크 독립적인 구조로 개선

---

**마지막 업데이트:** 2024-11-12
**서버 버전:** 3.2.0
