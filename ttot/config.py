"""
config.py - 서버 설정 파일
JSON 파일에서 설정을 로드하고 관리합니다.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class Config:
    """서버 설정 클래스 - JSON 기반"""
    
    # 기본 설정 파일 경로
    CONFIG_FILE_PATH = "config.json"
    
    # API 키 (환경 변수에서만 로드 - 보안)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    
    # JSON에서 로드될 설정들
    _config_data = None
    
    # 서버 설정
    SERVER_HOST = None
    SERVER_PORT = None
    SERVER_TITLE = None
    SERVER_DESCRIPTION = None
    SERVER_VERSION = None
    
    # 모델 설정
    LLM_MODEL = None
    EMBEDDING_MODEL = None
    
    # LLM 파라미터
    TEMPERATURE = None
    MAX_TOKENS = None
    
    # 경로 설정
    CHROMA_PERSIST_DIR = None
    MEMORY_DIR = None
    SYSTEM_PROMPT_FILE = None

    # 메모리 설정
    MEMORY_K = None

    # RAG 설정
    CHUNK_SIZE = None
    CHUNK_OVERLAP = None
    RETRIEVER_K = None

    # CORS 설정
    CORS_ORIGINS = None
    CORS_CREDENTIALS = None
    CORS_METHODS = None
    CORS_HEADERS = None

    @classmethod
    def load_config_from_json(cls, config_path: str = None):
        """JSON 파일에서 설정 로드"""
        config_path = config_path or cls.CONFIG_FILE_PATH

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                cls._config_data = json.load(f)

            # 서버 설정
            server = cls._config_data.get('server', {})
            cls.SERVER_HOST = server.get('host', '0.0.0.0')
            cls.SERVER_PORT = server.get('port', 8002)
            cls.SERVER_TITLE = server.get('title', 'LLM Server')
            cls.SERVER_DESCRIPTION = server.get('description', '')
            cls.SERVER_VERSION = server.get('version', '1.0.0')

            # 모델 설정
            model = cls._config_data.get('model', {})
            cls.LLM_MODEL = model.get('llm_model', 'gpt-4o-mini')
            cls.EMBEDDING_MODEL = model.get('embedding_model', 'text-embedding-3-small')

            # LLM 파라미터
            params = cls._config_data.get('llm_parameters', {})
            cls.TEMPERATURE = params.get('temperature', 0.7)
            cls.MAX_TOKENS = params.get('max_tokens', 300)

            # 경로 설정
            paths = cls._config_data.get('paths', {})
            cls.CHROMA_PERSIST_DIR = paths.get('chroma_persist_dir', './chroma_db')
            cls.MEMORY_DIR = paths.get('memory_dir', './chat_history')
            cls.SYSTEM_PROMPT_FILE = paths.get('system_prompt_file', './system_prompt.json')

            # 메모리 설정
            memory = cls._config_data.get('memory', {})
            cls.MEMORY_K = memory.get('k', 15)

            # RAG 설정
            rag = cls._config_data.get('rag', {})
            cls.CHUNK_SIZE = rag.get('chunk_size', 500)
            cls.CHUNK_OVERLAP = rag.get('chunk_overlap', 50)
            cls.RETRIEVER_K = rag.get('retriever_k', 3)

            # CORS 설정
            cors = cls._config_data.get('cors', {})
            cls.CORS_ORIGINS = cors.get('allow_origins', ['*'])
            cls.CORS_CREDENTIALS = cors.get('allow_credentials', True)
            cls.CORS_METHODS = cors.get('allow_methods', ['*'])
            cls.CORS_HEADERS = cors.get('allow_headers', ['*'])

            print(f"[Config] 설정 파일 로드 완료: {config_path}")

        except FileNotFoundError:
            raise FileNotFoundError(f"{config_path} 파일을 찾을 수 없습니다!")
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 파싱 오류: {e}")
        except Exception as e:
            raise Exception(f"설정 로드 실패: {e}")

    @classmethod
    def validate_config(cls):
        """설정 검증"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다!")

        os.environ["OPENAI_API_KEY"] = cls.OPENAI_API_KEY
        print(f"[Config] API 키 로드 완료")

        if not cls.LLM_MODEL:
            raise ValueError("LLM_MODEL이 설정되지 않았습니다!")
        if not cls.EMBEDDING_MODEL:
            raise ValueError("EMBEDDING_MODEL이 설정되지 않았습니다!")

    @classmethod
    def create_directories(cls):
        """필요한 디렉토리 생성"""
        Path(cls.CHROMA_PERSIST_DIR).mkdir(exist_ok=True)
        Path(cls.MEMORY_DIR).mkdir(exist_ok=True)
        print(f"[Config] 디렉토리 생성 완료")

    @classmethod
    def initialize(cls, config_path: str = None):
        """설정 초기화"""
        cls.load_config_from_json(config_path)
        cls.validate_config()
        cls.create_directories()
        print(f"[Config] 설정 초기화 완료")

    @classmethod
    def get_config_dict(cls) -> dict:
        """현재 설정을 딕셔너리로 반환"""
        return {
            "server": {
                "host": cls.SERVER_HOST,
                "port": cls.SERVER_PORT,
                "title": cls.SERVER_TITLE,
                "description": cls.SERVER_DESCRIPTION,
                "version": cls.SERVER_VERSION
            },
            "model": {
                "llm_model": cls.LLM_MODEL,
                "embedding_model": cls.EMBEDDING_MODEL
            },
            "llm_parameters": {
                "temperature": cls.TEMPERATURE,
                "max_tokens": cls.MAX_TOKENS
            },
            "memory": {
                "k": cls.MEMORY_K
            },
            "rag": {
                "chunk_size": cls.CHUNK_SIZE,
                "chunk_overlap": cls.CHUNK_OVERLAP,
                "retriever_k": cls.RETRIEVER_K
            }
        }