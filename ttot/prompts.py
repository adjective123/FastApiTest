"""
prompts.py - 시스템 프롬프트 관리
"""
import json
import os


class PromptManager:
    """시스템 프롬프트 관리 클래스"""
    
    DEFAULT_PROMPT = """당신은 어르신들의 따뜻한 말동무입니다.

# 대화 원칙
- 존댓말을 사용하고 항상 공손하게 대화합니다
- 짧고 명확하게 답변합니다 (2-3문장)
- 경청하고 공감하는 태도를 보입니다
- 주어진 컨텍스트 정보를 바탕으로 정확하게 답변합니다
- 컨텍스트에 없는 정보는 추측하지 않고 모른다고 솔직히 말합니다

# RAG 사용 원칙
- 검색된 컨텍스트 정보를 우선적으로 활용합니다
- 컨텍스트에 관련 정보가 있으면 그것을 바탕으로 답변합니다
- 컨텍스트에 정보가 없으면 일반적인 지식으로 답변합니다

# 한국 문화 이해
- 명절, 제사, 효도 등 한국 전통 가치 이해
- "진지 드셨어요?", "어디 아프신 데는 없으세요?" 같은 한국식 인사
- 사투리 표현도 자연스럽게 이해

# 피해야 할 것
- 너무 긴 답변
- 어려운 전문용어
- 컨텍스트에 없는 정보를 지어내기
"""
    
    def __init__(self, prompt_file: str = None):
        """
        Args:
            prompt_file: JSON 형식의 프롬프트 파일 경로
        """
        self.prompt_file = prompt_file
        self.system_prompt = self.load_prompt()
    
    def load_prompt(self) -> str:
        """
        JSON 파일에서 프롬프트 로드
        파일이 없으면 기본 프롬프트 사용
        """
        if self.prompt_file and os.path.exists(self.prompt_file):
            try:
                with open(self.prompt_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    prompt = data.get('system_prompt', self.DEFAULT_PROMPT)
                    print(f"[PromptManager] 프롬프트 로드 완료: {self.prompt_file}")
                    return prompt
            except Exception as e:
                print(f"[PromptManager] 프롬프트 로드 실패: {e}")
                print(f"[PromptManager] 기본 프롬프트 사용")
                return self.DEFAULT_PROMPT
        else:
            print(f"[PromptManager] 기본 프롬프트 사용")
            return self.DEFAULT_PROMPT
    
    def save_prompt(self, prompt: str = None) -> bool:
        """
        프롬프트를 JSON 파일로 저장
        
        Args:
            prompt: 저장할 프롬프트 (None이면 현재 프롬프트)
        
        Returns:
            bool: 저장 성공 여부
        """
        if not self.prompt_file:
            print(f"[PromptManager] 프롬프트 파일 경로가 설정되지 않았습니다")
            return False
        
        try:
            prompt_to_save = prompt if prompt else self.system_prompt
            
            data = {
                'system_prompt': prompt_to_save,
                'updated_at': str(datetime.now())
            }
            
            with open(self.prompt_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"[PromptManager] 프롬프트 저장 완료: {self.prompt_file}")
            return True
            
        except Exception as e:
            print(f"[PromptManager] 프롬프트 저장 실패: {e}")
            return False
    
    def update_prompt(self, new_prompt: str):
        """프롬프트 업데이트"""
        self.system_prompt = new_prompt
        self.save_prompt(new_prompt)
    
    def get_prompt(self) -> str:
        """현재 시스템 프롬프트 반환"""
        return self.system_prompt


if __name__ == "__main__":
    from datetime import datetime
    
    # 테스트
    manager = PromptManager()
    print(manager.get_prompt()[:100])
