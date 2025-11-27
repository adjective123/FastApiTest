"""
services.py - 비즈니스 로직 처리
RAG + Memory 통합 버전 (로컬 파일 메모리)
"""
from datetime import datetime
from typing import List, Dict, Optional

from langchain_core.documents import Document

from config import Config
from llm_manager import LLMManager
from rag_manager import RAGManager
from memory_manager import MemoryManager
from models import GenerateRequest, GenerateResponse


class ChatService:
    """채팅 관련 비즈니스 로직"""

    def __init__(
        self,
        llm_manager: LLMManager,
        rag_manager: RAGManager,
        memory_manager: MemoryManager
    ):
        self.llm_manager = llm_manager
        self.rag_manager = rag_manager
        self.memory_manager = memory_manager

    def generate_response(self, request: GenerateRequest) -> GenerateResponse:
        """사용자 요청에 대한 응답 생성"""
        print(f"\n[Service] 응답 생성 시작")
        print(f"  - 사용자: {request.user_id}")
        print(f"  - RAG: {request.use_rag}, Memory: {request.use_memory}")

        start_time = datetime.now()

        try:
            if request.use_rag:
                return self._generate_with_rag(request, start_time)
            else:
                return self._generate_without_rag(request, start_time)

        except Exception as e:
            error_msg = str(e)
            print(f"[Service] 오류 발생: {error_msg}")

            return GenerateResponse(
                success=False,
                response="죄송합니다. 일시적으로 응답을 생성할 수 없습니다.",
                user_id=request.user_id,
                error=error_msg
            )

    def _generate_with_rag(
        self,
        request: GenerateRequest,
        start_time: datetime
    ) -> GenerateResponse:
        """RAG를 사용한 응답 생성 (로컬 메모리 사용)"""
        print(f"[Service] RAG 모드 실행")

        if request.use_memory:
            print(f"[Service] RAG + 메모리 모드 (로컬 파일)")
            # 로컬 파일에서 대화 기록 불러오기
            memory = self.memory_manager.get_or_create_memory(request.user_id)
            chat_history = memory.load_memory_variables({}).get("chat_history", [])

            # RAG + 메모리 통합 응답 생성
            bot_response, source_docs = self.rag_manager.generate_with_rag_and_memory(
                request.text,
                chat_history
            )
        else:
            print(f"[Service] RAG 단독 모드")
            bot_response, source_docs = self.rag_manager.generate_with_rag(request.text)

        # 출처 문서 정보 포맷팅
        source_info = [
            f"[{i+1}] {doc.page_content[:100]}..."
            for i, doc in enumerate(source_docs)
        ]

        print(f"[Service] RAG 응답 완료 ({len(source_docs)}개 문서)")

        # 메모리 저장 (로컬 파일)
        if request.use_memory:
            self.memory_manager.save_context(
                request.user_id,
                request.text,
                bot_response
            )
            print(f"[Service] 대화 기록 저장 완료")

        return GenerateResponse(
            success=True,
            response=bot_response,
            user_id=request.user_id,
            rag_used=True,
            source_documents=source_info if source_docs else None
        )

    def _generate_without_rag(
        self,
        request: GenerateRequest,
        start_time: datetime
    ) -> GenerateResponse:
        """RAG 없이 일반 응답 생성 (로컬 메모리 사용)"""
        print(f"[Service] 일반 모드 실행")

        if request.use_memory:
            # 로컬 파일에서 대화 기록 불러오기
            memory = self.memory_manager.get_or_create_memory(request.user_id)
            chat_history = memory.load_memory_variables({}).get("chat_history", [])

            bot_response = self.llm_manager.generate_with_history(
                request.text,
                chat_history
            )

            # 메모리 저장
            self.memory_manager.save_context(
                request.user_id,
                request.text,
                bot_response
            )
        else:
            bot_response = self.llm_manager.generate(request.text)

        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        print(f"[Service] 일반 응답 완료 ({elapsed:.0f}ms)")

        return GenerateResponse(
            success=True,
            response=bot_response,
            user_id=request.user_id,
            rag_used=False
        )


class DocumentService:
    """문서 관련 비즈니스 로직"""

    def __init__(self, rag_manager: RAGManager):
        self.rag_manager = rag_manager

    def add_document(self, content: str, metadata: Optional[Dict] = None) -> Dict:
        """문서 추가"""
        print(f"[Service] 문서 추가 시작")

        result = self.rag_manager.add_document(content, metadata)

        if result["success"]:
            print(f"[Service] 문서 추가 완료: {result['chunks_created']}개 청크")
        else:
            print(f"[Service] 문서 추가 실패: {result.get('error')}")

        return result

    def add_document_from_file(self, filename: str, content: bytes) -> Dict:
        """파일에서 문서 추가"""
        print(f"[Service] 파일 업로드 시작: {filename}")

        try:
            text = content.decode('utf-8')

            result = self.rag_manager.add_document(
                text,
                {"source": filename, "timestamp": str(datetime.now())}
            )

            if result["success"]:
                return {
                    "success": True,
                    "filename": filename,
                    "chunks_created": result['chunks_created'],
                    "message": "파일이 성공적으로 추가되었습니다"
                }
            else:
                return {
                    "success": False,
                    "filename": filename,
                    "error": result.get("error")
                }

        except Exception as e:
            return {
                "success": False,
                "filename": filename,
                "error": str(e)
            }

    def search_documents(self, query: str, k: int = 3) -> Dict:
        """문서 검색"""
        print(f"[Service] 문서 검색: {query}")

        try:
            docs = self.rag_manager.search_documents(query, k)

            results = [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in docs
            ]

            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results)
            }

        except Exception as e:
            return {
                "success": False,
                "query": query,
                "error": str(e)
            }

    def get_document_count(self) -> int:
        """벡터 DB의 문서 수 조회"""
        return self.rag_manager.get_document_count()

    def clear_documents(self) -> bool:
        """벡터 DB 초기화"""
        print(f"[Service] 벡터 DB 초기화")
        return self.rag_manager.clear_documents()


class MemoryService:
    """메모리 관련 비즈니스 로직"""

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager

    def get_memory(self, user_id: str) -> Dict:
        """대화 메모리 조회"""
        info = self.memory_manager.get_memory_info(user_id)

        return {
            "user_id": info["user_id"],
            "conversation_count": info["conversation_count"],
            "history": info["history"]
        }

    def clear_memory(self, user_id: str) -> Dict:
        """대화 메모리 삭제"""
        success = self.memory_manager.clear_memory(user_id)

        if success:
            return {"message": f"{user_id}의 대화 기록이 삭제되었습니다"}
        else:
            return {"message": "대화 기록이 없습니다"}


class StatsService:
    """통계 관련 비즈니스 로직"""

    def __init__(
        self,
        memory_manager: MemoryManager,
        rag_manager: RAGManager
    ):
        self.memory_manager = memory_manager
        self.rag_manager = rag_manager

    def get_stats(self) -> Dict:
        """서버 통계 조회"""
        return {
            "active_users": self.memory_manager.get_active_users(),
            "total_conversations": self.memory_manager.get_total_conversations(),
            "documents_in_db": self.rag_manager.get_document_count(),
            "model": Config.LLM_MODEL,
            "embedding_model": Config.EMBEDDING_MODEL
        }

    def get_health(self) -> Dict:
        """헬스체크"""
        return {
            "status": "healthy",
            "service": "llm_server_modular",
            "model": Config.LLM_MODEL,
            "documents": self.rag_manager.get_document_count()
        }