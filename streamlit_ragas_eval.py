"""
RAGAS Evaluation Tool - Main Application
Evaluates RAG systems using RAGAS metrics
"""
from __future__ import annotations

import streamlit as st
import requests
from typing import List, Dict, Any, Optional, Tuple, Callable
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
    SSL_VERIFY,
    DEFAULT_API_MODEL_NAME,
    MAX_WORKERS,
    ITEM_TIMEOUT,
)
import sys
import time
import random
import logging
import os
import signal
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# Allow quick stop with Ctrl+C: set flag and raise so process exits promptly
_shutdown_requested = False

def _handle_shutdown(signum: int, frame: Any) -> None:
    global _shutdown_requested
    _shutdown_requested = True
    raise KeyboardInterrupt()

try:
    signal.signal(signal.SIGINT, _handle_shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_shutdown)
except (ValueError, OSError):
    pass  # signal may not be available in all contexts (e.g. some threads)

# User-friendly console logging: clean format, less noise from third-party libs.
# Set LOG_LEVEL=WARNING or LOG_LEVEL=ERROR to reduce output (default: INFO).
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_LOG_LEVEL = getattr(logging, _LOG_LEVEL, logging.INFO)
_fmt = logging.Formatter("%(levelname)s: %(message)s")
_handler = logging.StreamHandler()
_handler.setFormatter(_fmt)
logging.root.setLevel(_LOG_LEVEL)
logging.root.handlers.clear()
logging.root.addHandler(_handler)
# Reduce noise from Streamlit and other libs (only show warnings/errors)
_NOISY_LOGGERS = {
    "streamlit": logging.WARNING,
    "streamlit.runtime.scriptrunner_utils.script_run_context": logging.ERROR,
    "streamlit.runtime.state.session_state_proxy": logging.ERROR,
    "urllib3": logging.ERROR,
}
for _name, _lvl in _NOISY_LOGGERS.items():
    logging.getLogger(_name).setLevel(_lvl)
logger = logging.getLogger(__name__)
logger.setLevel(_LOG_LEVEL)

# Reduce Bedrock/LangChain console noise: INFO and their ERROR tracebacks (we handle and log errors ourselves)
logging.getLogger("langchain_aws").setLevel(logging.CRITICAL)
# Silence RAGAS executor's "Exception raised in Job[N]: TimeoutError()" spam (we handle retries ourselves)
logging.getLogger("ragas.executor").setLevel(logging.CRITICAL)
logging.getLogger("ragas.utils").setLevel(logging.WARNING)
# Disable tqdm progress bars on the console (we show progress in the Streamlit UI instead)
os.environ.setdefault("TQDM_DISABLE", "1")

EXPIRED_TOKEN_MESSAGE = (
    "AWS security token expired. Refresh your credentials (e.g. run 'aws sso login' or refresh your session) and try again."
)

def _is_expired_token(e: Exception) -> bool:
    """True if e is botocore ClientError with ExpiredTokenException."""
    try:
        from botocore.exceptions import ClientError
        return (
            isinstance(e, ClientError)
            and e.response.get("Error", {}).get("Code") == "ExpiredTokenException"
        )
    except ImportError:
        msg = str(e)
        msg_lower = msg.lower()
        return "ExpiredTokenException" in msg or ("security token" in msg_lower and "expired" in msg_lower)

def _format_bedrock_error(e: Exception) -> str:
    """User-friendly message for Bedrock errors; avoids long tracebacks for expired token."""
    return EXPIRED_TOKEN_MESSAGE if _is_expired_token(e) else str(e)

class Document:
    """Represents a document with content and metadata"""
    def __init__(self, page_content: str, metadata: Optional[Dict[str, Any]] = None):
        self.page_content = page_content
        self.metadata = metadata or {}

# Ordered by specificity (longer match first) for API-friendly model name
_BEDROCK_TO_API_MODEL = [
    ("claude-3-7-sonnet", "claude-3-7-sonnet"),
    ("claude-3-5-sonnet", "claude-3-5-sonnet"),
    ("claude-3-sonnet", "claude-3-sonnet"),
    ("claude-3-haiku", "claude-3-haiku"),
    ("titan-text-express", "titan-text-express"),
    ("titan-text-lite", "titan-text-lite"),
]


def extract_model_name_for_api(bedrock_model_id: str) -> str:
    """Extract simplified model name from Bedrock model ID for API calls."""
    for substring, api_name in _BEDROCK_TO_API_MODEL:
        if substring in bedrock_model_id:
            return api_name
    return DEFAULT_API_MODEL_NAME

def _api_config_tuple(
    get_config: Callable[[], Tuple[str, str, str, str, str, str]]
) -> Tuple[str, str, str, str, str]:
    """Return (api_url, bearer_token, tenant, knowledge_base_name, api_model_name)."""
    c = get_config()
    return (c[0], c[1], c[2], c[3], extract_model_name_for_api(c[4]))


class SimpleAPIRetriever:
    """Retriever for fetching documents from external API. Uses get_api_config so token is read fresh per request/retry."""
    def __init__(
        self,
        api_url: str = None,
        bearer_token: str = None,
        tenant: str = None,
        knowledge_base_name: str = None,
        model: str = None,
        *,
        get_api_config: Callable[[], Tuple[str, str, str, str, str]] = None,
    ):
        if get_api_config is not None:
            self._get_api_config = get_api_config
            self._static = False
        else:
            if api_url is None or bearer_token is None or tenant is None or knowledge_base_name is None:
                raise ValueError("Either get_api_config or (api_url, bearer_token, tenant, knowledge_base_name) must be provided")
            self._api_url = api_url
            self._tenant = tenant
            self._knowledge_base_name = knowledge_base_name
            self._model = model if model is not None else DEFAULT_API_MODEL_NAME
            self._bearer_token = bearer_token
            self._static = True

    def _current_config(self) -> Tuple[str, str, str, str, str]:
        if self._static:
            return (self._api_url, self._bearer_token, self._tenant, self._knowledge_base_name, self._model)
        return self._get_api_config()

    def get_relevant_documents(self, query: str, max_retries: int = MAX_RETRIES, silent: bool = False) -> List[Document]:
        """
        Retrieve relevant documents from the API. Uses fresh API config (bearer token, etc.) on each request and each retry.
        When silent=True (e.g. in worker threads), do not call st.* so Streamlit context is not required.
        """
        for attempt in range(max_retries):
            api_url, bearer_token, tenant, knowledge_base_name, model = self._current_config()
            headers = {
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "tenant": tenant,
                "message": query,
                "model": model,
                "knowledgeBaseName": knowledge_base_name
            }
            try:
                response = requests.post(
                    api_url,
                    json=payload,
                    headers=headers,
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
                    if not silent:
                        st.error(f"Error retrieving documents after {max_retries} attempts: {e}")
                    else:
                        logger.warning(f"Error retrieving documents after {max_retries} attempts: {e}")
                    return []
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                if not silent:
                    st.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time:.1f}s...")
                else:
                    logger.debug(f"Retrieval attempt {attempt + 1} failed, retrying in {wait_time:.1f}s")
                time.sleep(wait_time)
        return []

def generate_answer_from_context(
    question: str,
    contexts: List[str],
    llm_model: Optional[Any] = None,
    get_llm_model: Optional[Callable[[], Any]] = None,
) -> str:
    """
    Generate an answer from context using LLM or extractive methods.
    If get_llm_model is provided, each retry uses a fresh LLM client (e.g. fresh AWS credentials).
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
   
    question_lower = question.lower()
    key_terms = []
    stop_words = {'what', 'when', 'where', 'why', 'how', 'does', 'the', 'and', 'for', 'with', 'are', 'you'}
    for term in question_lower.split():
        if len(term) > 3 and term not in stop_words:
            key_terms.append(term)
    if 'purpose' in question_lower or 'why' in question_lower:
        key_terms.extend(['goal', 'objective', 'reason', 'benefit', 'aim'])
    if 'step' in question_lower or 'first' in question_lower:
        key_terms.extend(['begin', 'start', 'initial', 'process'])
   
    combined_context = ' '.join(valid_contexts)
    use_llm = llm_model is not None or get_llm_model is not None
    if use_llm:
        for attempt in range(MAX_RETRIES):
            model = (get_llm_model() if get_llm_model else llm_model)
            if model is None:
                break
            try:
                prompt = f"""Based on the following context, answer the question concisely and accurately.

Context: {combined_context[:MAX_CONTEXT_LENGTH]}

Question: {question}

Answer:"""
                response = model.invoke(prompt)
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


# Per-item result: (index, question, ground_truth, context_list, answer, status, duration_s, error_msg)
# status: "success" | "partial" | "failed" | "timeout"
ItemResult = Tuple[int, str, str, List[str], str, str, float, Optional[str]]
ResultsByIndex = Dict[int, Tuple[str, str, List[str], str, str, float, Optional[str]]]

# Index into the 7-tuple stored in results_by_index[i] (no index field in stored value)
_STATUS_IDX = 4
_PLACEHOLDER_CONTEXT = ["No relevant context found for this question."]
_PLACEHOLDER_ANSWER = "Unable to generate answer from available context."


def _status_display(status: str) -> str:
    """Human-readable status label for the per-item retrieval & generation step."""
    return {
        "success": "✅ OK",
        "partial": "⚠️ No context",
        "failed": "❌ Error",
        "timeout": "⏱️ Timeout",
    }.get(status, status)


def _report_rows_from_results(results_by_index: ResultsByIndex) -> List[Dict[str, Any]]:
    """Build report table rows from results_by_index for display in the UI."""
    rows = []
    for i in sorted(results_by_index.keys()):
        q, _gt, _ctx_list, _ans, status, dur, err = results_by_index[i]
        rows.append({
            "Index": i + 1,
            "Question": (q[:60] + "…") if len(q) > 60 else q,
            "Status": _status_display(status),
            "Duration (s)": f"{dur:.1f}",
            "Error": err or "",
        })
    return rows


def _placeholder_item_result(
    item: Dict[str, str],
    status: str,
    duration_sec: float,
    message: str,
) -> Tuple[str, str, List[str], str, str, float, Optional[str]]:
    """Build the 7-tuple value for a failed/timeout item (no index in stored value)."""
    return (
        str(item.get("question", "")),
        str(item.get("ground_truth", "")),
        _PLACEHOLDER_CONTEXT.copy(),
        _PLACEHOLDER_ANSWER,
        status,
        duration_sec,
        message,
    )


def _counts_by_status(results_by_index: ResultsByIndex, indices: List[int]) -> Dict[str, int]:
    """Return counts of success, partial, failed, timeout for the given indices."""
    counts = {"success": 0, "partial": 0, "failed": 0, "timeout": 0}
    for i in indices:
        status = results_by_index.get(i, ("", "", [], "", "timeout", 0.0, ""))[_STATUS_IDX]
        if status in counts:
            counts[status] += 1
    return counts


def _process_one_item(
    index: int,
    item: Dict[str, str],
    config: Tuple[str, str, str, str, str, str],
) -> ItemResult:
    """
    Process one test item (retrieval + answer generation). Runs in worker thread; no st.* or get_config.
    config = (api_url, bearer_token, tenant, kb_name, model_id, embedding_model_id).
    Returns: (index, question, ground_truth, context_list, answer, status, duration_s, error_msg).
    status: "success" | "partial" (retrieval failed) | "failed" (generation failed).
    """
    start = time.time()
    api_url, bearer_token, tenant, kb_name, model_id, _ = config
    question = str(item.get("question", "")).strip()
    ground_truth = str(item.get("ground_truth", "")).strip()
    retriever = SimpleAPIRetriever(
        api_url=api_url,
        bearer_token=bearer_token,
        tenant=tenant,
        knowledge_base_name=kb_name,
        model=extract_model_name_for_api(model_id),
    )
    context_list: List[str]
    status = "success"
    error_msg: Optional[str] = None
    try:
        documents = retriever.get_relevant_documents(question, silent=True)
        context_list = [doc.page_content for doc in documents if doc.page_content and doc.page_content.strip()]
        if not context_list:
            context_list = _PLACEHOLDER_CONTEXT.copy()
            status = "partial"
    except Exception as e:
        context_list = _PLACEHOLDER_CONTEXT.copy()
        status = "partial"
        error_msg = str(e)
        logger.warning(f"Item {index} retrieval failed: {e}")

    answer: str
    try:
        from langchain_aws import ChatBedrock
        model_config = get_model_config(model_id)
        kwargs = model_config["kwargs"].copy()
        if "max_tokens" in kwargs:
            kwargs["max_tokens"] = min(MAX_ANSWER_TOKENS, kwargs.get("max_tokens", MAX_ANSWER_TOKENS))
        elif "maxTokenCount" in kwargs:
            kwargs["maxTokenCount"] = min(MAX_ANSWER_TOKENS, kwargs.get("maxTokenCount", MAX_ANSWER_TOKENS))
        llm_model = ChatBedrock(region_name=AWS_REGION_NAME, model_id=model_id, model_kwargs=kwargs)
        answer = generate_answer_from_context(question, context_list, llm_model=llm_model)
        if not answer or not answer.strip():
            answer = _PLACEHOLDER_ANSWER
            if status != "partial":
                status = "failed"
    except Exception as e:
        answer = _PLACEHOLDER_ANSWER
        status = "failed"
        error_msg = _format_bedrock_error(e)
        if _is_expired_token(e):
            logger.error("Item %s: %s", index, EXPIRED_TOKEN_MESSAGE)
        else:
            logger.warning(f"Item {index} answer generation failed: {e}")

    duration = time.time() - start
    return (index, question, ground_truth, context_list, answer, status, duration, error_msg)


def _build_ragas_from_results(
    results_by_index: ResultsByIndex,
    indices: List[int],
    get_config: Callable[[], Tuple[str, str, str, str, str, str]],
) -> Tuple[Optional[Any], Optional[List[str]]]:
    """Build Dataset from results_by_index, run RAGAS evaluate, return (result, questions)."""
    questions_list = []
    answers_list = []
    contexts_list = []
    ground_truths_list = []
    for i in indices:
        q, gt, ctx_list, ans, _status, _dur, _err = results_by_index[i]
        questions_list.append(q)
        ground_truths_list.append(gt)
        contexts_list.append([str(c).strip() for c in ctx_list])
        answers_list.append(ans)

    from datasets import Dataset
    from langchain_aws import ChatBedrock
    from langchain_aws import BedrockEmbeddings
    from ragas import evaluate
    from ragas.metrics import faithfulness, context_recall, context_precision, answer_relevancy

    dataset = Dataset.from_dict({
        "question": questions_list,
        "answer": answers_list,
        "contexts": contexts_list,
        "ground_truth": ground_truths_list,
    })

    result = None
    for attempt in range(MAX_RETRIES):
        if _shutdown_requested:
            return None, None
        api_url, bearer_token, tenant, knowledge_base_name, model_id, embedding_model_id = get_config()
        model_config = get_model_config(model_id)
        try:
            bedrock_model = ChatBedrock(
                region_name=AWS_REGION_NAME,
                model_id=model_id,
                model_kwargs=model_config["kwargs"],
            )
            bedrock_embeddings = BedrockEmbeddings(
                region_name=AWS_REGION_NAME,
                model_id=embedding_model_id,
            )
            logger.info("RAGAS evaluate attempt %d/%d for %d items (4 metrics)…", attempt + 1, MAX_RETRIES, len(questions_list))
            result = evaluate(
                dataset,
                metrics=[faithfulness, context_recall, context_precision, answer_relevancy],
                llm=bedrock_model,
                embeddings=bedrock_embeddings,
                show_progress=False,
            )
            return result, questions_list
        except Exception as e:
            if _is_expired_token(e):
                logger.error(EXPIRED_TOKEN_MESSAGE)
                return None, None
            if attempt == MAX_RETRIES - 1:
                logger.error("Evaluation failed after %d attempts: %s", MAX_RETRIES, e, exc_info=True)
                return None, None
            logger.warning("Evaluation attempt %d failed (%s), retrying in %ds…", attempt + 1, e, EVALUATION_RETRY_DELAY)
            time.sleep(EVALUATION_RETRY_DELAY)
    return result, questions_list


_RAGAS_METRIC_NAMES = "faithfulness, context recall, context precision, answer relevancy"


def _start_ragas_scoring(
    results_by_index: ResultsByIndex,
    indices: List[int],
    get_config: Callable[[], Tuple[str, str, str, str, str, str]],
) -> None:
    """Launch RAGAS scoring in a background thread, storing the future in session state."""
    from concurrent.futures import ThreadPoolExecutor as _TPE
    executor = _TPE(max_workers=1)
    future = executor.submit(_build_ragas_from_results, results_by_index, indices, get_config)
    st.session_state.ragas_scoring_future = future
    st.session_state.ragas_scoring_executor = executor
    st.session_state.ragas_scoring_start = time.time()
    st.session_state.ragas_eval_stage = "scoring"
    logger.info("Started RAGAS scoring in background thread for %d items", len(indices))


def _clear_ragas_eval_state() -> None:
    executor = st.session_state.pop("ragas_scoring_executor", None)
    if executor is not None:
        try:
            executor.shutdown(wait=False)
        except Exception:
            pass
    for key in (
        "ragas_eval_phase", "ragas_eval_pending", "ragas_eval_results",
        "ragas_eval_test_data", "ragas_eval_stopped",
        "ragas_eval_start_time", "ragas_eval_stage",
        "ragas_scoring_future", "ragas_scoring_start",
    ):
        st.session_state.pop(key, None)


def run_ragas_evaluation(
    test_data: List[Dict[str, str]],
    get_config: Callable[[], Tuple[str, str, str, str, str, str]],
) -> Tuple[Optional[Any], Optional[List[str]], Optional[str]]:
    """
    Run RAGAS evaluation on test data with parallel per-item processing.
    Uses get_config() at the start of each batch so credentials are fresh. Each item is
    processed (retrieval + answer generation) in a worker; all items are fulfilled
    (placeholders used on failure). A live report is shown on the UI.
    Returns (result, questions, status) where status is None (complete), "in_progress", or "partial_stopped".
    """
    n_total = len(test_data)
    if n_total == 0:
        st.error("No test data to evaluate")
        return None, None, None

    # Use UI overrides if set, else config defaults
    max_workers_cfg = max(1, min(
        st.session_state.get("sidebar_max_workers", MAX_WORKERS),
        64,
    ))
    item_timeout_sec = max(10, min(st.session_state.get("sidebar_item_timeout", ITEM_TIMEOUT), 600))
    max_workers = max(1, min(max_workers_cfg, n_total))

    # ----- Chunked mode: resume from session state and allow Stop from UI -----
    if st.session_state.get("ragas_eval_phase") == "running":
        pending = list(st.session_state.get("ragas_eval_pending") or [])
        results_by_index = dict(st.session_state.get("ragas_eval_results") or {})
        test_data = st.session_state.get("ragas_eval_test_data") or test_data
        stopped = st.session_state.get("ragas_eval_stopped", False)

        # Track wall-clock start so we can show elapsed time on the UI
        if "ragas_eval_start_time" not in st.session_state:
            st.session_state.ragas_eval_start_time = time.time()

        # Separate single-element placeholders to avoid stacking from .container()
        activity_placeholder = st.empty()
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        report_header_placeholder = st.empty()
        report_table_placeholder = st.empty()

        def _update_progress_ui(completed_count: int, activity: str, stage_detail: str = "") -> None:
            """Refresh activity headline, progress bar, and status line."""
            frac = completed_count / n_total if n_total else 0
            elapsed = time.time() - st.session_state.get("ragas_eval_start_time", time.time())
            mins, secs = divmod(int(elapsed), 60)
            counts = _counts_by_status(results_by_index, list(results_by_index.keys()))
            parts = [f"**{completed_count} / {n_total}** items"]
            detail_parts = []
            if counts["success"]:
                detail_parts.append(f"✅ {counts['success']} OK")
            if counts["partial"]:
                detail_parts.append(f"⚠️ {counts['partial']} no context")
            if counts["failed"]:
                detail_parts.append(f"❌ {counts['failed']} errors")
            if counts["timeout"]:
                detail_parts.append(f"⏱️ {counts['timeout']} timed out")
            if detail_parts:
                parts.append(" · ".join(detail_parts))
            parts.append(f"⏱ Elapsed: {mins}m {secs:02d}s")
            if stage_detail:
                parts.append(stage_detail)
            activity_placeholder.markdown(f"### {activity}")
            progress_placeholder.progress(frac)
            status_placeholder.caption(" &nbsp;|&nbsp; ".join(parts))

        def _show_report_table(results: ResultsByIndex) -> None:
            """Render the per-item report into separate header + table placeholders."""
            if not results:
                return
            report_header_placeholder.markdown("**Step 1 of 2 — Retrieval & Answer Generation**")
            report_table_placeholder.dataframe(
                _report_rows_from_results(results),
                width="stretch",
                height=min(400, 50 * len(results)),
            )

        # Immediately render current progress from session state so the UI is never blank after a rerun
        if results_by_index and not stopped:
            completed = len(results_by_index)
            remaining_count = len(pending)
            current_stage = st.session_state.get("ragas_eval_stage", "")
            if current_stage == "scoring":
                scoring_elapsed = int(time.time() - st.session_state.get("ragas_scoring_start", time.time()))
                s_mins, s_secs = divmod(scoring_elapsed, 60)
                _update_progress_ui(
                    completed,
                    f"Step 2 of 2 — RAGAS Scoring in progress… ({s_mins}m {s_secs:02d}s)",
                    f"Metrics: {_RAGAS_METRIC_NAMES}",
                )
            elif pending:
                _update_progress_ui(
                    completed,
                    f"Step 1 of 2 — Retrieving & generating answers… ({remaining_count} remaining)",
                )
            else:
                _update_progress_ui(completed, "All items processed — preparing RAGAS scoring…")
            _show_report_table(results_by_index)

        # ----- Scoring stage: RAGAS metrics running in background thread -----
        if st.session_state.get("ragas_eval_stage") == "scoring":
            future = st.session_state.get("ragas_scoring_future")
            scoring_start = st.session_state.get("ragas_scoring_start", time.time())
            scoring_elapsed = int(time.time() - scoring_start)
            s_mins, s_secs = divmod(scoring_elapsed, 60)
            is_partial = st.session_state.get("ragas_eval_stopped", False)

            if future is not None and future.done():
                # Clear the in-place heartbeat line before logging the completion message
                sys.stderr.write("\r" + " " * 100 + "\r")
                sys.stderr.flush()
                try:
                    result, questions = future.result()
                except Exception as exc:
                    logger.error("RAGAS scoring failed: %s", exc, exc_info=True)
                    st.error(f"RAGAS metric computation failed: {exc}")
                    _clear_ragas_eval_state()
                    return None, None, None
                if result is not None:
                    counts = _counts_by_status(results_by_index, sorted(results_by_index.keys()))
                    logger.info("RAGAS scoring complete in %dm %02ds — %d OK, %d partial, %d failed, %d timeout",
                                s_mins, s_secs, counts["success"], counts["partial"], counts["failed"], counts["timeout"])
                else:
                    st.error("RAGAS metric computation failed. Check the console for details.")
                _clear_ragas_eval_state()
                return (result, questions, "partial_stopped" if is_partial else None)

            # Still running — overwrite the same console line with updated elapsed time
            n_items = len(results_by_index)
            sys.stderr.write(
                f"\rINFO: RAGAS scoring ({_RAGAS_METRIC_NAMES}) — {n_items} items — {s_mins}m {s_secs:02d}s elapsed"
            )
            sys.stderr.flush()
            time.sleep(3)
            return None, None, "in_progress"

        if stopped:
            if not results_by_index:
                st.warning("Evaluation stopped by user. No items had completed yet.")
                _clear_ragas_eval_state()
                return None, None, "partial_stopped"
            indices_done = sorted(results_by_index.keys())
            completed = len(indices_done)
            if st.session_state.get("ragas_eval_stage") != "scoring":
                _update_progress_ui(completed, "Stopped — starting RAGAS scoring for partial results…")
                _show_report_table(results_by_index)
                _start_ragas_scoring(results_by_index, indices_done, get_config)
                st.session_state.ragas_eval_stopped = True
                return None, None, "in_progress"
            # scoring already running — handled below in the scoring-stage block

        if not pending:
            # All items done in previous chunks — do timeout retries then RAGAS
            indices = list(range(n_total))
            timeout_indices = [i for i in indices if results_by_index.get(i, ("", "", [], "", "timeout", 0.0, ""))[_STATUS_IDX] == "timeout"]
            if timeout_indices and not _shutdown_requested:
                retry_timeout_sec = item_timeout_sec * 2
                _update_progress_ui(
                    len(results_by_index),
                    f"Retrying {len(timeout_indices)} timed-out item(s) (timeout {retry_timeout_sec}s)…",
                )
                logger.info("Retrying %d timed-out items with %ds timeout", len(timeout_indices), retry_timeout_sec)
                config = get_config()
                with ThreadPoolExecutor(max_workers=min(max_workers, len(timeout_indices))) as executor:
                    futures = {
                        executor.submit(_process_one_item, i, test_data[i], config): i
                        for i in timeout_indices
                    }
                    for future in futures:
                        if _shutdown_requested:
                            st.warning("Stopped by user (Ctrl+C).")
                            result, qs = _build_ragas_from_results(results_by_index, sorted(results_by_index.keys()), get_config)
                            _clear_ragas_eval_state()
                            return (result, qs, "partial_stopped")
                        idx = futures[future]
                        try:
                            remaining = retry_timeout_sec
                            outcome = None
                            while remaining > 0:
                                if _shutdown_requested:
                                    result, qs = _build_ragas_from_results(results_by_index, sorted(results_by_index.keys()), get_config)
                                    _clear_ragas_eval_state()
                                    return (result, qs, "partial_stopped")
                                chunk = min(3, remaining)
                                try:
                                    outcome = future.result(timeout=chunk)
                                    break
                                except FuturesTimeoutError:
                                    remaining -= chunk
                            if outcome is not None:
                                (_i, question, ground_truth, context_list, answer, status, duration, error_msg) = outcome
                                results_by_index[idx] = (question, ground_truth, context_list, answer, status, duration, error_msg)
                        except FuturesTimeoutError:
                            logger.warning("Item %d timed out again after %ds", idx, retry_timeout_sec)
                        except Exception as exc:
                            logger.exception("Item %d failed on retry: %s", idx, exc)

            indices = sorted(results_by_index.keys())
            if not indices:
                st.error("No valid data generated for evaluation")
                _clear_ragas_eval_state()
                return None, None, None
            if st.session_state.get("ragas_eval_stage") != "scoring":
                _update_progress_ui(
                    len(results_by_index),
                    "All items processed — starting RAGAS scoring…",
                )
                _start_ragas_scoring(results_by_index, indices, get_config)
                return None, None, "in_progress"
            # scoring already running — handled below in the scoring-stage block

        # Run for up to TIMESLICE_SEC seconds, then return so UI can process Stop
        TIMESLICE_SEC = 8
        slice_start = time.time()
        while pending and (time.time() - slice_start) < TIMESLICE_SEC:
            if _shutdown_requested:
                indices_done = sorted(results_by_index.keys())
                if indices_done:
                    result, qs = _build_ragas_from_results(results_by_index, indices_done, get_config)
                    _clear_ragas_eval_state()
                    return (result, qs, "partial_stopped")
                _clear_ragas_eval_state()
                return None, None, "partial_stopped"
            batch_indices = pending[:max_workers]
            pending = pending[max_workers:]
            config = get_config()
            with ThreadPoolExecutor(max_workers=len(batch_indices)) as executor:
                futures = {
                    executor.submit(_process_one_item, i, test_data[i], config): i
                    for i in batch_indices
                }
                for future in futures:
                    if _shutdown_requested:
                        break
                    idx = futures[future]
                    try:
                        remaining = item_timeout_sec
                        outcome = None
                        while remaining > 0 and not _shutdown_requested:
                            chunk = min(3, remaining)
                            try:
                                outcome = future.result(timeout=chunk)
                                break
                            except FuturesTimeoutError:
                                remaining -= chunk
                        if outcome is None:
                            raise FuturesTimeoutError()
                        (_i, question, ground_truth, context_list, answer, status, duration, error_msg) = outcome
                        results_by_index[idx] = (question, ground_truth, context_list, answer, status, duration, error_msg)
                    except FuturesTimeoutError:
                        results_by_index[idx] = _placeholder_item_result(
                            test_data[idx], "timeout", float(item_timeout_sec),
                            f"Item did not complete within {item_timeout_sec}s",
                        )
                    except Exception as e:
                        results_by_index[idx] = _placeholder_item_result(
                            test_data[idx], "failed", 0.0, str(e),
                        )

            completed = len(results_by_index)
            remaining_count = len(pending)
            _update_progress_ui(
                completed,
                f"Step 1 of 2 — Retrieving & generating answers… ({remaining_count} remaining)",
            )
            _show_report_table(results_by_index)
            logger.info("Batch complete — %d/%d items done, %d remaining", completed, n_total, remaining_count)
            st.session_state.ragas_eval_pending = pending
            st.session_state.ragas_eval_results = results_by_index

        # Return in_progress so UI auto-reruns and shows Stop button
        return None, None, "in_progress"

    # If we reach here, ragas_eval_phase was not "running" — should not happen
    # since the UI always sets it before calling this function.
    st.error("Unexpected state: evaluation was called without initializing chunked mode.")
    return None, None, None

def test_api_connection(api_url: str, bearer_token: str, tenant: str, 
                       knowledge_base_name: str, model: str = None) -> Dict[str, Any]:
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
    if model is None:
        model = DEFAULT_API_MODEL_NAME
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
            except Exception:
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
        from langchain_aws import ChatBedrock
        from langchain_aws import BedrockEmbeddings
        model_config = get_model_config(model_id)
        start_time = time.time()
        llm_model = ChatBedrock(
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
        err_msg = _format_bedrock_error(e)
        llm_test["error"] = err_msg
        result["details"]["llm"] = {
            "model_id": model_id,
            "status": "❌ Failed",
            "error": err_msg[:200]
        }
        if _is_expired_token(e):
            logger.error("LLM test: %s", EXPIRED_TOKEN_MESSAGE)
        else:
            logger.error(f"LLM test error: {e}", exc_info=True)
    
    # Test Embedding connection (BedrockEmbeddings imported above)
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
        err_msg = _format_bedrock_error(e)
        embedding_test["error"] = err_msg
        result["details"]["embedding"] = {
            "model_id": embedding_model_id,
            "status": "❌ Failed",
            "error": err_msg[:200]
        }
        if _is_expired_token(e):
            logger.error("Embedding test: %s", EXPIRED_TOKEN_MESSAGE)
        else:
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
    
    st.title("RAGAS Evaluation Tool")
    ui = StreamlitUI()
    ui.render_sidebar()
    test_data = ui.render_file_upload()
    
    # So evaluation and retries always read fresh bearer token / AWS credentials from UI
    def get_config():
        return (
            st.session_state.get("sidebar_api_url", ""),
            st.session_state.get("sidebar_bearer_token", ""),
            st.session_state.get("sidebar_tenant", ""),
            st.session_state.get("sidebar_kb_name", ""),
            st.session_state.get("sidebar_model_id", ""),
            st.session_state.get("sidebar_embedding_id", ""),
        )
    
    if test_data:
        ui.render_evaluation_section(test_data, get_config, run_ragas_evaluation)