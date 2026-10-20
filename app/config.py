import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    llm_api_key: str = ""
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "openai/gpt-oss-120b"
    embeddings: str = "default"  # "default" | "hash"
    kb_dir: str = "data/kb"
    chroma_dir: str = ".chroma"
    db_path: str = "supportpilot.db"
    top_k: int = 4
    min_retrieval_score: float = 0.30
    confidence_threshold: float = 0.70

    @classmethod
    def from_env(cls) -> "Settings":
        d = cls()
        return cls(
            llm_api_key=os.getenv("LLM_API_KEY", d.llm_api_key),
            llm_base_url=os.getenv("LLM_BASE_URL", d.llm_base_url),
            llm_model=os.getenv("LLM_MODEL", d.llm_model),
            embeddings=os.getenv("EMBEDDINGS", d.embeddings),
            kb_dir=os.getenv("KB_DIR", d.kb_dir),
            chroma_dir=os.getenv("CHROMA_DIR", d.chroma_dir),
            db_path=os.getenv("DB_PATH", d.db_path),
            top_k=int(os.getenv("TOP_K", d.top_k)),
            min_retrieval_score=float(os.getenv("MIN_RETRIEVAL_SCORE", d.min_retrieval_score)),
            confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", d.confidence_threshold)),
        )
