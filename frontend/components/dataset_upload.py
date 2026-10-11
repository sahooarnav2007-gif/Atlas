import streamlit as st
import httpx
import json

def render_dataset_upload(backend_url: str):
    st.subheader("📁 Upload Tabular Dataset")
    st.markdown("Universal ingestion for **CSV** and **XLSX** files with schema inference and versioning.")

    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader("Select CSV or Excel file", type=["csv", "tsv", "xlsx", "xls"])
    with col2:
        dataset_family = st.text_input("Dataset Family", value="customer_sales", help="Used to scope persistent memories across dataset versions")
        version = st.text_input("Version Tag", value="v1")

    if uploaded_file and st.button("Ingest & Profile Dataset", type="primary"):
        with st.spinner("Analyzing schema, profiling distributions, and caching..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                data = {"dataset_family": dataset_family, "version": version}
                resp = httpx.post(f"{backend_url}/api/datasets", files=files, data=data, timeout=30.0)
                
                if resp.status_code == 200:
                    res_data = resp.json()
                    st.session_state["current_dataset"] = res_data
                    st.session_state["dataset_id"] = res_data["dataset_id"]
                    st.success(f"Dataset successfully registered! ID: `{res_data['dataset_id']}` ({res_data['row_count']:,} rows, {res_data['column_count']} columns)")
                    st.rerun()
                else:
                    st.error(f"Ingestion failed: {resp.text}")
            except Exception as e:
                st.error(f"Connection error to backend: {str(e)}")
