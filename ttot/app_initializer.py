"""
app_initializer.py - 서버 초기화 로직
Manager와 Service 초기화를 담당합니다.
"""
from config import Config
from prompts import PromptManager
from llm_manager import LLMManager
from rag_manager import RAGManager
from memory_manager import MemoryManager
from services import ChatService, DocumentService, StatsService


class AppInitializer:
    """애플리케이션 초기화 클래스"""
    
    def __init__(self):
        """초기화"""
        print("=" * 60)
        print("RAG 기반 LLM 서버 초기화 시작")
        print("=" * 60)
        
        # 설정 초기화
        Config.initialize()
        
        # Manager 초기화
        self.prompt_manager = PromptManager(prompt_file=Config.SYSTEM_PROMPT_FILE)
        self.llm_manager = LLMManager(config=Config, prompt_manager=self.prompt_manager)
        self.rag_manager = RAGManager(
            config=Config,
            prompt_manager=self.prompt_manager,
            llm=self.llm_manager.llm
        )
        self.memory_manager = MemoryManager(config=Config)
        
        # Service 초기화
        self.chat_service = ChatService(
            self.llm_manager,
            self.rag_manager,
            self.memory_manager
        )
        self.document_service = DocumentService(self.rag_manager)
        self.stats_service = StatsService(self.rag_manager)
        
        print("=" * 60)
        print("모든 모듈 초기화 완료")
        print("=" * 60)
    
    def get_services(self):
        """서비스 객체들 반환"""
        return {
            'chat': self.chat_service,
            'document': self.document_service,
            'stats': self.stats_service
        }
    
    def print_startup_info(self):
        """서버 시작 정보 출력"""
        print("\n" + "=" * 60)
        print("RAG 기반 LLM 서버 시작")
        print("=" * 60)
        print(f"포트: {Config.SERVER_PORT}")
        print(f"LLM 모델: {Config.LLM_MODEL}")
        print(f"임베딩 모델: {Config.EMBEDDING_MODEL}")
        print(f"문서 수: {self.document_service.get_document_count()}")
        print(f"아키텍처: 모듈화 + 서비스 레이어 (라우터 서버 연동)")
        print("=" * 60)
