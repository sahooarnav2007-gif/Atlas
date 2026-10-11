import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def render_results_viewer(analysis_result: dict):
    if not analysis_result:
        return

    st.subheader("📊 Analysis Results & Evidence")
    
    # Grounded textual answer
    answer = analysis_result.get("answer", "")
    st.markdown(answer)

    # Visualizations
    visualizations = analysis_result.get("visualizations", [])
    if visualizations:
        st.markdown("### Visual Insights")
        for fig_data in visualizations:
            try:
                fig = go.Figure(fig_data)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error rendering chart: {str(e)}")

    # Tables from trace
    trace = analysis_result.get("execution_trace", [])
    for step in trace:
        if step.get("tool_name") == "query_data" and step.get("status") == "success":
            rows = step.get("result", {}).get("rows", [])
            if rows:
                with st.expander(f"📋 Data Table ({step.get('operation_id')})", expanded=True):
                    df_res = pd.DataFrame(rows)
                    st.dataframe(df_res, use_container_width=True)

    # Warnings
    warnings = analysis_result.get("warnings", [])
    if warnings:
        st.warning("⚠️ Execution Warnings:\n- " + "\n- ".join(warnings))
