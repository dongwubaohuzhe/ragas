"""
Configuration constants for RAGAS Evaluation Tool
"""
import os
import urllib3  # type: ignore[import-untyped]

# AWS Bedrock Configuration (region for Bedrock client)
AWS_REGION_NAME = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-gov-west-1"))

# API Configuration
DEFAULT_API_URL = "https://api.url.com/chat"
DEFAULT_TENANT = "tenant-name"
DEFAULT_KB_NAME = "kb-name"

# Default model IDs (must match entries in model_config.SUPPORTED_MODELS / SUPPORTED_EMBEDDINGS)
DEFAULT_LLM_MODEL_ID = os.getenv("DEFAULT_LLM_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
DEFAULT_EMBEDDING_MODEL_ID = os.getenv("DEFAULT_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
# API-friendly name for the default LLM (used when calling external API)
DEFAULT_API_MODEL_NAME = os.getenv("DEFAULT_API_MODEL_NAME", "claude-3-5-sonnet")

# Retry Configuration
MAX_RETRIES = 3
API_TIMEOUT = 30
EVALUATION_RETRY_DELAY = 5

# Parallel evaluation (per-item retrieval + answer generation)
def _int_env(name: str, default: int, min_val: int, max_val: int = 1000) -> int:
    try:
        v = int(os.getenv(name, str(default)))
        return max(min_val, min(max_val, v))
    except (TypeError, ValueError):
        return default

MAX_WORKERS = _int_env("MAX_WORKERS", 8, 1, 64)  # concurrent items per batch (min 1 to avoid infinite loop)
# Per-item timeout in seconds (retrieval + answer); allow slow items to complete
ITEM_TIMEOUT = _int_env("ITEM_TIMEOUT", 120, 10)

# Answer Generation Configuration
MAX_ANSWER_TOKENS = 200
MAX_CONTEXT_LENGTH = 1000
MIN_CONTEXT_LENGTH = 10
MIN_ANSWER_LENGTH = 10

# SSL Configuration
# Default False to avoid InsecureRequestWarning for internal/self-signed APIs.
# Set env SSL_VERIFY=true (or True) in production with proper certificates.
SSL_VERIFY = os.getenv("SSL_VERIFY", "false").lower() in ("true", "1")
if not SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

