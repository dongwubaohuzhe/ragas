"""Model configuration for different Bedrock models.

Single source of truth for supported models: kwargs, answer_gen_kwargs,
api_model_name, and optional inference_profile_id.
"""

from typing import Optional

# Ordered list of supported LLM model IDs (for UI dropdowns)
SUPPORTED_LLM_MODEL_IDS = [
    "anthropic.claude-sonnet-4-5-20250929-v1:0",
    "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "anthropic.claude-3-7-sonnet-20250219-v1:0",
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "amazon.nova-pro-v1:0",
    "amazon.titan-text-express-v1",
    "amazon.titan-text-lite-v1",
]

SUPPORTED_MODELS = {
    "anthropic.claude-sonnet-4-5-20250929-v1:0": {
        "type": "claude",
        "kwargs": {"temperature": 0.1, "max_tokens": 1000},
        "api_model_name": "claude-sonnet-4-5",
        "inference_profile_id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    },
    "anthropic.claude-3-sonnet-20240229-v1:0": {
        "type": "claude",
        "kwargs": {"temperature": 0.1, "max_tokens": 1000},
    },
    "anthropic.claude-3-haiku-20240307-v1:0": {
        "type": "claude",
        "kwargs": {"temperature": 0.1, "max_tokens": 1000},
    },
    "anthropic.claude-3-5-sonnet-20240620-v1:0": {
        "type": "claude",
        "kwargs": {"temperature": 0.1, "max_tokens": 1000},
    },
    "anthropic.claude-3-7-sonnet-20250219-v1:0": {
        "type": "claude",
        "kwargs": {"temperature": 0.1, "max_tokens": 1000},
    },
    "amazon.nova-pro-v1:0": {
        "type": "nova",
        "kwargs": {"temperature": 0.1, "max_tokens": 1000},
    },
    "amazon.titan-text-express-v1": {
        "type": "titan",
        "kwargs": {"temperature": 0.1, "maxTokenCount": 1000},
    },
    "amazon.titan-text-lite-v1": {
        "type": "titan",
        "kwargs": {"temperature": 0.1, "maxTokenCount": 1000},
    },
}

SUPPORTED_EMBEDDINGS = [
    "amazon.titan-embed-text-v1",
    "amazon.titan-embed-text-v2:0",
    "cohere.embed-english-v3",
    "cohere.embed-multilingual-v3",
]


def get_model_config(model_id: str) -> dict:
    """Return configuration for a specific Bedrock model (type, kwargs)."""
    return SUPPORTED_MODELS.get(
        model_id,
        {"type": "default", "kwargs": {"temperature": 0.1, "max_tokens": 1000}},
    )


def get_answer_gen_kwargs(model_id: str) -> dict:
    """Return kwargs for answer generation.

    Uses ``answer_gen_kwargs`` from config when defined (allowing per-model
    overrides for answer generation), otherwise falls back to ``kwargs``.
    """
    cfg = SUPPORTED_MODELS.get(model_id, {})
    return cfg.get(
        "answer_gen_kwargs",
        cfg.get("kwargs", {"temperature": 0.1, "max_tokens": 1000}),
    ).copy()


def get_api_model_name(model_id: str) -> Optional[str]:
    """Return the API-friendly model name from config, or ``None`` to use pattern matching."""
    return SUPPORTED_MODELS.get(model_id, {}).get("api_model_name")


def get_model_invocation_id(model_id: str, override: str = "") -> str:
    """Return the invocation ID for Bedrock API calls.

    If *override* is provided (e.g. from the UI sidebar), use that.
    Otherwise return the base *model_id* for standard on-demand invocation.
    The ``inference_profile_id`` in config is only a hint for the UI help
    text; it is never applied automatically.
    """
    if override and override.strip():
        return override.strip()
    return model_id