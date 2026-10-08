# AUTOSAR HLD Document Analysis Assistant Configuration
import os
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
from pathlib import Path
from dotenv import load_dotenv

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
INDEX_DIR = DATA_DIR / "index"
PROCESSED_DIR = DATA_DIR / "processed"
EXPORTS_DIR = DATA_DIR / "exports"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"

# Ensure required directories exist
for directory in [DATA_DIR, UPLOADS_DIR, INDEX_DIR, PROCESSED_DIR, EXPORTS_DIR, SAMPLE_DATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Database
DB_PATH = PROCESSED_DIR / "autosar_analysis.db"

# Vector Store & Embedding Configuration
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
FAISS_INDEX_PATH = INDEX_DIR / "autosar_index.faiss"
FAISS_METADATA_PATH = INDEX_DIR / "autosar_metadata.json"

# Chunking Configuration
CHUNK_SIZE = 1000       # Target characters per chunk (~150-250 tokens)
CHUNK_OVERLAP = 150     # Overlap characters to preserve contextual boundaries
MIN_CHUNK_SIZE = 100    # Minimum characters to create a chunk

# LLM / Ollama Configuration
MODEL_NAME = "qwen2.5:1.5b"
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", MODEL_NAME)
FALLBACK_OLLAMA_MODELS = [
    MODEL_NAME,
    "llama3:latest",
    "qwen2.5:7b",
    "llama3.1:latest",
    "mistral:latest",
    "qwen:latest"
]

# Gemini Fallback Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_FALLBACK_MODEL = "gemini-2.5-flash"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Retrieval Configuration
TOP_K_RETRIEVAL = 5
SIMILARITY_THRESHOLD = 0.25
