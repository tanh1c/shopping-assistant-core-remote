import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Shared LLM Settings
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "alibaba")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.5-plus")
    LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("ALIBABA_API_KEY")
    LLM_BASE_URL = os.getenv(
        "LLM_BASE_URL",
        "https://coding-intl.dashscope.aliyuncs.com/v1",
    )
    LLM_ANTHROPIC_BASE_URL = os.getenv(
        "LLM_ANTHROPIC_BASE_URL",
        "https://coding-intl.dashscope.aliyuncs.com/apps/anthropic",
    )
    LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))

settings = Config()
