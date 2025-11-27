"""
memory_manager.py - 대화 메모리 관리
로컬 파일(chat_history 폴더) 기반 버전
"""
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from typing import Dict, List
import json
import os
from datetime import datetime

from config import Config


class SimpleMemory:
    """간단한 대화 메모리 구현"""

    def __init__(self, k: int = 15):
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
    """대화 메모리 관리 클래스 - 로컬 파일 기반"""

    def __init__(self, config: Config = None):
        """
        Args:
            config: 설정 객체
        """
        self.config = config or Config
        self.memory_store: Dict[str, SimpleMemory] = {}

        # 메모리 디렉토리 생성
        os.makedirs(self.config.MEMORY_DIR, exist_ok=True)

        print(f"[MemoryManager] 메모리 관리자 초기화 완료 (저장 경로: {self.config.MEMORY_DIR})")

    def _create_memory(self) -> SimpleMemory:
        """새 메모리 생성"""
        return SimpleMemory(k=self.config.MEMORY_K)

    def get_or_create_memory(self, user_id: str) -> SimpleMemory:
        """
        사용자 메모리 가져오기 또는 생성

        Args:
            user_id: 사용자 ID

        Returns:
            SimpleMemory: 사용자 메모리
        """
        # 메모리 저장소에 있으면 반환
        if user_id in self.memory_store:
            return self.memory_store[user_id]

        # 파일에서 로드 시도
        memory = self.load_memory_from_file(user_id)
        if memory:
            self.memory_store[user_id] = memory
            return memory

        # 새로 생성
        memory = self._create_memory()
        self.memory_store[user_id] = memory
        return memory

    def save_context(self, user_id: str, input_text: str, output_text: str):
        """
        대화 내용 저장

        Args:
            user_id: 사용자 ID
            input_text: 사용자 입력
            output_text: AI 출력
        """
        memory = self.get_or_create_memory(user_id)
        memory.add_user_message(input_text)
        memory.add_ai_message(output_text)

        # 파일로 저장
        self.save_memory_to_file(user_id)

    def get_chat_history(self, user_id: str) -> List[Dict]:
        """
        대화 기록 조회 (API 응답용)

        Args:
            user_id: 사용자 ID

        Returns:
            List[Dict]: 대화 기록
        """
        memory = self.get_or_create_memory(user_id)
        messages = memory.get_messages()

        return [
            {
                "type": msg.type,
                "content": msg.content
            }
            for msg in messages
        ]

    def save_memory_to_file(self, user_id: str) -> bool:
        """
        대화 기록을 JSON 파일로 저장

        Args:
            user_id: 사용자 ID

        Returns:
            bool: 저장 성공 여부
        """
        if user_id not in self.memory_store:
            return False

        try:
            memory = self.memory_store[user_id]
            messages = memory.get_messages()

            # JSON 형태로 변환
            history_data = [
                {
                    "type": msg.type,
                    "content": msg.content,
                    "timestamp": datetime.now().isoformat()
                }
                for msg in messages
            ]

            # JSON 파일로 저장
            filepath = f"{self.config.MEMORY_DIR}/{user_id}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)

            print(f"[Memory] 대화 기록 저장: {filepath}")
            return True

        except Exception as e:
            print(f"[Memory] 저장 실패: {e}")
            return False

    def load_memory_from_file(self, user_id: str) -> SimpleMemory:
        """
        JSON 파일에서 대화 기록 복원

        Args:
            user_id: 사용자 ID

        Returns:
            SimpleMemory: 복원된 메모리 (없으면 None)
        """
        filepath = f"{self.config.MEMORY_DIR}/{user_id}.json"

        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                history_data = json.load(f)

            memory = self._create_memory()

            # 메시지 복원
            for item in history_data:
                if item["type"] == "human":
                    memory.add_user_message(item["content"])
                elif item["type"] == "ai":
                    memory.add_ai_message(item["content"])

            print(f"[Memory] 대화 기록 로드: {filepath} ({len(history_data)}개)")
            return memory

        except Exception as e:
            print(f"[Memory] 로드 실패: {e}")
            return None

    def clear_memory(self, user_id: str) -> bool:
        """
        특정 사용자의 메모리 삭제

        Args:
            user_id: 사용자 ID

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            # 메모리 저장소에서 삭제
            if user_id in self.memory_store:
                del self.memory_store[user_id]

            # 파일 삭제
            filepath = f"{self.config.MEMORY_DIR}/{user_id}.json"
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"[Memory] 대화 기록 삭제: {filepath}")

            return True

        except Exception as e:
            print(f"[Memory] 삭제 실패: {e}")
            return False

    def get_all_user_ids(self) -> List[str]:
        """
        저장된 모든 사용자 ID 가져오기

        Returns:
            List[str]: 사용자 ID 목록
        """
        try:
            files = os.listdir(self.config.MEMORY_DIR)
            user_ids = [f.replace(".json", "") for f in files if f.endswith(".json")]
            return user_ids
        except Exception as e:
            print(f"[Memory] 사용자 목록 조회 실패: {e}")
            return []

    def get_memory_info(self, user_id: str) -> dict:
        """
        메모리 정보 조회

        Args:
            user_id: 사용자 ID

        Returns:
            dict: 메모리 정보
        """
        memory = self.get_or_create_memory(user_id)
        messages = memory.get_messages()

        return {
            "user_id": user_id,
            "conversation_count": len(messages) // 2,
            "total_messages": len(messages),
            "history": [
                {"type": msg.type, "content": msg.content}
                for msg in messages
            ]
        }

    def get_active_users(self) -> int:
        """활성 사용자 수 반환"""
        return len(self.get_all_user_ids())

    def get_total_conversations(self) -> int:
        """전체 대화 수 반환"""
        total = 0
        for user_id in self.get_all_user_ids():
            info = self.get_memory_info(user_id)
            total += info.get('conversation_count', 0)
        return total