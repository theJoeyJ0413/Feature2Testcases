from dotenv import load_dotenv
import os

load_dotenv()

class Config:

    # OpenAI config
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # 单次 LLM 请求最长等待时间（秒），防止网络异常时无限挂起
    REQUEST_TIMEOUT = 900

    # Output config
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_PATH = os.path.join(PROJECT_ROOT, OUTPUT_DIR)

    # Supported input formats
    SUPPORTED_INPUT_FORMATS = {".txt", ".md", ".pdf"}

    @classmethod
    def validate(cls):
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set")
