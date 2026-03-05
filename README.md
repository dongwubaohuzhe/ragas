# Automated KB Testing

## Overview
Automated testing framework for RAGAS (Retrieval Augmented Generation Assessment) applications. This tool evaluates the quality of RAG (Retrieval Augmented Generation) systems by testing knowledge base retrieval accuracy and answer generation quality.

## Features
- Knowledge base retrieval testing
- Generation quality assessment
- Automated evaluation metrics (Faithfulness, Context Recall, Context Precision, Answer Relevancy)
- Performance benchmarking
- CSV-based test plan upload with **column mapping** (choose which columns are question and ground truth)
- **Stop evaluation** from the UI; download partial results when stopped
- Results retained until you load a different file
- Configurable model selection and evaluation options (parallelism, timeout)

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
- **Region**: Configurable via `AWS_REGION` or `AWS_DEFAULT_REGION` (default `us-gov-west-1`)
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

1. **Python 3.12+** (required for UV installation)
2. **UV** - Fast Python package manager
   - Auto-installed by `install.bat` (Windows) or `install.sh` (Mac/Unix)
   - Or install manually: https://github.com/astral-sh/uv
3. **AWS Credentials** configured for Bedrock access
   - Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
   - IAM role (if running on EC2)
   - AWS credentials file (`~/.aws/credentials`)
4. **API Access** to the knowledge base service
   - API URL
   - Bearer token
   - Tenant information
   - Knowledge base name

## Installation

### UV Installation (Fast & Conflict-Free)

**UV** is a fast Python package manager that automatically resolves dependencies without version conflicts.

**Quick Setup (Windows):**
1. Run `install.bat` - This will install UV (if needed) and set up the project automatically
2. Run `start.bat` to launch the application

**Quick Setup (Mac/Unix):**
1. Run `./install.sh` - This will install UV (if needed) and set up the project automatically
2. Run `./start.sh` to launch the application

**Alternative:** If UV is already installed, use `uv-install.bat` (Windows) or `./uv-install.sh` (Mac/Unix) to only sync dependencies.

**Manual UV Setup (Windows):**
```bash
# Install UV (if not installed)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install project dependencies (UV automatically resolves versions)
uv sync --no-install-project

# Run the application
uv run streamlit run streamlit_ragas_eval.py
```

**Manual UV Setup (Mac/Unix):**
```bash
# Install UV (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
# Ensure ~/.local/bin is in your PATH: export PATH="$HOME/.local/bin:$PATH"

# Install project dependencies
uv sync --no-install-project

# Run the application
./start.sh
# Or: source .venv/bin/activate && streamlit run streamlit_ragas_eval.py
```

**Benefits of UV:**
- ✅ Automatic dependency resolution (no version conflicts)
- ✅ Much faster installation (10-100x faster than pip)
- ✅ No need to specify exact versions
- ✅ Automatically creates and manages virtual environment
- ✅ Works seamlessly with Python 3.12+

## Running the Application

```bash
# Windows
start.bat

# Mac/Unix
./start.sh

# Or manually (after activating venv)
uv run streamlit run streamlit_ragas_eval.py
```

On both platforms, `start.bat` / `start.sh` load optional environment variables from a `.env` file (e.g. `AWS_PROFILE`, `AWS_DEFAULT_PROFILE`) after activating the virtual environment. Copy `.env.example` to `.env` and set your values.

## Configuration

### Environment Variables (Optional)

Copy `.env.example` to `.env` in the project root and set your values. The `.env` file is gitignored.

**Start scripts** (`start.bat` / `start.sh`) load `.env` after activating the virtual environment, so you can set:

```bash
# AWS profile (e.g. after aws sso login) – loaded by start.bat / start.sh
AWS_PROFILE=your-profile-name
AWS_DEFAULT_PROFILE=your-profile-name
```

Other optional variables (see `config.py` and UI defaults):

```bash
# AWS (region used for Bedrock; credentials from profile or env)
AWS_REGION=us-gov-west-1

# API defaults (can also be set in UI)
# API_URL, TENANT, KNOWLEDGE_BASE_NAME

# SSL (set true in production)
SSL_VERIFY=false
```

### AWS Credentials Setup

The application needs AWS credentials for Bedrock. Recommended: use an **AWS profile** (e.g. SSO) and set it in `.env`:

```bash
# In .env (loaded by start.bat / start.sh)
AWS_PROFILE=your-sso-profile
AWS_DEFAULT_PROFILE=your-sso-profile
```

Other options:

1. **Environment variables**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and optionally `AWS_REGION` (default `us-gov-west-1`)
2. **Credentials file** (`~/.aws/credentials`) with a `[profile]` or default profile
3. **IAM role** when running on EC2/ECS

## Usage

### Step 1: Prepare Test Plan

Create a CSV file with at least two columns: one for the test question and one for the expected/correct answer. Column names can be anything; after uploading, you choose which column is the **question** and which is the **ground truth**.

**Example CSV format** (see `example_test_plan.csv`). If you name columns `question` and `ground_truth`, they are selected by default:
```csv
question,ground_truth
What is the purpose of this system?,The system is designed to evaluate RAG applications.
How do I configure the API?,Configure the API by providing the URL and bearer token.
```
You can use different headers (e.g. `query`, `expected_answer`) and map them in the app.

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
2. Select **Question column** and **Ground truth column** (defaults to `question` / `ground_truth` if present)
3. Verify the loaded data preview
4. Click **🚀 Start RAGAS Evaluation**
5. Evaluation runs in batches; you can click **▶️ Continue evaluation** for the next batch or **⏹️ Stop evaluation** to finish early with partial results

### Step 4: Download Results

- When evaluation completes (or after you stop), download the results CSV
- Results stay on screen until you load a different file
- Download CSV includes:
  - All evaluation metrics (faithfulness, context recall, context precision, answer relevancy)
  - Timestamp, knowledge base name, model IDs
  - Per-question results
- If you stopped early, the file is marked `_partial` and contains only the items evaluated up to that point

## Evaluation Metrics

The tool evaluates RAG systems using four key metrics:

- **Faithfulness** (0-1): Measures if the answer is factually consistent with the given context. Higher is better.
- **Context Recall** (0-1): Measures how much of the ground truth can be attributed to the retrieved context. Higher is better.
- **Context Precision** (0-1): Measures how relevant the retrieved contexts are to the question. Higher is better.
- **Answer Relevancy** (0-1): Measures how relevant the generated answer is to the question. Higher is better.

## Test Plan Format

The test plan CSV must have **at least two columns**. After upload, you choose which column is the question and which is the ground truth.

| Role        | Description              | Example column names (any allowed)     |
|-------------|--------------------------|----------------------------------------|
| Question    | The question to test     | `question`, `query`, `prompt`           |
| Ground truth| Expected/correct answer  | `ground_truth`, `expected_answer`, `answer` |

**Notes**:
- If your CSV has columns named `question` and `ground_truth` (case-insensitive after trim), they are auto-selected
- Empty cells are allowed; rows are still included
- See `example_test_plan.csv` for a sample

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

#### 5. CSV Format / Column Mapping
**Issue**: CSV has different column names (e.g. `query`, `answer`).

**Solution**: After uploading, use the **Question column** and **Ground truth column** dropdowns. Ensure at least two columns and UTF-8 encoding.

#### 6. Partial Results After Stop
**Behavior**: You clicked **⏹️ Stop evaluation** and see a partial CSV.

**Explanation**: The app computes RAGAS metrics for all completed items and offers a download. The filename includes `_partial`. You can run again with a smaller test plan or different settings.

### Performance Tips

1. **Batch size**: Use the sidebar **Evaluation options** to tune **Max parallel items** and **Per-item timeout**
2. **Model selection**: Claude Haiku is faster; Sonnet gives higher quality
3. **Stop early**: Use **⏹️ Stop evaluation** to get partial results without running the full set
4. **Network**: Stable connection helps for API and Bedrock calls

## Development

### Project Structure

```
ragas/
├── streamlit_ragas_eval.py  # Main application
├── streamlit_ui.py          # UI components
├── model_config.py          # Model configurations
├── config.py                # Configuration constants
├── pyproject.toml           # UV project configuration
├── install.bat / install.sh      # Main installation script (installs UV if needed + dependencies)
├── uv-install.bat / uv-install.sh # Alternative installation script (UV + dependencies only)
├── start.bat / start.sh          # Startup script (loads .env, then runs Streamlit)
├── .env.example                  # Template for .env (copy to .env)
├── .env                          # Local env vars (gitignored; optional)
├── example_test_plan.csv         # Example test plan
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