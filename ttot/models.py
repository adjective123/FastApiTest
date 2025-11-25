"""
models.py - API 요청/응답 모델 정의
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class GenerateRequest(BaseModel):
    """LLM 생성 요청 모델"""
    text: str = Field(..., description="사용자 입력 텍스트")
    user_id: str = Field(default="anonymous", description="사용자 ID")
    use_rag: bool = Field(default=True, description="RAG 사용 여부")
    use_memory: bool = Field(default=True, description="대화 메모리 사용 여부")
    temperature: Optional[float] = Field(default=None, description="생성 온도")
    max_tokens: Optional[int] = Field(default=None, description="최대 토큰 수")


class GenerateResponse(BaseModel):
    """LLM 생성 응답 모델"""
    success: bool = Field(..., description="성공 여부")
    response: str = Field(..., description="AI 응답")
    source: str = Field(default="llm", description="응답 소스")
    user_id: str = Field(..., description="사용자 ID")
    rag_used: bool = Field(default=False, description="RAG 사용 여부")
    source_documents: Optional[List[str]] = Field(default=None, description="출처 문서")
    tokens_used: Optional[int] = Field(default=None, description="사용된 토큰 수")
    error: Optional[str] = Field(default=None, description="에러 메시지")


class AddDocumentRequest(BaseModel):
    """문서 추가 요청 모델"""
    content: str = Field(..., description="문서 내용")
    metadata: Optional[Dict] = Field(default=None, description="문서 메타데이터")


class DocumentSearchRequest(BaseModel):
    """문서 검색 요청 모델"""
    query: str = Field(..., description="검색 쿼리")
    k: int = Field(default=3, description="검색할 문서 수")


class StatsResponse(BaseModel):
    """서버 통계 응답 모델"""
    documents_in_db: int = Field(..., description="벡터 DB 문서 수")
    model: str = Field(..., description="사용 중인 LLM 모델")
    embedding_model: str = Field(..., description="사용 중인 임베딩 모델")


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str = Field(..., description="서버 상태")
    service: str = Field(..., description="서비스 이름")
    model: str = Field(..., description="LLM 모델")
    documents: int = Field(..., description="벡터 DB 문서 수")
