"""
memory_manager.py - 대화 메모리 관리
라우터 서버에서 대화 기록 가져오기
"""
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from typing import Dict, List
import httpx

from config import Config


class SimpleMemory:
    """간단한 대화 메모리 구현"""

    def __init__(self, k: int = 5):
        """
        Args:
            k: 유지할 최근 대화 개수
        """
        self.k = k
        self.messages: List[BaseMessage] = []

    def add_message(self, message: BaseMessage):
        """메시지 추가"""
        self.messages.append(message)
        # 최근 k개 대화만 유지 (Human + AI 쌍)
        if len(self.messages) > self.k * 2:
            self.messages = self.messages[-(self.k * 2):]

    def add_user_message(self, text: str):
        """사용자 메시지 추가"""
        self.add_message(HumanMessage(content=text))

    def add_ai_message(self, text: str):
        """AI 메시지 추가"""
        self.add_message(AIMessage(content=text))

    def get_messages(self) -> List[BaseMessage]:
        """모든 메시지 반환"""
        return self.messages

    def clear(self):
        """메모리 초기화"""
        self.messages = []

    def load_memory_variables(self, inputs: dict) -> dict:
        """LangChain 호환성을 위한 메서드"""
        return {"chat_history": self.messages}


class MemoryManager:
    """대화 메모리 관리 클래스 - 라우터 서버 연동"""

    def __init__(self, config: Config = None, router_url: str = "http://127.0.0.1:5000"):
        """
        Args:
            config: 설정 객체
            router_url: 라우터 서버 URL
        """
        self.config = config or Config
        self.router_url = router_url
        self.memory_store: Dict[str, SimpleMemory] = {}

        print(f"[MemoryManager] 메모리 관리자 초기화 완료 (라우터 서버: {router_url})")

    def _create_memory(self) -> SimpleMemory:
        """새 메모리 생성"""
        return SimpleMemory(k=self.config.MEMORY_K)

    async def load_chat_history_from_router(self, user_id: str) -> List[Dict]:
        """
        라우터 서버에서 대화 기록 가져오기

        Args:
            user_id: 사용자 ID

        Returns:
            List[Dict]: 대화 기록
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.router_url}/chat-history/{user_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"[MemoryManager] 라우터에서 대화 기록 로드: {user_id} ({len(data)}개)")
                    return data
                else:
                    print(f"[MemoryManager] 대화 기록 없음: {user_id}")
                    return []
                    
        except Exception as e:
            print(f"[MemoryManager] 라우터 연결 실패: {e}")
            return []

    def get_or_create_memory(self, user_id: str, chat_history: List[Dict] = None) -> SimpleMemory:
        """
        사용자 메모리 가져오기 또는 생성

        Args:
            user_id: 사용자 ID
            chat_history: 라우터에서 가져온 대화 기록

        Returns:
            SimpleMemory: 사용자 메모리
        """
        # 메모리 저장소에 있으면 반환
        if user_id in self.memory_store:
            return self.memory_store[user_id]

        # 새로 생성
        memory = self._create_memory()
        
        # 대화 기록이 있으면 복원
        if chat_history:
            for item in chat_history:
                if item.get("role") == "user":
                    memory.add_user_message(item.get("content", ""))
                elif item.get("role") == "assistant":
                    memory.add_ai_message(item.get("content", ""))
        
        self.memory_store[user_id] = memory
        return memorys