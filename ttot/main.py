"""
main.py - RAG 기반 LLM 서버 (API 엔드포인트)
로컬 파일 기반 메모리 버전
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from models import (
    GenerateRequest,
    GenerateResponse,
    AddDocumentRequest,
    MemoryResponse,
    StatsResponse,
    HealthResponse
)
from app_initializer import AppInitializer


# ============================================
# [서버 초기화]
# ============================================

initializer = AppInitializer()
services = initializer.get_services()

chat_service = services['chat']
document_service = services['document']
memory_service = services['memory']
stats_service = services['stats']


# ============================================
# [FastAPI 앱 생성]
# ============================================

app = FastAPI(
    title=Config.SERVER_TITLE,
    description=Config.SERVER_DESCRIPTION,
    version=Config.SERVER_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=Config.CORS_CREDENTIALS,
    allow_methods=Config.CORS_METHODS,
    allow_headers=Config.CORS_HEADERS,
)


# ============================================
# [API 엔드포인트 - 채팅]
# ============================================

@app.post("/generate", response_model=GenerateResponse)
async def generate_response(request: GenerateRequest):
    """채팅 응답 생성 (POST 방식)"""
    return chat_service.generate_response(request)


@app.get("/generate", response_model=GenerateResponse)
async def generate_response_get(
    text: str = None,
    user_id: str = "anonymous",
    use_rag: bool = True,
    use_memory: bool = True
):
    """채팅 응답 생성 (GET 방식)"""
    if not text:
        return GenerateResponse(
            success=False,
            response="text 파라미터가 필요합니다",
            user_id=user_id,
            error="missing text parameter"
        )

    request = GenerateRequest(
        text=text,
        user_id=user_id,
        use_rag=use_rag,
        use_memory=use_memory
    )
    return chat_service.generate_response(request)


# ============================================
# [API 엔드포인트 - 문서 관리]
# ============================================

@app.post("/documents/add")
async def add_document(request: AddDocumentRequest):
    """벡터 DB에 문서 추가"""
    result = document_service.add_document(request.content, request.metadata)

    if result["success"]:
        return {
            "success": True,
            "message": f"{result['chunks_created']}개의 청크로 분할되어 추가되었습니다",
            "chunks_created": result['chunks_created']
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error"))


@app.post("/documents/add-file")
async def add_document_from_file(file: UploadFile = File(...)):
    """파일에서 문서 추가"""
    content = await file.read()
    result = document_service.add_document_from_file(file.filename, content)

    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result.get("error"))


@app.get("/documents/search")
async def search_documents(query: str, k: int = 3):
    """벡터 DB에서 문서 검색"""
    result = document_service.search_documents(query, k)

    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result.get("error"))


@app.get("/documents/count")
async def get_document_count():
    """벡터 DB의 문서 수 조회"""
    count = document_service.get_document_count()
    return {
        "success": True,
        "count": count,
        "collection_name": "elderly_knowledge"
    }


@app.delete("/documents/clear")
async def clear_documents():
    """벡터 DB 초기화"""
    success = document_service.clear_documents()

    if success:
        return {"success": True, "message": "벡터 DB가 초기화되었습니다"}
    else:
        raise HTTPException(status_code=500, detail="초기화 실패")


# ============================================
# [API 엔드포인트 - 메모리 관리]
# ============================================

@app.get("/memory/{user_id}", response_model=MemoryResponse)
async def get_memory(user_id: str):
    """대화 메모리 조회"""
    result = memory_service.get_memory(user_id)

    return MemoryResponse(
        user_id=result["user_id"],
        conversation_count=result["conversation_count"],
        history=result["history"]
    )


@app.delete("/memory/{user_id}")
async def clear_memory(user_id: str):
    """대화 메모리 삭제"""
    return memory_service.clear_memory(user_id)


# ============================================
# [API 엔드포인트 - 시스템 정보]
# ============================================

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """서버 통계 조회"""
    result = stats_service.get_stats()

    return StatsResponse(
        active_users=result["active_users"],
        total_conversations=result["total_conversations"],
        documents_in_db=result["documents_in_db"],
        model=result["model"],
        embedding_model=result["embedding_model"]
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스체크"""
    result = stats_service.get_health()

    return HealthResponse(
        status=result["status"],
        service=result["service"],
        model=result["model"],
        documents=result["documents"]
    )


@app.get("/config")
async def get_config():
    """현재 서버 설정 조회"""
    return Config.get_config_dict()


@app.get("/")
async def root():
    """루트 엔드포인트 - API 정보"""
    return {
        "service": Config.SERVER_TITLE,
        "version": Config.SERVER_VERSION,
        "description": Config.SERVER_DESCRIPTION,
        "model": Config.LLM_MODEL,
        "memory_storage": "local_file",
        "features": [
            "RAG (문서 기반 검색)",
            "Memory (로컬 파일 기반 대화 기록)",
            "Document Management (문서 추가/검색/삭제)"
        ],
        "endpoints": {
            "chat": {"generate": "POST/GET /generate"},
            "documents": {
                "add": "POST /documents/add",
                "search": "GET /documents/search",
                "count": "GET /documents/count",
                "clear": "DELETE /documents/clear"
            },
            "memory": {
                "get": "GET /memory/{user_id}",
                "clear": "DELETE /memory/{user_id}"
            },
            "system": {
                "stats": "GET /stats",
                "health": "GET /health",
                "config": "GET /config"
            }
        }
    }


# ============================================
# [서버 실행]
# ============================================

if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*50)
    print("🚀 LLM 서버를 시작합니다...")
    print("="*50 + "\n")

    initializer.print_startup_info()

    print("\n" + "="*50)
    print(f"✅ 서버: http://{Config.SERVER_HOST}:{Config.SERVER_PORT}")
    print(f"📚 API 문서: http://{Config.SERVER_HOST}:{Config.SERVER_PORT}/docs")
    print("="*50 + "\n")
    
    uvicorn.run(
        app,
        host=Config.SERVER_HOST,
        port=Config.SERVER_PORT,
        log_level="info"
    )