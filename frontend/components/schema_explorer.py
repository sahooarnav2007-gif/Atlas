import streamlit as st
import pandas as pd

def render_schema_explorer():
    dataset = st.session_state.get("current_dataset")
    if not dataset:
        st.info("No dataset loaded yet. Upload a dataset in the Upload tab to inspect its schema.")
        return

    st.subheader(f"🔍 Schema & Data Quality: {dataset.get('filename')}")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Rows", f"{dataset.get('row_count', 0):,}")
    col2.metric("Total Columns", dataset.get("column_count", 0))
    
    schema = dataset.get("schema", {})
    col3.metric("Duplicate Rows", f"{schema.get('duplicate_rows', 0):,}")
    col4.metric("Dataset Family", dataset.get("dataset_family", "default"))

    cand_ids = schema.get("candidate_identifiers", [])
    cand_dates = schema.get("candidate_dates", [])
    if cand_ids or cand_dates:
        col_a, col_b = st.columns(2)
        if cand_ids:
            col_a.info(f"🔑 **Candidate Identifiers (Unique keys):** {', '.join(cand_ids)}")
        if cand_dates:
            col_b.info(f"📅 **Detected Temporal/Date Columns:** {', '.join(cand_dates)}")

    # Column Details Table
    cols_data = schema.get("columns", {})
    if cols_data:
        table_rows = []
        for cname, info in cols_data.items():
            table_rows.append({
                "Column Name": cname,
                "Inferred Type": info.get("inferred_type"),
                "Null Count": info.get("null_count"),
                "Null %": f"{info.get('null_pct')}%",
                "Distinct Values": info.get("distinct_count"),
                "Sample Values": ", ".join(info.get("sample_values", [])[:3])
            })
        df_cols = pd.DataFrame(table_rows)
        st.dataframe(df_cols, use_container_width=True, hide_index=True)
