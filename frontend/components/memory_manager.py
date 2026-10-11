import streamlit as st
import httpx
import json

def render_memory_manager(backend_url: str):
    st.subheader("🧠 Persistent Domain Memory Manager")
    st.markdown("Store metric definitions, business rules, column semantics, and preferences that alter future agent computations.")

    # 1. Add New Memory
    with st.expander("➕ Define New Domain Knowledge / Metric Rule", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            mem_type = st.selectbox(
                "Memory Type",
                ["metric_definition", "column_semantics", "reusable_filter", "preference"]
            )
            key = st.text_input("Memory Key", value="active_customer", help="Identifier such as 'active_customer' or 'churn_definition'")
            family = st.text_input("Scope / Dataset Family", value="customer_sales")
        with col2:
            cols_input = st.text_input("Target Columns (comma-separated)", value="customer_status")
            rule_input = st.text_input("SQL Filter Rule", value="customer_status != 'cancelled'")
            definition_text = st.text_area("Human Definition", value="Customer whose status is not cancelled")

        if st.button("Save to Persistent Memory", type="primary"):
            payload = {
                "type": mem_type,
                "key": key,
                "value": {
                    "definition": definition_text,
                    "rule": rule_input
                },
                "dataset_family": family,
                "columns": [c.strip() for c in cols_input.split(",") if c.strip()],
                "source": "explicit_user"
            }
            try:
                resp = httpx.post(f"{backend_url}/api/memories", json=payload)
                if resp.status_code == 200:
                    st.success(f"Memory rule `{key}` successfully saved!")
                    st.rerun()
                else:
                    st.error(f"Error saving memory: {resp.text}")
            except Exception as e:
                st.error(f"Backend communication failed: {str(e)}")

    # 2. View and Manage Existing Memories
    st.markdown("### Active Stored Memories")
    try:
        resp = httpx.get(f"{backend_url}/api/memories")
        if resp.status_code == 200:
            memories = resp.json()
            if not memories:
                st.info("No active memories stored yet.")
            else:
                for mem in memories:
                    with st.container():
                        col_info, col_del = st.columns([5, 1])
                        val = mem.get("value", {})
                        with col_info:
                            st.markdown(f"**Key:** `{mem.get('key')}` (v{mem.get('version')}) | **Type:** `{mem.get('type')}` | **Family:** `{mem.get('dataset_family')}`")
                            st.markdown(f"> **Rule:** `{val.get('rule')}`  \n> *{val.get('definition')}*")
                        with col_del:
                            if st.button("Delete", key=f"del_{mem.get('memory_id')}"):
                                httpx.delete(f"{backend_url}/api/memories/{mem.get('memory_id')}")
                                st.warning(f"Memory {mem.get('key')} deleted.")
                                st.rerun()
                        st.divider()
        else:
            st.error("Failed to fetch memories from backend.")
    except Exception as e:
        st.error(f"Backend communication failed: {str(e)}")
