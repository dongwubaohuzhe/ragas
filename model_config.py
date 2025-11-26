

"""Model configuration for different Bedrock models"""

SUPPORTED_MODELS = {
    "anthropic.claude-3-sonnet-20240229-v1:0": {
        "type": "claude",
        "kwargs": {"temperature": 0.1, "max_tokens": 1000}
    },
    "anthropic.claude-3-haiku-20240307-v1:0": {
        "type": "claude",
        "kwargs": {"temperature": 0.1, "max_tokens": 1000}
    },
    "anthropic.claude-3-5-sonnet-20240620-v1:0": {
        "type": "claude",
        "kwargs": {"temperature": 0.1, "max_tokens": 1000}
    },
    "anthropic.claude-3-7-sonnet-20250219-v1:0": {
        "type": "claude",
        "kwargs": {"temperature": 0.1, "max_tokens": 1000}
    },
    "amazon.titan-text-express-v1": {
        "type": "titan",
        "kwargs": {"temperature": 0.1, "maxTokenCount": 1000}
    },
    "amazon.titan-text-lite-v1": {
        "type": "titan",
        "kwargs": {"temperature": 0.1, "maxTokenCount": 1000}
    }
}

SUPPORTED_EMBEDDINGS = [
    "amazon.titan-embed-text-v1",
    "amazon.titan-embed-text-v2:0",
    "cohere.embed-english-v3",
    "cohere.embed-multilingual-v3"
]

def get_model_config(model_id):
    """Get configuration for a specific model"""
    return SUPPORTED_MODELS.get(model_id, {"type": "default", "kwargs": {"temperature": 0.1}})