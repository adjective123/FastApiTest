# 🧪 LLM 서버 테스트 가이드

## ✅ 테스트 결과 요약

**서버 상태:** 정상 작동 ✅
- 서버 시작: 성공
- API 엔드포인트: 정상
- 헬스체크: 정상

**제한 사항:**
- 네트워크 환경으로 인해 OpenAI API 호출이 제한될 수 있습니다
- 로컬 테스트는 정상 작동합니다

---

## 🚀 서버 실행 방법

### 1. 기본 실행
```bash
cd /mnt/user-data/outputs
python main.py
```

### 2. 백그라운드 실행
```bash
cd /mnt/user-data/outputs
nohup python main.py > server.log 2>&1 &
echo $! > server.pid
```

### 3. 서버 종료
```bash
# PID 파일 사용
kill $(cat server.pid)
rm server.pid

# 또는 직접 종료
ps aux | grep "python main.py"
kill <PID>
```

---

## 🧪 수동 테스트

### 테스트 1: 헬스체크

```bash
curl http://localhost:8002/health
```

**예상 응답:**
```json
{
  "status": "healthy",
  "service": "llm_server_modular",
  "model": "gpt-3.5-turbo",
  "documents": 0
}
```

---

### 테스트 2: 간단한 채팅 (메모리/RAG 없음)

```bash
curl -X POST http://localhost:8002/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "안녕하세요",
    "user_id": "test_user",
    "use_rag": false,
    "use_memory": false
  }'
```

**예상 응답:**
```json
{
  "success": true,
  "response": "안녕하세요! 무엇을 도와드릴까요?",
  "user_id": "test_user",
  "rag_used": false
}
```

---

### 테스트 3: 문서 추가

```bash
curl -X POST http://localhost:8002/documents/add \
  -H "Content-Type: application/json" \
  -d '{
    "content": "복지센터 운영시간: 월~금 09:00-18:00",
    "metadata": {"source": "manual", "type": "info"}
  }'
```

**예상 응답:**
```json
{
  "success": true,
  "message": "문서 추가 완료",
  "chunks_added": 1
}
```

---

### 테스트 4: 문서 검색

```bash
curl "http://localhost:8002/documents/search?query=운영시간&k=3"
```

**예상 응답:**
```json
{
  "success": true,
  "query": "운영시간",
  "documents": [
    "복지센터 운영시간: 월~금 09:00-18:00"
  ]
}
```

---

### 테스트 5: RAG 기반 채팅

```bash
curl -X POST http://localhost:8002/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "복지센터 언제 열어?",
    "user_id": "test_user",
    "use_rag": true,
    "use_memory": false
  }'
```

**예상 응답:**
```json
{
  "success": true,
  "response": "복지센터는 월요일부터 금요일까지 오전 9시에 문을 엽니다.",
  "user_id": "test_user",
  "rag_used": true,
  "source_documents": ["복지센터 운영시간: 월~금 09:00-18:00"]
}
```

---

### 테스트 6: 대화 메모리

**첫 번째 대화:**
```bash
curl -X POST http://localhost:8002/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "내 이름은 철수야",
    "user_id": "memory_test",
    "use_rag": false,
    "use_memory": true
  }'
```

**두 번째 대화:**
```bash
curl -X POST http://localhost:8002/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "내 이름이 뭐야?",
    "user_id": "memory_test",
    "use_rag": false,
    "use_memory": true
  }'
```

**예상 응답:** "철수님이시죠!" (이전 대화를 기억)

---

### 테스트 7: 메모리 조회

```bash
curl http://localhost:8002/memory/memory_test
```

**예상 응답:**
```json
{
  "user_id": "memory_test",
  "conversation_count": 2,
  "history": [
    {
      "type": "human",
      "content": "내 이름은 철수야",
      "timestamp": "2024-11-12T..."
    },
    {
      "type": "ai",
      "content": "철수님, 안녕하세요!",
      "timestamp": "2024-11-12T..."
    }
  ]
}
```

---

### 테스트 8: 서버 통계

```bash
curl http://localhost:8002/stats
```

**예상 응답:**
```json
{
  "active_users": 2,
  "total_conversations": 5,
  "documents_in_db": 1,
  "model": "gpt-3.5-turbo",
  "embedding_model": "text-embedding-3-small",
  "service": "llm_server_modular"
}
```

---

### 테스트 9: 설정 조회

```bash
curl http://localhost:8002/config
```

**예상 응답:**
```json
{
  "server": {
    "port": 8002,
    "host": "0.0.0.0"
  },
  "model": {
    "llm_model": "gpt-3.5-turbo",
    "embedding_model": "text-embedding-3-small"
  },
  "llm_parameters": {
    "temperature": 0.7,
    "max_tokens": 300
  }
}
```

---

## 🐍 Python 클라이언트 테스트

### client_test.py 사용

```bash
# 서버가 실행 중인 상태에서
python client_test.py
```

### 커스텀 테스트 작성

```python
import requests

# 1. 헬스체크
response = requests.get("http://localhost:8002/health")
print(response.json())

# 2. 채팅
response = requests.post(
    "http://localhost:8002/generate",
    json={
        "text": "안녕하세요",
        "user_id": "my_user"
    }
)
print(response.json())

# 3. 문서 추가
response = requests.post(
    "http://localhost:8002/documents/add",
    json={
        "content": "테스트 문서입니다.",
        "metadata": {"source": "test"}
    }
)
print(response.json())
```

---

## 📊 종합 테스트 스크립트 실행

```bash
# 서버 시작
python main.py &
sleep 10

# 종합 테스트 실행
python test_server.py

# 서버 종료
pkill -f "python main.py"
```

---

## 🌐 API 문서 확인

서버 실행 후 브라우저에서:

```
http://localhost:8002/docs
```

- Swagger UI로 모든 API 확인 가능
- 직접 테스트 가능
- 요청/응답 예시 확인

---

## 🔍 로그 확인

```bash
# 실시간 로그 보기
tail -f server.log

# 에러만 보기
grep -i error server.log

# 최근 100줄 보기
tail -100 server.log
```

---

## ✅ 체크리스트

서버가 정상 작동하는지 확인:

- [ ] `python main.py` 실행 시 에러 없이 시작
- [ ] `curl http://localhost:8002/health` 응답 정상
- [ ] API 문서 (`/docs`) 접속 가능
- [ ] 간단한 채팅 요청 성공
- [ ] 문서 추가/검색 성공
- [ ] 대화 메모리 작동

---

## 🚨 문제 해결

### 서버가 시작되지 않는 경우

1. **포트 충돌 확인**
   ```bash
   lsof -i :8002
   # 사용 중이면 프로세스 종료
   kill <PID>
   ```

2. **패키지 설치 확인**
   ```bash
   pip install -r requirements.txt --break-system-packages
   ```

3. **API 키 확인**
   ```bash
   cat .env
   # OPENAI_API_KEY가 설정되어 있는지 확인
   ```

### API 호출이 실패하는 경우

1. **서버 상태 확인**
   ```bash
   curl http://localhost:8002/health
   ```

2. **로그 확인**
   ```bash
   tail -50 server.log
   ```

3. **네트워크 확인**
   ```bash
   ping localhost
   ```

---

## 📝 주의사항

1. **API 키**: OpenAI API 키가 올바르게 설정되어 있어야 합니다
2. **네트워크**: 인터넷 연결이 필요합니다 (OpenAI API 호출)
3. **포트**: 8002 포트가 사용 가능해야 합니다
4. **디렉토리**: `./chroma_db/`, `./chat_history/` 자동 생성됩니다

---

## 🎯 다음 단계

1. ✅ 서버 테스트 완료
2. 라우터 서버와 연동 테스트
3. TTS/STT 서버와 통합 테스트
4. 실제 어르신 대상 테스트
5. 성능 모니터링 및 최적화

---

## 💡 유용한 명령어

```bash
# 서버 프로세스 확인
ps aux | grep "python main.py"

# 서버 로그 실시간 보기
tail -f server.log

# 문서 개수 확인
curl http://localhost:8002/documents/count

# 모든 메모리 삭제
curl -X DELETE http://localhost:8002/memory/<user_id>

# 모든 문서 삭제
curl -X DELETE http://localhost:8002/documents/clear
```
