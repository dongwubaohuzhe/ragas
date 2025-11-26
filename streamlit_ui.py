"""
Streamlit UI components for RAGAS Evaluation Tool
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Tuple
import io
from config import DEFAULT_API_URL, DEFAULT_TENANT, DEFAULT_KB_NAME

class StreamlitUI:
    """UI components for the RAGAS evaluation tool"""
    def __init__(self):
        self.api_url = DEFAULT_API_URL
        self.tenant = DEFAULT_TENANT
        self.knowledge_base_name = DEFAULT_KB_NAME
       
    def render_sidebar(self):
        st.sidebar.header("⚙️ Configuration")
        
        # Initialize session state for form values if not present
        if 'sidebar_api_url' not in st.session_state:
            st.session_state.sidebar_api_url = self.api_url
        if 'sidebar_bearer_token' not in st.session_state:
            st.session_state.sidebar_bearer_token = ""
        if 'sidebar_tenant' not in st.session_state:
            st.session_state.sidebar_tenant = self.tenant
        if 'sidebar_kb_name' not in st.session_state:
            st.session_state.sidebar_kb_name = self.knowledge_base_name
        if 'sidebar_model_id' not in st.session_state:
            st.session_state.sidebar_model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
        if 'sidebar_embedding_id' not in st.session_state:
            st.session_state.sidebar_embedding_id = "amazon.titan-embed-text-v2:0"
        
        api_url = st.sidebar.text_input("API URL", value=st.session_state.sidebar_api_url, key="sidebar_api_url_input")
        bearer_token = st.sidebar.text_input("Bearer Token", type="password", value=st.session_state.sidebar_bearer_token, key="sidebar_bearer_token_input")
        tenant = st.sidebar.text_input("Tenant", value=st.session_state.sidebar_tenant, key="sidebar_tenant_input")
        knowledge_base_name = st.sidebar.text_input("Knowledge Base Name", value=st.session_state.sidebar_kb_name, key="sidebar_kb_name_input")
        
        model_id = st.sidebar.selectbox(
            "LLM Model",
            ["anthropic.claude-3-5-sonnet-20240620-v1:0","anthropic.claude-3-7-sonnet-20250219-v1:0","amazon.titan-text-express-v1"],
            index=0 if st.session_state.sidebar_model_id == "anthropic.claude-3-5-sonnet-20240620-v1:0" else (1 if st.session_state.sidebar_model_id == "anthropic.claude-3-7-sonnet-20250219-v1:0" else 2),
            key="sidebar_model_id_select"
        )
        
        embedding_model_id = st.sidebar.selectbox(
            "Embedding Model",
            ["amazon.titan-embed-text-v2:0"],
            key="sidebar_embedding_id_select"
        )
        
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
        Render file upload component for test plan CSV
        
        Returns:
            List of dictionaries with test data or None
        """
        st.header("1. Upload Test Plan")
        st.info("📄 CSV Format: Must contain 'question' and 'ground_truth' columns")
        uploaded_file = st.file_uploader("Choose CSV file", type=["csv"], help="Upload a CSV file with 'question' and 'ground_truth' columns")
       
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                st.success(f"✅ Loaded {len(df)} questions from test plan")
                st.dataframe(df.head(), width='stretch')
               
                # Validate required columns
                required_columns = {'question', 'ground_truth'}
                if not required_columns.issubset(df.columns):
                    missing = required_columns - set(df.columns)
                    st.error(f"❌ CSV must contain 'question' and 'ground_truth' columns. Missing: {', '.join(missing)}")
                    return None
               
                # Check for empty rows
                if df['question'].isna().any() or df['ground_truth'].isna().any():
                    st.warning("⚠️ Some rows have empty questions or ground_truth values. These will be skipped.")
               
                return df.to_dict('records')
            except Exception as e:
                st.error(f"❌ Error reading CSV file: {e}")
                st.info("Please ensure the file is a valid CSV format.")
                return None
       
        return None
   
    def render_evaluation_section(self, test_data: List[Dict[str, str]], 
                                  config: Tuple[str, str, str, str, str, str], 
                                  evaluation_func) -> None:
        """
        Render evaluation section with start button
        
        Args:
            test_data: List of test data dictionaries
            config: Configuration tuple (api_url, bearer_token, tenant, kb_name, model_id, embedding_id)
            evaluation_func: Function to run evaluation
        """
        st.header("2. Run Evaluation")
        st.info(f"📊 Ready to evaluate {len(test_data)} test cases")
        
        if st.button("🚀 Start RAGAS Evaluation", type="primary"):
            api_url, bearer_token, tenant, knowledge_base_name, model_id, embedding_model_id = config
           
            # Validate configuration
            if not all([api_url, bearer_token, tenant, knowledge_base_name]):
                missing = [field for field, value in zip(
                    ["API URL", "Bearer Token", "Tenant", "Knowledge Base Name"],
                    [api_url, bearer_token, tenant, knowledge_base_name]
                ) if not value]
                st.error(f"❌ Please fill in all configuration fields. Missing: {', '.join(missing)}")
                return
           
            with st.spinner("🔄 Running RAGAS evaluation... This may take several minutes."):
                try:
                    result, evaluation_data = evaluation_func(
                        test_data, api_url, bearer_token, tenant,
                        knowledge_base_name, model_id, embedding_model_id
                    )
                   
                    if result is not None:
                        self._render_results(result, knowledge_base_name, model_id, embedding_model_id)
                    else:
                        st.error("❌ Evaluation completed but no results were generated.")
                   
                except Exception as e:
                    st.error(f"❌ Evaluation failed: {e}")
                    st.exception(e)
   
    def _render_results(self, result, knowledge_base_name, model_id, embedding_model_id):
        st.success("Evaluation completed!")
       
        st.header("3. Download Results")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ragas_evaluation_{knowledge_base_name}_{timestamp}.csv"
       
        results_df = result.to_pandas()
       
        results_df['evaluation_timestamp'] = timestamp
        results_df['knowledge_base_name'] = knowledge_base_name
        results_df['model_id'] = model_id
        results_df['embedding_model_id'] = embedding_model_id
       
        csv_buffer = io.StringIO()
        results_df.to_csv(csv_buffer, index=False)
       
        st.download_button(
            "Download Results CSV",
            csv_buffer.getvalue(),
            filename,
            "text/csv"
        )
       
        st.info(f"Results saved with {len(results_df)} evaluations")
        st.dataframe(results_df)
   
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
                    # Temporarily set flag to prevent UI re-rendering during import
                    original_flag = getattr(st, '_ragas_skip_ui', False)
                    st._ragas_skip_ui = True
                    try:
                        # Import the functions we need
                        from streamlit_ragas_eval import test_api_connection, extract_model_name_for_api
                        api_model_name = extract_model_name_for_api(model_id)
                        result = test_api_connection(api_url, bearer_token, tenant, knowledge_base_name, api_model_name)
                        st.session_state['api_test_result'] = result
                    finally:
                        # Always restore the flag
                        st._ragas_skip_ui = original_flag
        
        # Test Bedrock Connection
        if st.sidebar.button("🧪 Test Bedrock Connection", key="test_bedrock_btn"):
            with st.spinner("Testing Bedrock connection..."):
                # Temporarily set flag to prevent UI re-rendering during import
                original_flag = getattr(st, '_ragas_skip_ui', False)
                st._ragas_skip_ui = True
                try:
                    from streamlit_ragas_eval import test_bedrock_connection
                    result = test_bedrock_connection(model_id, embedding_model_id)
                    st.session_state['bedrock_test_result'] = result
                finally:
                    # Always restore the flag
                    st._ragas_skip_ui = original_flag
        
        # Display test results
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
                        st.text(f"  • {key}: {value}")
                    
                    if api_result.get('error'):
                        with st.expander("Error Details"):
                            st.code(api_result['error'], language='text')
                    
                    st.caption(f"Tested at: {api_result['timestamp']}")
                    st.markdown("---")
                
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
            1. Upload Test Plan (csv) with 'question' and 'ground_truth' columns
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