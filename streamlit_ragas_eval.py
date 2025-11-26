"""
RAGAS Evaluation Tool - Main Application
Evaluates RAG systems using RAGAS metrics
"""
import streamlit as st
import pandas as pd
import requests
from datasets import Dataset
from typing import List, Dict, Any, Optional, Tuple
from langchain_community.chat_models import BedrockChat
from langchain_community.embeddings import BedrockEmbeddings
from ragas import evaluate
from ragas.metrics import faithfulness, context_recall, context_precision, answer_relevancy
from model_config import get_model_config
from config import (
    AWS_REGION_NAME,
    MAX_RETRIES,
    API_TIMEOUT,
    EVALUATION_RETRY_DELAY,
    MAX_ANSWER_TOKENS,
    MAX_CONTEXT_LENGTH,
    MIN_CONTEXT_LENGTH,
    MIN_ANSWER_LENGTH,
    SSL_VERIFY
)
import io
import time
import random
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Document:
    """Represents a document with content and metadata"""
    def __init__(self, page_content: str, metadata: Optional[Dict[str, Any]] = None):
        self.page_content = page_content
        self.metadata = metadata or {}

def extract_model_name_for_api(bedrock_model_id: str) -> str:
    """Extract simplified model name from Bedrock model ID for API calls"""
    # Convert Bedrock model IDs to API-friendly format
    # Check more specific versions first
    if "claude-3-7-sonnet" in bedrock_model_id:
        return "claude-3-7-sonnet"
    elif "claude-3-5-sonnet" in bedrock_model_id:
        return "claude-3-5-sonnet"
    elif "claude-3-sonnet" in bedrock_model_id:
        return "claude-3-sonnet"
    elif "claude-3-haiku" in bedrock_model_id:
        return "claude-3-haiku"
    elif "titan-text-express" in bedrock_model_id:
        return "titan-text-express"
    elif "titan-text-lite" in bedrock_model_id:
        return "titan-text-lite"
    # Default fallback
    return "claude-3-7-sonnet"

class SimpleAPIRetriever:
    """Retriever for fetching documents from external API"""
    def __init__(self, api_url: str, bearer_token: str, tenant: str, 
                 knowledge_base_name: str, model: str = "claude-3-7-sonnet"):
        self.api_url = api_url
        self.bearer_token = bearer_token
        self.tenant = tenant
        self.knowledge_base_name = knowledge_base_name
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }

    def get_relevant_documents(self, query: str, max_retries: int = MAX_RETRIES) -> List[Document]:
        """
        Retrieve relevant documents from the API
        
        Args:
            query: The search query
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of Document objects
        """
        payload = {
            "tenant": self.tenant,
            "message": query,
            "model": self.model,
            "knowledgeBaseName": self.knowledge_base_name
        }
       
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url, 
                    json=payload, 
                    headers=self.headers, 
                    verify=SSL_VERIFY, 
                    timeout=API_TIMEOUT
                )
                response.raise_for_status()
                result = response.json()
               
                documents = []
               
                if isinstance(result, list) and len(result) > 1:
                    bot_response = result[1]
                   
                    if 'references' in bot_response:
                        for ref in bot_response['references']:
                            if 'content' in ref and ref['content'].strip():
                                doc = Document(
                                    page_content=ref['content'].strip(),
                                    metadata={
                                        'source': ref.get('name', 'unknown'),
                                        'location': ref.get('location', '')
                                    }
                                )
                                documents.append(doc)
                   
                    if not documents and 'message' in bot_response:
                        doc = Document(
                            page_content=bot_response['message'],
                            metadata={'source': 'bot_response'}
                        )
                        documents.append(doc)
               
                elif isinstance(result, dict):
                    if 'sources' in result:
                        for source in result['sources']:
                            doc = Document(
                                page_content=source.get('content', ''),
                                metadata=source.get('metadata', {})
                            )
                            documents.append(doc)
                    elif 'answer' in result:
                        doc = Document(
                            page_content=result['answer'],
                            metadata={'source': 'api_response'}
                        )
                        documents.append(doc)
               
                return documents
           
            except Exception as e:
                if attempt == max_retries - 1:
                    st.error(f"Error retrieving documents after {max_retries} attempts: {e}")
                    return []
               
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                st.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
       
        return []

def generate_answer_from_context(question: str, contexts: List[str], 
                                 llm_model: Optional[BedrockChat] = None) -> str:
    """
    Generate an answer from context using LLM or extractive methods
    
    Args:
        question: The question to answer
        contexts: List of context strings
        llm_model: Optional LLM model for generation
        
    Returns:
        Generated answer string
    """
    if not contexts or not any(ctx.strip() for ctx in contexts):
        return "No relevant information found to answer this question."
   
    valid_contexts = []
    for ctx in contexts:
        if ctx and ctx.strip():
            cleaned = ctx.strip().replace('\\n', ' ').replace('\n', ' ')
            cleaned = ' '.join(cleaned.split())
            if len(cleaned) > MIN_CONTEXT_LENGTH:
                valid_contexts.append(cleaned)
   
    if not valid_contexts:
        return "No valid context available to generate an answer."
   
    # Improved keyword matching with synonyms and related terms
    question_lower = question.lower()
    key_terms = []
   
    # Extract meaningful terms (longer than 3 chars, not common words)
    stop_words = {'what', 'when', 'where', 'why', 'how', 'does', 'the', 'and', 'for', 'with', 'are', 'you'}
    for term in question_lower.split():
        if len(term) > 3 and term not in stop_words:
            key_terms.append(term)
   
    # Add related terms for better matching
    if 'purpose' in question_lower or 'why' in question_lower:
        key_terms.extend(['goal', 'objective', 'reason', 'benefit', 'aim'])
    if 'step' in question_lower or 'first' in question_lower:
        key_terms.extend(['begin', 'start', 'initial', 'process'])
   
    combined_context = ' '.join(valid_contexts)
    # Try LLM-based answer generation first with retry logic
    if llm_model:
        for attempt in range(MAX_RETRIES):
            try:
                prompt = f"""Based on the following context, answer the question concisely and accurately.

Context: {combined_context[:MAX_CONTEXT_LENGTH]}

Question: {question}

Answer:"""
               
                response = llm_model.invoke(prompt)
                if hasattr(response, 'content'):
                    answer = response.content.strip()
                else:
                    answer = str(response).strip()
               
                if answer and len(answer) > MIN_ANSWER_LENGTH and answer != combined_context:
                    return answer
                break
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    logger.warning(f"LLM generation failed after {MAX_RETRIES} attempts: {e}")
                else:
                    time.sleep(2 ** attempt)
   
    # Fallback to improved extractive method
    sentences = combined_context.replace('!', '.').replace('?', '.').split('.')
    relevant_sentences = []
   
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 15:
            sentence_lower = sentence.lower()
            # Score sentences based on keyword matches
            score = sum(1 for term in key_terms if term in sentence_lower)
            if score > 0:
                relevant_sentences.append((sentence, score))
   
    if relevant_sentences:
        # Sort by relevance score and take top sentences
        relevant_sentences.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [sent[0] for sent in relevant_sentences[:2]]
        answer = '. '.join(top_sentences)
        if not answer.endswith('.'):
            answer += '.'
        return answer
   
    # Final fallback - return summarized context
    first_context = valid_contexts[0]
    if len(first_context) > 200:
        # Try to find the most relevant part
        parts = first_context.split('. ')
        for part in parts:
            if any(term in part.lower() for term in key_terms):
                return part + '.'
        # If no relevant part found, truncate
        return first_context[:200] + "..."
   
    return first_context

def run_ragas_evaluation(
    test_data: List[Dict[str, str]], 
    api_url: str, 
    bearer_token: str, 
    tenant: str, 
    knowledge_base_name: str, 
    model_id: str, 
    embedding_model_id: str
) -> Tuple[Optional[Any], Optional[List[str]]]:
    """
    Run RAGAS evaluation on test data
    
    Args:
        test_data: List of dictionaries with 'question' and 'ground_truth' keys
        api_url: API endpoint URL
        bearer_token: Bearer token for API authentication
        tenant: Tenant identifier
        knowledge_base_name: Name of the knowledge base
        model_id: Bedrock model ID for LLM
        embedding_model_id: Bedrock model ID for embeddings
        
    Returns:
        Tuple of (evaluation_result, questions_list) or (None, None) on failure
    """
    # Get model configuration once (used for both answer generation and evaluation)
    model_config = get_model_config(model_id)
    
    # Convert Bedrock model ID to API-friendly format
    api_model_name = extract_model_name_for_api(model_id)
    retriever = SimpleAPIRetriever(api_url, bearer_token, tenant, knowledge_base_name, model=api_model_name)
   
    questions = []
    answers = []
    contexts = []
    ground_truths = []
   
    progress_bar = st.progress(0)
   
    for i, item in enumerate(test_data):
        question = item['question']
        ground_truth = item['ground_truth']
       
        # Get documents from retriever
        documents = retriever.get_relevant_documents(question)
        context_list = [doc.page_content for doc in documents if doc.page_content and doc.page_content.strip()]
       
        # Ensure we have valid contexts
        if not context_list:
            context_list = ["No relevant context found for this question."]
       
        # Initialize LLM for answer generation
        try:
            # Use smaller max_tokens for answer generation
            answer_gen_kwargs = model_config["kwargs"].copy()
            if "max_tokens" in answer_gen_kwargs:
                answer_gen_kwargs["max_tokens"] = min(
                    MAX_ANSWER_TOKENS, 
                    answer_gen_kwargs.get("max_tokens", MAX_ANSWER_TOKENS)
                )
            elif "maxTokenCount" in answer_gen_kwargs:
                answer_gen_kwargs["maxTokenCount"] = min(
                    MAX_ANSWER_TOKENS, 
                    answer_gen_kwargs.get("maxTokenCount", MAX_ANSWER_TOKENS)
                )
            
            llm_model = BedrockChat(
                region_name=AWS_REGION_NAME,
                model_id=model_id,
                model_kwargs=answer_gen_kwargs
            )
        except Exception as e:
            st.warning(f"Could not initialize LLM for answer generation: {e}")
            llm_model = None
       
        # Generate answer from contexts using LLM
        answer = generate_answer_from_context(question, context_list, llm_model)
       
        if not answer or not answer.strip():
            answer = "Unable to generate answer from available context."
       
        questions.append(str(question).strip())
        answers.append(str(answer).strip())
        contexts.append([str(ctx).strip() for ctx in context_list])
        ground_truths.append(str(ground_truth).strip())
       
        progress_bar.progress((i + 1) / len(test_data))
   
    if not questions:
        st.error("No valid data generated for evaluation")
        return None, None
   
    # Create dataset
    dataset = Dataset.from_dict({
        'question': questions,
        'answer': answers,
        'contexts': contexts,
        'ground_truth': ground_truths
    })
   
    # Use model configuration (already retrieved above)

    # Initialize models
    #bedrock_model = BedrockChat(
    #    region_name="us-gov-west-1",
    #    model_id=model_id,
    #    model_kwargs={"temperature": 0.1, "max_tokens": 512}
    #)

    bedrock_model = BedrockChat(
        region_name=AWS_REGION_NAME,
        model_id=model_id,
        model_kwargs=model_config["kwargs"]
    )
   
    bedrock_embeddings = BedrockEmbeddings(
        region_name=AWS_REGION_NAME,
        model_id=embedding_model_id
    )
   
    # Run evaluation with retry logic
    for attempt in range(MAX_RETRIES):
        try:
            result = evaluate(
                dataset,
                metrics=[faithfulness, context_recall, context_precision, answer_relevancy],
                llm=bedrock_model,
                embeddings=bedrock_embeddings
            )
            break
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                st.error(f"Evaluation failed after {MAX_RETRIES} attempts: {e}")
                logger.error(f"Evaluation failed: {e}", exc_info=True)
                return None, None
            st.warning(f"Evaluation attempt {attempt + 1} failed, retrying...")
            time.sleep(EVALUATION_RETRY_DELAY)
   
    return result, questions

def test_api_connection(api_url: str, bearer_token: str, tenant: str, 
                       knowledge_base_name: str, model: str = "claude-3-7-sonnet") -> Dict[str, Any]:
    """
    Test API connection with a simple query
    
    Args:
        api_url: API endpoint URL
        bearer_token: Bearer token for authentication
        tenant: Tenant identifier
        knowledge_base_name: Knowledge base name
        model: Model name for API
        
    Returns:
        Dictionary with test results
    """
    result = {
        "success": False,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": "",
        "details": {},
        "error": None
    }
    
    try:
        # Create a simple test query
        test_query = "test connection"
        payload = {
            "tenant": tenant,
            "message": test_query,
            "model": model,
            "knowledgeBaseName": knowledge_base_name
        }
        
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        
        # Make test request
        start_time = time.time()
        response = requests.post(
            api_url, 
            json=payload, 
            headers=headers, 
            verify=SSL_VERIFY, 
            timeout=API_TIMEOUT
        )
        elapsed_time = time.time() - start_time
        
        result["details"]["status_code"] = response.status_code
        result["details"]["response_time"] = f"{elapsed_time:.2f}s"
        
        if response.status_code == 200:
            result["success"] = True
            result["message"] = f"✅ API connection successful! Response time: {elapsed_time:.2f}s"
            try:
                response_data = response.json()
                result["details"]["response_type"] = type(response_data).__name__
                if isinstance(response_data, list):
                    result["details"]["response_items"] = len(response_data)
                elif isinstance(response_data, dict):
                    result["details"]["response_keys"] = list(response_data.keys())
            except:
                result["details"]["response_preview"] = response.text[:200]
        else:
            result["success"] = False
            result["message"] = f"❌ API returned status code {response.status_code}"
            result["error"] = response.text[:500]
            
    except requests.exceptions.Timeout:
        result["success"] = False
        result["message"] = "❌ API connection timeout - request took too long"
        result["error"] = "Request exceeded timeout limit"
    except requests.exceptions.ConnectionError as e:
        result["success"] = False
        result["message"] = "❌ API connection failed - could not reach server"
        result["error"] = str(e)
    except requests.exceptions.RequestException as e:
        result["success"] = False
        result["message"] = "❌ API request failed"
        result["error"] = str(e)
    except Exception as e:
        result["success"] = False
        result["message"] = "❌ Unexpected error during API test"
        result["error"] = str(e)
        logger.error(f"API test error: {e}", exc_info=True)
    
    return result

def test_bedrock_connection(model_id: str, embedding_model_id: str) -> Dict[str, Any]:
    """
    Test Bedrock connection by initializing models
    
    Args:
        model_id: Bedrock LLM model ID
        embedding_model_id: Bedrock embedding model ID
        
    Returns:
        Dictionary with test results
    """
    result = {
        "success": False,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": "",
        "details": {},
        "error": None
    }
    
    llm_test = {"success": False, "error": None}
    embedding_test = {"success": False, "error": None}
    
    # Test LLM connection
    try:
        model_config = get_model_config(model_id)
        start_time = time.time()
        llm_model = BedrockChat(
            region_name=AWS_REGION_NAME,
            model_id=model_id,
            model_kwargs=model_config["kwargs"]
        )
        elapsed_time = time.time() - start_time
        llm_test["success"] = True
        llm_test["init_time"] = f"{elapsed_time:.2f}s"
        result["details"]["llm"] = {
            "model_id": model_id,
            "status": "✅ Connected",
            "init_time": f"{elapsed_time:.2f}s"
        }
    except Exception as e:
        llm_test["error"] = str(e)
        result["details"]["llm"] = {
            "model_id": model_id,
            "status": "❌ Failed",
            "error": str(e)[:200]
        }
        logger.error(f"LLM test error: {e}", exc_info=True)
    
    # Test Embedding connection
    try:
        start_time = time.time()
        embedding_model = BedrockEmbeddings(
            region_name=AWS_REGION_NAME,
            model_id=embedding_model_id
        )
        elapsed_time = time.time() - start_time
        embedding_test["success"] = True
        embedding_test["init_time"] = f"{elapsed_time:.2f}s"
        result["details"]["embedding"] = {
            "model_id": embedding_model_id,
            "status": "✅ Connected",
            "init_time": f"{elapsed_time:.2f}s"
        }
    except Exception as e:
        embedding_test["error"] = str(e)
        result["details"]["embedding"] = {
            "model_id": embedding_model_id,
            "status": "❌ Failed",
            "error": str(e)[:200]
        }
        logger.error(f"Embedding test error: {e}", exc_info=True)
    
    # Overall result
    if llm_test["success"] and embedding_test["success"]:
        result["success"] = True
        result["message"] = "✅ Bedrock connection successful! Both LLM and Embedding models connected."
    elif llm_test["success"] or embedding_test["success"]:
        result["success"] = False
        result["message"] = "⚠️ Partial connection - one model failed"
        if not llm_test["success"]:
            result["error"] = f"LLM failed: {llm_test['error']}"
        if not embedding_test["success"]:
            result["error"] = f"Embedding failed: {embedding_test['error']}"
    else:
        result["success"] = False
        result["message"] = "❌ Bedrock connection failed - both models failed"
        result["error"] = f"LLM: {llm_test.get('error', 'Unknown')}, Embedding: {embedding_test.get('error', 'Unknown')}"
    
    return result

# Always render the UI - only skip if we're being imported during a test
# Use a module-level flag to track if we're in an import context
if not hasattr(st, '_ragas_skip_ui') or not st._ragas_skip_ui:
    from streamlit_ui import StreamlitUI
    
    # Main application
    st.title("RAGAS Evaluation Tool")
    
    ui = StreamlitUI()
    config = ui.render_sidebar()
    test_data = ui.render_file_upload()
    
    if test_data:
        ui.render_evaluation_section(test_data, config, run_ragas_evaluation)