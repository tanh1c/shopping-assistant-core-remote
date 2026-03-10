import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLM Settings
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    LLM_MODEL = os.getenv("LLM_MODEL", "phi3:mini")

settings = Config()