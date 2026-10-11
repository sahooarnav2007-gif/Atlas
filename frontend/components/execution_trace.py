import streamlit as st
import json

def render_execution_trace(trace: list):
    if not trace:
        st.info("No execution trace available.")
        return

    st.subheader("⏱️ Inspectable Execution Trace & Provenance")
    st.markdown("Full transparency into agent actions, validated parameters, operation IDs, and computation duration.")

    for idx, env in enumerate(trace, 1):
        status = env.get("status", "unknown")
        tool = env.get("tool_name", "")
        op_id = env.get("operation_id", "")
        duration = env.get("duration_ms", 0)

        badge = "🟢 SUCCESS" if status == "success" else "🔴 ERROR"
        with st.expander(f"Step {idx}: {tool} ({op_id}) — {badge} [{duration}ms]"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Validated Parameters:**")
                st.json(env.get("validated_parameters", {}))
            with col2:
                st.markdown("**Result / Summary:**")
                res = env.get("result", {})
                if "rows" in res:
                    st.write(f"Returned {len(res['rows'])} rows.")
                    st.dataframe(res["rows"][:5], hide_index=True)
                else:
                    st.json(res)

            warnings = env.get("warnings", [])
            if warnings:
                st.warning("Warnings: " + "; ".join(warnings))
            if env.get("error_message"):
                st.error(f"Error: {env['error_message']}")
