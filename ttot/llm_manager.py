"""
llm_manager.py - LLM 모델 관리
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

from config import Config
from prompts import PromptManager


class LLMManager:
    """LLM 모델 관리 클래스"""
    
    def __init__(self, config: Config = None, prompt_manager: PromptManager = None):
        """
        Args:
            config: 설정 객체
            prompt_manager: 프롬프트 관리자
        """
        self.config = config or Config()
        self.prompt_manager = prompt_manager or PromptManager()
        
        print(f"[LLMManager] LLM 모델 초기화: {self.config.LLM_MODEL}")
        
        self.llm = self._initialize_llm()
        
        print(f"[LLMManager] LLM 모델 로딩 완료")

    def _initialize_llm(self) -> ChatOpenAI:
        """LLM 모델 초기화"""
        # GPT-5는 max_completion_tokens 사용, temperature=1만 지원
        if 'gpt-5' in self.config.LLM_MODEL.lower():
            params = {
                "model": self.config.LLM_MODEL,
                "openai_api_key": self.config.OPENAI_API_KEY,
                "streaming": False
            }

            # max_completion_tokens가 있으면 추가
            if self.config.MAX_COMPLETION_TOKENS:
                params["max_completion_tokens"] = self.config.MAX_COMPLETION_TOKENS

            # GPT-5는 temperature를 설정하지 않음 (기본값 1 사용)
            print("[LLMManager] GPT-5 모드: temperature=1.0 (기본값)")

            return ChatOpenAI(**params)
        else:
            # GPT-4 이하는 max_tokens와 temperature 사용
            return ChatOpenAI(
                model=self.config.LLM_MODEL,
                temperature=self.config.TEMPERATURE,
                max_tokens=self.config.MAX_TOKENS,
                openai_api_key=self.config.OPENAI_API_KEY,
                streaming=False
            )
    
    def create_simple_chain(self):
        """단순 대화 체인 생성 (메모리 없음)"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompt_manager.get_prompt()),
            ("human", "{input}")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        return chain
    
    def create_conversational_chain(self):
        """대화 기록 포함 체인 생성"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompt_manager.get_prompt()),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        return chain
    
    def generate(self, text: str) -> str:
        """
        단순 텍스트 생성
        
        Args:
            text: 입력 텍스트
        
        Returns:
            str: 생성된 응답
        """
        chain = self.create_simple_chain()
        response = chain.invoke({"input": text})
        return response
    
    def generate_with_history(self, text: str, chat_history: list) -> str:
        """
        대화 기록을 포함한 텍스트 생성
        
        Args:
            text: 입력 텍스트
            chat_history: 대화 기록 (LangChain Message 형식)
        
        Returns:
            str: 생성된 응답
        """
        chain = self.create_conversational_chain()
        response = chain.invoke({
            "input": text,
            "chat_history": chat_history
        })
        return response


if __name__ == "__main__":
    # 테스트
    Config.initialize()
    
    llm_manager = LLMManager()
    response = llm_manager.generate("안녕하세요")
    print(f"응답: {response}")
