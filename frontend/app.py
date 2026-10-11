import os
import streamlit as st
import httpx
import pandas as pd
from pathlib import Path
from frontend.components.dashboard_stage import render_dashboard_stage
from frontend.components.schema_explorer import render_schema_explorer
from frontend.components.execution_trace import render_execution_trace
from frontend.components.memory_manager import render_memory_manager

st.set_page_config(
    page_title="Data Agent | Dashboard Stage",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load custom dark styles matching reference UI
css_path = Path(__file__).parent / "styles" / "custom.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# Session State Initialization
if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = [
        {
            "role": "agent",
            "text": "Hello! I am your Data Agent. Click the Demo option below or upload a CSV, then ask me questions like 'Show sales by region' or 'Top 5 products'."
        }
    ]

if "current_dataset" not in st.session_state:
    st.session_state["current_dataset"] = None

if "dataset_df" not in st.session_state:
    st.session_state["dataset_df"] = None

if "latest_trace" not in st.session_state:
    st.session_state["latest_trace"] = []

# Function to load demo dataset
def load_demo():
    try:
        resp = httpx.post(f"{BACKEND_URL}/api/datasets/demo", timeout=20.0)
        if resp.status_code == 200:
            data = resp.json()
            st.session_state["current_dataset"] = data
            st.session_state["dataset_id"] = data["dataset_id"]
            
            # Load local dataframe for instant interactive charting
            demo_csv = Path("data/demo_retail_orders.csv")
            if demo_csv.exists():
                st.session_state["dataset_df"] = pd.read_csv(demo_csv)
            
            st.session_state["chat_messages"].append({
                "role": "status",
                "text": f"⚡ Loaded {data['row_count']} rows from Demo Retail Orders. I've prepared your dashboard. You can now ask me to visualize specific data points!"
            })
            st.rerun()
        else:
            st.error(f"Failed to load demo dataset: {resp.text}")
    except Exception as e:
        st.error(f"Error connecting to backend: {str(e)}")

# Top Navigation Bar
top_c1, top_c2 = st.columns([6, 1])
with top_c1:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
        <span style="font-size:24px; color:#38bdf8;">⚡</span>
        <span style="font-size:20px; font-weight:700; color:#f8fafc; letter-spacing:0.5px;">ATLAS · AGENTIC TABULAR INTELLIGENCE</span>
    </div>
    """, unsafe_allow_html=True)
with top_c2:
    try:
        r = httpx.get(f"{BACKEND_URL}/health", timeout=1.0)
        if r.status_code == 200:
            st.markdown("<div style='text-align:right;'><span style='color:#34d399; font-weight:600; font-size:12px;'>● LIVE</span></div>", unsafe_allow_html=True)
    except Exception:
        st.markdown("<div style='text-align:right;'><span style='color:#f87171; font-weight:600; font-size:12px;'>○ OFFLINE</span></div>", unsafe_allow_html=True)

# Main Split Screen Layout (Matches Reference Image)
col_left, col_right = st.columns([1, 1.7])

# ==========================================
# LEFT COLUMN: DATA AGENT (Chat & Uploads)
# ==========================================
with col_left:
    st.markdown("""
    <div class="agent-header">
        <span>💬</span>
        <span>Data Agent</span>
    </div>
    """, unsafe_allow_html=True)

    # Demo & Upload Option Section
    with st.container():
        c_demo, c_up = st.columns([1.2, 1])
        with c_demo:
            if st.button("✨ Load Demo Retail CSV", type="primary", use_container_width=True, help="Automatically loads the attached retail orders CSV and builds the dashboard"):
                load_demo()
        with c_up:
            show_upload = st.checkbox("📁 Custom Upload", value=False)

    if show_upload:
        uploaded_file = st.file_uploader("Upload custom CSV/XLSX", type=["csv", "tsv", "xlsx", "xls"], label_visibility="collapsed")
        if uploaded_file and st.button("Ingest Custom File", use_container_width=True):
            with st.spinner("Profiling dataset..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    resp = httpx.post(f"{BACKEND_URL}/api/datasets", files=files, timeout=30.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state["current_dataset"] = data
                        st.session_state["dataset_id"] = data["dataset_id"]
                        
                        # Load dataframe
                        uploaded_file.seek(0)
                        if uploaded_file.name.endswith(".csv"):
                            st.session_state["dataset_df"] = pd.read_csv(uploaded_file)
                        else:
                            st.session_state["dataset_df"] = pd.read_excel(uploaded_file)

                        st.session_state["chat_messages"].append({
                            "role": "status",
                            "text": f"⚡ Loaded {data['row_count']} rows from {data['filename']}. Dashboard updated!"
                        })
                        st.rerun()
                except Exception as e:
                    st.error(f"Upload failed: {str(e)}")

    # Chat Stream Container
    chat_box = st.container(height=480)
    with chat_box:
        for msg in st.session_state["chat_messages"]:
            if msg["role"] == "user":
                st.markdown(f'<div class="msg-user">{msg["text"]}</div>', unsafe_allow_html=True)
            elif msg["role"] == "status":
                st.markdown(f'<div class="msg-agent-status">{msg["text"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="msg-agent">{msg["text"]}</div>', unsafe_allow_html=True)

    # Quick Suggestion Prompts
    st.caption("Quick Queries:")
    q_col1, q_col2 = st.columns(2)
    with q_col1:
        if st.button("Show sales by region", use_container_width=True):
            st.session_state["pending_query"] = "Which regions contribute the most revenue?"
    with q_col2:
        if st.button("Top products by profit", use_container_width=True):
            st.session_state["pending_query"] = "Top 5 products by profit"

    # Input Box at bottom
    with st.form("chat_form", clear_on_submit=True):
        default_val = st.session_state.pop("pending_query", "")
        user_input = st.text_input("Message Data Agent...", value=default_val, placeholder="Ask 'Show Profit vs Sales' or anything...", label_visibility="collapsed")
        c_sub1, c_sub2 = st.columns([4, 1])
        with c_sub2:
            submitted = st.form_submit_button("✈️ Send", use_container_width=True)

    if submitted and user_input:
        ds_id = st.session_state.get("dataset_id")
        if not ds_id:
            # Auto-load demo dataset if user asks query before loading
            load_demo()
            ds_id = st.session_state.get("dataset_id")

        st.session_state["chat_messages"].append({"role": "user", "text": user_input})
        
        with st.spinner("Computing evidence..."):
            try:
                payload = {
                    "dataset_id": ds_id,
                    "question": user_input,
                    "options": {"include_chart": True}
                }
                resp = httpx.post(f"{BACKEND_URL}/api/analyses", json=payload, timeout=60.0)
                if resp.status_code == 200:
                    res_data = resp.json()
                    st.session_state["latest_trace"] = res_data.get("execution_trace", [])
                    answer_text = res_data.get("answer", "Analysis completed.")
                    
                    # Add Agent Response Bubble matching UI style
                    st.session_state["chat_messages"].append({
                        "role": "agent",
                        "text": f"I've computed the evidence for your question. Check the Dashboard Stage!\n\n{answer_text}"
                    })
                else:
                    st.session_state["chat_messages"].append({
                        "role": "agent",
                        "text": f"⚠️ Could not execute query: {resp.text}"
                    })
            except Exception as e:
                st.session_state["chat_messages"].append({
                    "role": "agent",
                    "text": f"⚠️ Execution error: {str(e)}"
                })
        st.rerun()

# ==========================================
# RIGHT COLUMN: DASHBOARD STAGE (Charts & Tabs)
# ==========================================
with col_right:
    tab_stage, tab_table, tab_trace, tab_memory = st.tabs([
        "🪟 Dashboard Stage",
        "📋 Data Table",
        "⏱️ Execution Trace",
        "🧠 Domain Memory"
    ])

    with tab_stage:
        df = st.session_state.get("dataset_df")
        render_dashboard_stage(df)

    with tab_table:
        df = st.session_state.get("dataset_df")
        if df is not None:
            st.markdown(f"**Loaded Dataset ({len(df):,} rows, {len(df.columns)} columns)**")
            st.dataframe(df, use_container_width=True)
            render_schema_explorer()
        else:
            st.info("No dataset loaded yet.")

    with tab_trace:
        trace = st.session_state.get("latest_trace", [])
        render_execution_trace(trace)

    with tab_memory:
        render_memory_manager(BACKEND_URL)
