"""
Streamlit UI components for RAGAS Evaluation Tool
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Callable, Any
import io
from config import (
    DEFAULT_API_URL,
    DEFAULT_TENANT,
    DEFAULT_KB_NAME,
    DEFAULT_LLM_MODEL_ID,
    DEFAULT_EMBEDDING_MODEL_ID,
    MAX_WORKERS as DEFAULT_MAX_WORKERS,
    ITEM_TIMEOUT as DEFAULT_ITEM_TIMEOUT,
)
from model_config import SUPPORTED_LLM_MODEL_IDS, SUPPORTED_EMBEDDINGS

class StreamlitUI:
    """UI components for the RAGAS evaluation tool"""
    def __init__(self):
        self.api_url = DEFAULT_API_URL
        self.tenant = DEFAULT_TENANT
        self.knowledge_base_name = DEFAULT_KB_NAME
       
    def render_sidebar(self):
        st.sidebar.header("⚙️ Configuration")
        
        # Initialize session state for form values if not present
        _sidebar_defaults = {
            "sidebar_api_url": self.api_url,
            "sidebar_bearer_token": "",
            "sidebar_tenant": self.tenant,
            "sidebar_kb_name": self.knowledge_base_name,
            "sidebar_model_id": DEFAULT_LLM_MODEL_ID,
            "sidebar_embedding_id": DEFAULT_EMBEDDING_MODEL_ID,
            "sidebar_max_workers": DEFAULT_MAX_WORKERS,
            "sidebar_item_timeout": DEFAULT_ITEM_TIMEOUT,
        }
        for key, default in _sidebar_defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default

        api_url = st.sidebar.text_input("API URL", value=st.session_state.sidebar_api_url, key="sidebar_api_url_input")
        bearer_token = st.sidebar.text_input("Bearer Token", type="password", value=st.session_state.sidebar_bearer_token, key="sidebar_bearer_token_input")
        tenant = st.sidebar.text_input("Tenant", value=st.session_state.sidebar_tenant, key="sidebar_tenant_input")
        knowledge_base_name = st.sidebar.text_input("Knowledge Base Name", value=st.session_state.sidebar_kb_name, key="sidebar_kb_name_input")
        
        llm_options = SUPPORTED_LLM_MODEL_IDS
        try:
            model_index = llm_options.index(st.session_state.sidebar_model_id) if st.session_state.sidebar_model_id in llm_options else 0
        except ValueError:
            model_index = 0
        model_id = st.sidebar.selectbox(
            "LLM Model",
            llm_options,
            index=model_index,
            key="sidebar_model_id_select"
        )
        
        embedding_options = SUPPORTED_EMBEDDINGS
        try:
            emb_index = embedding_options.index(st.session_state.sidebar_embedding_id) if st.session_state.sidebar_embedding_id in embedding_options else 0
        except ValueError:
            emb_index = 0
        embedding_model_id = st.sidebar.selectbox(
            "Embedding Model",
            embedding_options,
            index=emb_index,
            key="sidebar_embedding_id_select"
        )
        
        # Evaluation options (parallelism and timeout)
        with st.sidebar.expander("⚡ Evaluation options", expanded=False):
            max_workers = st.number_input(
                "Max parallel items",
                min_value=1,
                max_value=64,
                value=st.session_state.sidebar_max_workers,
                step=1,
                help="Number of questions processed in parallel (1–64). Higher values speed up runs but may hit rate limits.",
                key="sidebar_max_workers_input",
            )
            item_timeout = st.number_input(
                "Per-item timeout (seconds)",
                min_value=10,
                max_value=600,
                value=st.session_state.sidebar_item_timeout,
                step=10,
                help="Max seconds per question (retrieval + answer). Slow items are retried once with 2× this timeout.",
                key="sidebar_item_timeout_input",
            )
            st.session_state.sidebar_max_workers = max_workers
            st.session_state.sidebar_item_timeout = item_timeout
        
        # Update session state with current values
        st.session_state.sidebar_api_url = api_url
        st.session_state.sidebar_bearer_token = bearer_token
        st.session_state.sidebar_tenant = tenant
        st.session_state.sidebar_kb_name = knowledge_base_name
        st.session_state.sidebar_model_id = model_id
        st.session_state.sidebar_embedding_id = embedding_model_id
       
        # Connection Testing Section
        self._render_connection_tests(api_url, bearer_token, tenant, knowledge_base_name, model_id, embedding_model_id)
       
        self._render_instructions()
       
        return api_url, bearer_token, tenant, knowledge_base_name, model_id, embedding_model_id
   
    def render_file_upload(self) -> Optional[List[Dict[str, str]]]:
        """
        Render file upload component for test plan CSV.
        User can select which columns to use as question and ground_truth if names differ.
        Returns:
            List of dicts with keys 'question' and 'ground_truth' for evaluation.
        """
        st.header("1. Upload Test Plan")
        st.info("📄 Upload a CSV with at least two columns. Choose which column is the **question** and which is the **ground truth**.")
        uploaded_file = st.file_uploader("Choose CSV file", type=["csv"], help="CSV with your test cases")
       
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                if len(df) == 0:
                    st.warning("⚠️ CSV has no rows. Upload a file with at least one row.")
                    return None
                # Normalize column names: strip and lowercase for flexible matching
                df.columns = df.columns.str.strip().str.lower()
                cols = df.columns.tolist()
                if len(cols) < 2:
                    st.error("❌ CSV must have at least two columns (e.g. question and answer/ground truth).")
                    return None
                st.success(f"✅ Loaded {len(df)} rows from {uploaded_file.name}")
                st.dataframe(df.head(), width="stretch")

                # Column mapping: default to 'question' / 'ground_truth' if present
                default_question = "question" if "question" in cols else cols[0]
                default_ground_truth = "ground_truth" if "ground_truth" in cols else (cols[1] if len(cols) > 1 else cols[0])
                # Persist selection per file so it doesn’t reset on rerun
                file_key = f"{uploaded_file.name}_{len(df)}"
                session_q = st.session_state.get("ragas_question_col", {}).get(file_key, default_question)
                session_gt = st.session_state.get("ragas_ground_truth_col", {}).get(file_key, default_ground_truth)
                if session_q not in cols:
                    session_q = default_question
                if session_gt not in cols:
                    session_gt = default_ground_truth

                st.markdown("**Map columns to evaluation fields:**")
                c1, c2 = st.columns(2)
                # Key by file so column selection is per-file when user switches files
                widget_suffix = file_key.replace(" ", "_")
                with c1:
                    question_col = st.selectbox(
                        "Question column",
                        options=cols,
                        index=cols.index(session_q) if session_q in cols else 0,
                        key=f"file_question_col_{widget_suffix}",
                    )
                with c2:
                    ground_truth_col = st.selectbox(
                        "Ground truth column",
                        options=cols,
                        index=cols.index(session_gt) if session_gt in cols else min(1, len(cols) - 1),
                        key=f"file_ground_truth_col_{widget_suffix}",
                    )
                if question_col == ground_truth_col:
                    st.warning("⚠️ Question and ground truth columns are the same. Consider selecting different columns.")
                # Store selection for this file
                if "ragas_question_col" not in st.session_state:
                    st.session_state.ragas_question_col = {}
                if "ragas_ground_truth_col" not in st.session_state:
                    st.session_state.ragas_ground_truth_col = {}
                st.session_state.ragas_question_col[file_key] = question_col
                st.session_state.ragas_ground_truth_col[file_key] = ground_truth_col

                # Build test_data with canonical keys 'question' and 'ground_truth'
                df_mapped = df[[question_col, ground_truth_col]].copy()
                df_mapped = df_mapped.rename(columns={question_col: "question", ground_truth_col: "ground_truth"})
                if df_mapped["question"].isna().any() or df_mapped["ground_truth"].isna().any():
                    st.warning("⚠️ Some rows have empty question or ground_truth values. They will still be included.")
                st.session_state.ragas_current_file_id = file_key
                return df_mapped.to_dict("records")
            except Exception as e:
                st.error(f"❌ Error reading CSV file: {e}")
                st.info("Please ensure the file is a valid CSV format.")
                return None
       
        # No file selected: clear file id so stored results are not tied to a previous file
        if "ragas_current_file_id" in st.session_state:
            del st.session_state["ragas_current_file_id"]
        return None
   
    def render_evaluation_section(
        self,
        test_data: List[Dict[str, str]],
        get_config: Callable[[], Tuple[str, str, str, str, str, str]],
        evaluation_func,
    ) -> None:
        """
        Render evaluation section with start button.
        get_config() returns (api_url, bearer_token, tenant, kb_name, model_id, embedding_id)
        so evaluation can read fresh credentials/token on each use and retry.
        evaluation_func returns (result, questions, status) with status None | "in_progress" | "partial_stopped".
        """
        st.header("2. Run Evaluation")
        n_total = len(test_data)
        current_file_id = st.session_state.get("ragas_current_file_id")

        # Clear stored results if user loaded a different file
        last_file_id = st.session_state.get("ragas_last_result_file_id")
        if last_file_id is not None and current_file_id is not None and last_file_id != current_file_id:
            for key in ("ragas_last_result_df", "ragas_last_result_meta", "ragas_last_result_file_id"):
                st.session_state.pop(key, None)
            last_file_id = None

        # Show retained results from last run (same file still loaded) until user loads a new file
        if last_file_id is not None and current_file_id == last_file_id and "ragas_last_result_df" in st.session_state:
            stored_df = st.session_state.ragas_last_result_df
            meta = st.session_state.get("ragas_last_result_meta") or {}
            self._render_stored_results(stored_df, meta)
            return

        # Evaluation in progress (chunked mode): auto-run next batch, show Stop button
        if st.session_state.get("ragas_eval_phase") == "running":
            eval_results = st.session_state.get("ragas_eval_results") or {}
            eval_stopped = st.session_state.get("ragas_eval_stopped", False)
            eval_test_data = st.session_state.get("ragas_eval_test_data") or test_data
            eval_stage = st.session_state.get("ragas_eval_stage", "")

            # Show Stop button only during item processing (not during RAGAS scoring)
            if eval_stage != "scoring" and not eval_stopped:
                if st.button("⏹️ Stop evaluation", key="eval_stop_btn"):
                    st.session_state.ragas_eval_stopped = True
                    st.rerun()

            try:
                result, _eval_data, status = evaluation_func(eval_test_data, get_config)
                if status == "in_progress":
                    st.rerun()
                elif status == "partial_stopped" and result is not None:
                    _, _, _, kb_name, mid, emb_id = get_config()
                    self._render_results(result, kb_name, mid, emb_id, partial=True)
                elif status is None and result is not None:
                    _, _, _, kb_name, mid, emb_id = get_config()
                    self._render_results(result, kb_name, mid, emb_id)
                elif status == "partial_stopped":
                    st.warning("Evaluation stopped by user. No items had completed yet.")
            except Exception as e:
                st.error(f"❌ Evaluation failed: {e}")
                st.exception(e)
            return

        st.info(f"📊 Ready to evaluate {n_total} test cases")

        if st.button("🚀 Start RAGAS Evaluation", type="primary"):
            api_url, bearer_token, tenant, knowledge_base_name, model_id, embedding_model_id = get_config()
            if not all([api_url, bearer_token, tenant, knowledge_base_name]):
                missing = [field for field, value in zip(
                    ["API URL", "Bearer Token", "Tenant", "Knowledge Base Name"],
                    [api_url, bearer_token, tenant, knowledge_base_name]
                ) if not value]
                st.error(f"❌ Please fill in all configuration fields. Missing: {', '.join(missing)}")
                return

            # Start chunked evaluation: set state so first run enters chunked mode
            st.session_state.ragas_eval_phase = "running"
            st.session_state.ragas_eval_pending = list(range(n_total))
            st.session_state.ragas_eval_results = {}
            st.session_state.ragas_eval_test_data = test_data
            st.session_state.ragas_eval_stopped = False

            try:
                result, _eval_data, status = evaluation_func(test_data, get_config)
                if status == "in_progress":
                    st.rerun()
                elif result is not None:
                    _, _, _, kb_name, mid, emb_id = get_config()
                    self._render_results(result, kb_name, mid, emb_id, partial=(status == "partial_stopped"))
                elif status == "partial_stopped":
                    st.warning("Evaluation stopped by user. No completed items to show.")
                else:
                    st.error("❌ Evaluation completed but no results were generated.")
            except Exception as e:
                st.error(f"❌ Evaluation failed: {e}")
                st.exception(e)

    def _render_results(self, result, knowledge_base_name, model_id, embedding_model_id, partial: bool = False):
        """Build results DataFrame from RAGAS result, persist to session state, then render download + table."""
        # Clear chunked-eval state so it doesn't persist into the next rerun
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_df = result.to_pandas().copy()
        results_df["evaluation_timestamp"] = timestamp
        results_df["knowledge_base_name"] = knowledge_base_name
        results_df["model_id"] = model_id
        results_df["embedding_model_id"] = embedding_model_id
        meta = {
            "partial": partial,
            "knowledge_base_name": knowledge_base_name,
            "model_id": model_id,
            "embedding_model_id": embedding_model_id,
            "timestamp": timestamp,
        }
        st.session_state.ragas_last_result_df = results_df
        st.session_state.ragas_last_result_meta = meta
        st.session_state.ragas_last_result_file_id = st.session_state.get("ragas_current_file_id")
        self._render_results_ui(results_df, meta)

    def _render_results_ui(self, results_df: pd.DataFrame, meta: Dict[str, Any]) -> None:
        """Render success/partial message, download button, and results table (shared by fresh and stored results)."""
        partial = meta.get("partial", False)
        if partial:
            st.warning(
                "⏹️ **Evaluation stopped by user.** Partial results are shown below. "
                "You can download the evaluation file with whatever was evaluated up to that point."
            )
        else:
            st.success("Evaluation completed!")
        st.header("3. Download Results")
        kb_name = meta.get("knowledge_base_name", "")
        timestamp = meta.get("timestamp", datetime.now().strftime("%Y%m%d_%H%M%S"))
        suffix = "_partial" if partial else ""
        filename = f"ragas_evaluation_{kb_name}_{timestamp}{suffix}.csv"
        csv_buffer = io.StringIO()
        results_df.to_csv(csv_buffer, index=False)
        st.download_button(
            "Download Results CSV",
            csv_buffer.getvalue(),
            filename,
            "text/csv",
            key="download_ragas_results_csv",
        )
        st.info(f"Results saved with {len(results_df)} evaluations")
        st.dataframe(results_df)

    def _render_stored_results(self, stored_df: pd.DataFrame, meta: Dict[str, Any]) -> None:
        """Render results UI from stored session state (retained until user loads a new file)."""
        self._render_results_ui(stored_df, meta)
   
    def _render_connection_tests(self, api_url: str, bearer_token: str, tenant: str,
                                 knowledge_base_name: str, model_id: str, embedding_model_id: str) -> None:
        """Render connection test buttons and results panel"""
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔌 Connection Tests")
        st.sidebar.info("Test connections before running evaluation")
        
        # Test API Connection
        if st.sidebar.button("🧪 Test API Connection", key="test_api_btn"):
            if not all([api_url, bearer_token, tenant, knowledge_base_name]):
                st.sidebar.error("❌ Please fill in API URL, Bearer Token, Tenant, and Knowledge Base Name")
            else:
                with st.spinner("Testing API connection..."):
                    # Show only this test result (clear Bedrock result)
                    if 'bedrock_test_result' in st.session_state:
                        del st.session_state['bedrock_test_result']
                    original_flag = getattr(st, '_ragas_skip_ui', False)
                    st._ragas_skip_ui = True
                    try:
                        from streamlit_ragas_eval import test_api_connection, extract_model_name_for_api
                        api_model_name = extract_model_name_for_api(model_id)
                        result = test_api_connection(api_url, bearer_token, tenant, knowledge_base_name, api_model_name)
                        st.session_state['api_test_result'] = result
                    finally:
                        st._ragas_skip_ui = original_flag
        
        # Test Bedrock Connection
        if st.sidebar.button("🧪 Test Bedrock Connection", key="test_bedrock_btn"):
            with st.spinner("Testing Bedrock connection..."):
                # Show only this test result (clear API result)
                if 'api_test_result' in st.session_state:
                    del st.session_state['api_test_result']
                original_flag = getattr(st, '_ragas_skip_ui', False)
                st._ragas_skip_ui = True
                try:
                    from streamlit_ragas_eval import test_bedrock_connection
                    result = test_bedrock_connection(model_id, embedding_model_id)
                    st.session_state['bedrock_test_result'] = result
                finally:
                    st._ragas_skip_ui = original_flag
        
        # Display test results (only one at a time: whichever test was run last)
        if 'api_test_result' in st.session_state or 'bedrock_test_result' in st.session_state:
            st.sidebar.markdown("---")
            with st.sidebar.expander("📊 Test Results", expanded=True):
                # API Test Results
                if 'api_test_result' in st.session_state:
                    api_result = st.session_state['api_test_result']
                    if api_result['success']:
                        st.success(api_result['message'])
                    else:
                        st.error(api_result['message'])
                    
                    st.markdown("**API Details:**")
                    for key, value in api_result.get('details', {}).items():
                        st.text(f"  • {key}: {value if isinstance(value, str) else str(value)}")
                    
                    if api_result.get('error'):
                        with st.expander("Error Details"):
                            st.code(api_result['error'], language='text')
                    st.caption(f"Tested at: {api_result['timestamp']}")
                
                # Bedrock Test Results
                if 'bedrock_test_result' in st.session_state:
                    bedrock_result = st.session_state['bedrock_test_result']
                    if bedrock_result['success']:
                        st.success(bedrock_result['message'])
                    else:
                        st.error(bedrock_result['message'])
                    
                    st.markdown("**Bedrock Details:**")
                    if 'llm' in bedrock_result.get('details', {}):
                        llm_info = bedrock_result['details']['llm']
                        status_icon = "✅" if "Connected" in llm_info['status'] else "❌"
                        st.markdown(f"  • LLM: {status_icon} {llm_info['model_id']}")
                        if 'init_time' in llm_info:
                            st.text(f"    Init time: {llm_info['init_time']}")
                        if 'error' in llm_info:
                            st.text(f"    Error: {llm_info['error']}")
                    
                    if 'embedding' in bedrock_result.get('details', {}):
                        emb_info = bedrock_result['details']['embedding']
                        status_icon = "✅" if "Connected" in emb_info['status'] else "❌"
                        st.markdown(f"  • Embedding: {status_icon} {emb_info['model_id']}")
                        if 'init_time' in emb_info:
                            st.text(f"    Init time: {emb_info['init_time']}")
                        if 'error' in emb_info:
                            st.text(f"    Error: {emb_info['error']}")
                    
                    if bedrock_result.get('error'):
                        with st.expander("Error Details"):
                            st.code(bedrock_result['error'], language='text')
                    
                    st.caption(f"Tested at: {bedrock_result['timestamp']}")
    
    def _render_instructions(self):
        st.sidebar.markdown("---")
        with st.sidebar.expander("📋 Instructions"):
            st.markdown("""
            1. Upload Test Plan (CSV), then choose question and ground truth columns
            2. Configure API settings and models
            3. Run evaluation
            4. Download results (csv) with timestamp
            """)
       
        with st.sidebar.expander("📊 Metric Definitions"):
            st.markdown("""
            **Faithfulness** (0-1)  
            Measures if the answer is factually consistent with the given context. Higher is better.
           
            **Context Recall** (0-1)  
            Measures how much of the ground truth can be attributed to the retrieved context. Higher is better.
           
            **Context Precision** (0-1)  
            Measures how relevant the retrieved contexts are to the question. Higher is better.
           
            **Answer Relevancy** (0-1)  
            Measures how relevant the generated answer is to the question. Higher is better.
            """)