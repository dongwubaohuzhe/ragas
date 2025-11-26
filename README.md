# Automated KB Testing

## Overview
Automated testing framework for RAGAS (Retrieval Augmented Generation Assessment) applications. This tool evaluates the quality of RAG (Retrieval Augmented Generation) systems by testing knowledge base retrieval accuracy and answer generation quality.

## Features
- Knowledge base retrieval testing
- Generation quality assessment
- Automated evaluation metrics (Faithfulness, Context Recall, Context Precision, Answer Relevancy)
- Performance benchmarking
- CSV-based test plan upload
- Configurable model selection

## Architecture

The application requires **two separate connections**:

### Connection 1: External API (Knowledge Base Retrieval)
- **Type**: HTTP REST API via `requests`
- **Purpose**: Retrieves documents/context from a knowledge base
- **Authentication**: Bearer token
- **Configuration**: 
  - API URL (configurable in UI)
  - Bearer Token
  - Tenant
  - Knowledge Base Name
- **Note**: This is an external API service that handles knowledge base queries. The API receives queries and returns relevant documents/context.

### Connection 2: Amazon Bedrock (LLM & Embeddings)
- **Type**: Direct AWS Bedrock connection via `boto3`/`langchain`
- **Region**: `us-gov-west-1` (AWS GovCloud)
- **Purpose**: 
  1. **Answer Generation**: Uses `BedrockChat` to generate answers from retrieved context
  2. **RAGAS Evaluation**: Uses `BedrockChat` for running evaluation metrics
  3. **Embeddings**: Uses `BedrockEmbeddings` for semantic similarity calculations
- **Authentication**: AWS credentials (from environment, IAM role, or credentials file)
- **Supported Models**:
  - LLM: Claude 3.5 Sonnet, Claude 3.7 Sonnet, Amazon Titan Text Express
  - Embeddings: Amazon Titan Embed Text v2

### Architecture Diagram
```
┌─────────────────┐
│  Streamlit App  │
└────────┬────────┘
         │
         ├───► Connection 1: External API (HTTP)
         │     └───► Retrieves documents from Knowledge Base
         │           (via intermediary API service)
         │
         └───► Connection 2: Amazon Bedrock (Direct)
               ├───► BedrockChat (LLM inference)
               └───► BedrockEmbeddings (vector embeddings)
```

## Prerequisites

1. **Python 3.12+** (or Python 3.x with fallback)
2. **AWS Credentials** configured for Bedrock access
   - Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
   - IAM role (if running on EC2)
   - AWS credentials file (`~/.aws/credentials`)
3. **API Access** to the knowledge base service
   - API URL
   - Bearer token
   - Tenant information
   - Knowledge base name

## Installation

### Windows (Automated)

**Standard Installation:**
1. Run `install.bat` to set up virtual environment and install dependencies
2. Run `start.bat` to launch the application

**Fast Installation (Recommended for slow connections):**
1. Run `install-fast.bat` for faster installation with strict version constraints
2. Uses `--no-cache-dir` and optimized resolver for faster downloads
3. Run `start.bat` to launch the application

### Manual Installation
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running the Application

### Windows
```bash
start.bat
```

### Manual
```bash
streamlit run streamlit_ragas_eval.py
```

## Configuration

### Environment Variables (Optional)

Create a `.env` file in the project root (see `.env.example` for template):

```bash
# AWS Configuration
AWS_REGION=us-gov-west-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# API Configuration (optional - can be set in UI)
API_URL=https://api.url.com/chat
TENANT=tenant-name
KNOWLEDGE_BASE_NAME=kb-name

# SSL Configuration
SSL_VERIFY=false
```

### AWS Credentials Setup

The application requires AWS credentials to access Bedrock. Configure using one of these methods:

1. **Environment Variables**:
   ```bash
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   export AWS_REGION=us-gov-west-1
   ```

2. **AWS Credentials File** (`~/.aws/credentials`):
   ```ini
   [default]
   aws_access_key_id = your_key
   aws_secret_access_key = your_secret
   region = us-gov-west-1
   ```

3. **IAM Role** (if running on EC2/ECS)

## Usage

### Step 1: Prepare Test Plan

Create a CSV file with the following columns:
- `question`: The test question to evaluate
- `ground_truth`: The expected/correct answer

**Example CSV format** (see `example_test_plan.csv`):
```csv
question,ground_truth
What is the purpose of this system?,The system is designed to evaluate RAG applications.
How do I configure the API?,Configure the API by providing the URL and bearer token.
```

### Step 2: Configure Settings

In the sidebar, configure:
- **API URL**: Endpoint for knowledge base retrieval
- **Bearer Token**: Authentication token for the API
- **Tenant**: Tenant identifier
- **Knowledge Base Name**: Name of the knowledge base to query
- **LLM Model**: Bedrock model for evaluation (Claude 3.5/3.7 Sonnet or Titan)
- **Embedding Model**: Bedrock embedding model (Titan Embed v2)

### Step 3: Upload and Run

1. Upload your test plan CSV file
2. Verify the loaded data preview
3. Click "🚀 Start RAGAS Evaluation"
4. Wait for evaluation to complete (may take several minutes)

### Step 4: Download Results

- Results are automatically saved with timestamp
- Download CSV includes:
  - All evaluation metrics
  - Timestamp
  - Knowledge base name
  - Model IDs used
  - Individual question results

## Evaluation Metrics

The tool evaluates RAG systems using four key metrics:

- **Faithfulness** (0-1): Measures if the answer is factually consistent with the given context. Higher is better.
- **Context Recall** (0-1): Measures how much of the ground truth can be attributed to the retrieved context. Higher is better.
- **Context Precision** (0-1): Measures how relevant the retrieved contexts are to the question. Higher is better.
- **Answer Relevancy** (0-1): Measures how relevant the generated answer is to the question. Higher is better.

## Test Plan Format

The test plan CSV must contain exactly two columns:

| Column | Description | Example |
|--------|-------------|---------|
| `question` | The question to test | "What is the purpose of this system?" |
| `ground_truth` | Expected answer | "The system evaluates RAG applications." |

**Important Notes**:
- Column names must match exactly (case-sensitive)
- Empty rows will be skipped
- Questions and ground_truth should be clear and specific
- See `example_test_plan.csv` for a sample format

## Troubleshooting

### Common Issues

#### 1. AWS Credentials Not Found
**Error**: `NoCredentialsError` or `Unable to locate credentials`

**Solution**:
- Verify AWS credentials are configured (see Configuration section)
- Check that credentials have Bedrock access permissions
- Ensure region is set correctly (`us-gov-west-1`)

#### 2. API Connection Failed
**Error**: `Error retrieving documents after 3 attempts`

**Solutions**:
- Verify API URL is correct and accessible
- Check bearer token is valid and not expired
- Ensure tenant and knowledge base name are correct
- Check network connectivity and firewall settings
- For internal APIs with self-signed certificates, set `SSL_VERIFY=false` in `.env`

#### 3. Model Not Found
**Error**: `Model not found` or `Invalid model ID`

**Solution**:
- Verify the model ID exists in your AWS Bedrock account
- Check model availability in `us-gov-west-1` region
- Ensure your AWS account has access to the selected model

#### 4. Evaluation Timeout
**Error**: Evaluation takes too long or times out

**Solutions**:
- Reduce the number of test cases in your CSV
- Check Bedrock service status
- Verify network connectivity
- Consider using faster models (Haiku instead of Sonnet)

#### 5. CSV Format Errors
**Error**: `CSV must contain 'question' and 'ground_truth' columns`

**Solution**:
- Ensure column names match exactly (case-sensitive)
- Check CSV encoding (should be UTF-8)
- Verify no special characters in column headers
- Use the provided `example_test_plan.csv` as a template

### Performance Tips

1. **Batch Size**: Process test plans in smaller batches (10-20 questions) for faster results
2. **Model Selection**: Use Claude Haiku for faster evaluation (lower quality) or Sonnet for better quality (slower)
3. **Network**: Ensure stable network connection for API and Bedrock calls
4. **Caching**: Results are not cached - re-running evaluation will make new API calls

## Development

### Project Structure

```
ragas/
├── streamlit_ragas_eval.py  # Main application
├── streamlit_ui.py          # UI components
├── model_config.py          # Model configurations
├── config.py                # Configuration constants
├── requirements.txt         # Python dependencies
├── install.bat             # Windows installation script
├── start.bat                # Windows startup script
├── setup_venv.bat           # Virtual environment setup
├── .env.example             # Environment variables template
├── example_test_plan.csv    # Example test plan
└── README.md                # This file
```

### Code Quality

- Type hints used throughout
- Comprehensive error handling
- Logging for debugging
- Constants in `config.py` for easy configuration
- Modular design with separate UI and evaluation logic

## License

This project is provided as-is for internal use.

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review error messages in the application
3. Check logs for detailed error information