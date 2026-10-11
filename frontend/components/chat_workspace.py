import streamlit as st
import httpx
from frontend.components.results_viewer import render_results_viewer
from frontend.components.execution_trace import render_execution_trace

DEMO_QUESTIONS = [
    "Which five regions contribute the most revenue?",
    "Is revenue growing month over month?",
    "Which variables are most strongly associated with churn?",
    "Compare average order value across customer segments and assess whether differences are statistically significant.",
    "Find anomalous transactions and explain the detection method.",
    "Build a baseline model for an explicitly selected target and report held-out performance.",
    "Give me an overall profile and summary of missing values and distributions."
]

def render_chat_workspace(backend_url: str):
    dataset_id = st.session_state.get("dataset_id")
    if not dataset_id:
        st.info("👈 Please upload or select a dataset first in the 'Upload Dataset' tab.")
        return

    st.subheader("💬 Natural Language Analysis Workspace")
    st.caption("Ask analytical questions in plain English. The agent plans steps, selects tools, and computes verifiable evidence.")

    # Quick demo questions dropdown
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_sample = st.selectbox("Sample Analytical Questions:", ["Select or type below..."] + DEMO_QUESTIONS)
    
    question_val = selected_sample if selected_sample != "Select or type below..." else ""
    question = st.text_input("Enter your analytical question:", value=question_val, placeholder="e.g. Which five regions contribute the most revenue?")

    if st.button("Run Agentic Analysis", type="primary", use_container_width=True):
        if not question:
            st.error("Please enter a question.")
            return

        with st.spinner("Agent planning, selecting tools, and executing computations..."):
            try:
                payload = {
                    "dataset_id": dataset_id,
                    "question": question,
                    "options": {"include_chart": True, "include_execution_trace": True}
                }
                resp = httpx.post(f"{backend_url}/api/analyses", json=payload, timeout=60.0)
                if resp.status_code == 200:
                    analysis_data = resp.json()
                    st.session_state["latest_analysis"] = analysis_data
                else:
                    st.error(f"Analysis failed: {resp.text}")
            except Exception as e:
                st.error(f"Failed to communicate with backend: {str(e)}")

    # Display analysis outcome if present
    analysis = st.session_state.get("latest_analysis")
    if analysis:
        st.divider()
        tab_res, tab_trace = st.tabs(["📊 Results & Visualizations", "⏱️ Execution Trace"])
        with tab_res:
            render_results_viewer(analysis)
        with tab_trace:
            render_execution_trace(analysis.get("execution_trace", []))
