"""
Configuration constants for RAGAS Evaluation Tool
"""
import os

# AWS Bedrock Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-gov-west-1")
AWS_REGION_NAME = "us-gov-west-1"  # Default region

# API Configuration
DEFAULT_API_URL = "https://api.url.com/chat"
DEFAULT_TENANT = "tenant-name"
DEFAULT_KB_NAME = "kb-name"

# Retry Configuration
MAX_RETRIES = 3
API_TIMEOUT = 30
EVALUATION_RETRY_DELAY = 5

# Answer Generation Configuration
MAX_ANSWER_TOKENS = 200
MAX_CONTEXT_LENGTH = 1000
MIN_CONTEXT_LENGTH = 10
MIN_ANSWER_LENGTH = 10

# SSL Configuration
# Note: verify=False is used for internal APIs that may use self-signed certificates
# In production, set this to True and ensure proper SSL certificates are configured
SSL_VERIFY = os.getenv("SSL_VERIFY", "False").lower() == "true"

