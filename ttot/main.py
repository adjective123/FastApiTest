# main.py - TTOT Server
# !uvicorn ttot.main:app --port 8002

"""
main.py - RAG 기반 LLM 서버 (API 엔드포인트)
외부 서버와 통신하는 API 엔드포인트만 정의합니다.
비즈니스 로직은 services.py에 구현되어 있습니다.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx

from config import Config
from models import (
    GenerateRequest,
    GenerateResponse,
    AddDocumentRequest,
    HealthResponse
)
from app_initializer import AppInitializer


# ============================================
# [서버 초기화]
# ============================================

# 모든 초기화 로직은 AppInitializer에서 처리
initializer = AppInitializer()
services = initializer.get_services()

# 서비스 객체들
chat_service = services['chat']
document_service = services['document']
stats_service = services['stats']


# ============================================
# [FastAPI 앱 생성]
# ============================================

app = FastAPI(
    title=Config.SERVER_TITLE,
    description=Config.SERVER_DESCRIPTION,
    version=Config.SERVER_VERSION
)

# CORS 설정
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
    """
    채팅 응답 생성 (외부 호출용)
    
    Args:
        request: 생성 요청
    
    Returns:
        GenerateResponse: AI 응답
    """
    return await chat_service.generate_response(request)

@app.get("/generate")  # response_model 제거
async def get_generate_response():
    try:
        async with httpx.AsyncClient() as client:
            atot_response = await client.get("http://127.0.0.1:5000/atot")
            atot_response.raise_for_status()
            
            atot_data = atot_response.json()
            
            user_id = atot_data.get("user_id")
            atot_text = atot_data.get("atot_text")
            
            # None 체크 추가
            if not atot_text:
                raise HTTPException(status_code=400, detail="atot_text가 비어있습니다. ATOT 서버에서 먼저 POST /run-model을 실행하세요.")
            
            gen_req = GenerateRequest(
                text=str(atot_text),
                user_id=str(user_id),
                use_rag=False,
                use_memory=True,
                temperature=0,
                max_tokens=0
            )
            
            response = chat_service.generate_response(gen_req)
            
            # GenerateResponse 객체를 그대로 반환
            return response
            
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Backend 서버 연결 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알 수 없는 오류: {str(e)}")

# ============================================
# [API 엔드포인트 - 문서 관리]
# ============================================

@app.post("/documents/add")
async def add_document(request: AddDocumentRequest):
    """
    벡터 DB에 문서 추가 (외부 호출용)
    
    Args:
        request: 문서 추가 요청
    
    Returns:
        Dict: 추가 결과
    """
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
    """
    파일에서 문서 추가 (외부 호출용)
    
    Args:
        file: 업로드된 파일
    
    Returns:
        Dict: 추가 결과
    """
    content = await file.read()
    result = document_service.add_document_from_file(file.filename, content)
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result.get("error"))


@app.get("/documents/search")
async def search_documents(query: str, k: int = 3):
    """
    벡터 DB에서 문서 검색 (외부 호출용)
    
    Args:
        query: 검색 쿼리
        k: 검색할 문서 수
    
    Returns:
        Dict: 검색 결과
    """
    result = document_service.search_documents(query, k)
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result.get("error"))


@app.get("/documents/count")
async def get_document_count():
    """
    벡터 DB의 문서 수 조회 (외부 호출용)
    
    Returns:
        Dict: 문서 수 정보
    """
    count = document_service.get_document_count()
    return {
        "success": True,
        "count": count,
        "collection_name": "elderly_knowledge"
    }


@app.delete("/documents/clear")
async def clear_documents():
    """
    벡터 DB 초기화 (외부 호출용)
    
    Returns:
        Dict: 초기화 결과
    """
    success = document_service.clear_documents()
    
    if success:
        return {
            "success": True,
            "message": "벡터 DB가 초기화되었습니다"
        }
    else:
        raise HTTPException(status_code=500, detail="초기화 실패")


# ============================================
# [API 엔드포인트 - 시스템 정보]
# ============================================

@app.get("/stats")
async def get_stats():
    """
    서버 통계 조회 (외부 호출용)
    
    Returns:
        Dict: 서버 통계
    """
    return stats_service.get_stats()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    헬스체크 (외부 호출용)
    
    Returns:
        HealthResponse: 서버 상태
    """
    result = stats_service.get_health()
    
    return HealthResponse(
        status=result["status"],
        service=result["service"],
        model=result["model"],
        documents=result["documents"]
    )


@app.get("/config")
async def get_config():
    """
    현재 서버 설정 조회 (외부 호출용)
    
    Returns:
        Dict: 서버 설정 정보
    """
    return Config.get_config_dict()


@app.get("/")
async def root():
    """
    루트 엔드포인트 - API 정보 (외부 호출용)
    
    Returns:
        Dict: 서버 정보 및 엔드포인트 목록
    """
    return {
        "service": Config.SERVER_TITLE,
        "version": Config.SERVER_VERSION,
        "description": Config.SERVER_DESCRIPTION,
        "model": Config.LLM_MODEL,
        "features": [
            "RAG (문서 기반 검색)",
            "Memory (라우터 서버 연동)",
            "Document Management (문서 추가/검색/삭제)",
            "Modular Architecture (모듈화 구조)",
            "JSON Configuration (JSON 기반 설정)"
        ],
        "endpoints": {
            "chat": {
                "generate": "POST /generate - 채팅 응답 생성"
            },
            "documents": {
                "add": "POST /documents/add - 문서 추가",
                "add_file": "POST /documents/add-file - 파일에서 문서 추가",
                "search": "GET /documents/search - 문서 검색",
                "count": "GET /documents/count - 문서 수 조회",
                "clear": "DELETE /documents/clear - 문서 DB 초기화"
            },
            "system": {
                "stats": "GET /stats - 서버 통계",
                "health": "GET /health - 헬스체크",
                "config": "GET /config - 설정 정보"
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
    
    # 서버 시작 정보 출력
    initializer.print_startup_info()
    
    print("\n" + "="*50)
    print(f"✅ 서버가 http://{Config.SERVER_HOST}:{Config.SERVER_PORT} 에서 실행 중입니다")
    print(f"📚 API 문서: http://{Config.SERVER_HOST}:{Config.SERVER_PORT}/docs")
    print("="*50 + "\n")
    
    uvicorn.run(
        app,
        host=Config.SERVER_HOST,
        port=Config.SERVER_PORT,
        log_level="info"
    )