import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any, List

def create_styled_chart(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        font=dict(color="#94a3b8", family="Inter, sans-serif", size=11),
        title=dict(text="", font=dict(color="#f8fafc", size=14)),
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis=dict(showgrid=False, zeroline=False, color="#64748b"),
        yaxis=dict(showgrid=True, gridcolor="#1e293b", zeroline=False, color="#64748b"),
        hoverlabel=dict(bgcolor="#1e293b", font_color="#38bdf8", font_size=12)
    )
    # Give all bar traces the vibrant cyan from the reference image
    fig.update_traces(marker_color="#00b4d8", marker_line_color="#38bdf8", marker_line_width=0.5)
    return fig

def render_dashboard_stage(df: pd.DataFrame, custom_charts: List[Dict[str, Any]] = None):
    col_hdr, col_btn = st.columns([3, 1])
    with col_hdr:
        st.markdown("### 🪟 Dashboard Stage")
    with col_btn:
        if st.button("📥 FULL REPORT", use_container_width=True):
            st.toast("Generating full analytical report...", icon="📄")
            st.session_state["show_full_report"] = True

    if df is None or df.empty:
        st.info("No dataset loaded yet. Click the **'✨ Load Demo Retail CSV'** button or upload a CSV on the left to populate the dashboard stage.")
        return

    # We arrange up to 4 charts in a 2x2 grid
    cols_grid_1, cols_grid_2 = st.columns(2)
    
    # 1. Chart 1: Categorical Bar Chart (e.g. Region or Customer Segment)
    with cols_grid_1:
        st.markdown("""
        <div class="dash-card">
            <div class="card-title-row">
                <span class="card-title">Revenue by Region</span>
                <span class="card-badge">Regional Total</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if "region" in df.columns and "revenue_inr" in df.columns:
            sub1 = df.groupby("region")["revenue_inr"].sum().reset_index().sort_values("revenue_inr", ascending=False)
            fig1 = px.bar(sub1, x="region", y="revenue_inr", labels={"region": "", "revenue_inr": "Revenue (INR)"})
            create_styled_chart(fig1, "Revenue by Region")
            st.plotly_chart(fig1, use_container_width=True, key="chart_region")
        elif "region" in df.columns and "revenue" in df.columns:
            sub1 = df.groupby("region")["revenue"].sum().reset_index().sort_values("revenue", ascending=False)
            fig1 = px.bar(sub1, x="region", y="revenue", labels={"region": "", "revenue": "Revenue"})
            create_styled_chart(fig1, "Revenue by Region")
            st.plotly_chart(fig1, use_container_width=True, key="chart_region")
        else:
            cat_col = df.select_dtypes(include=["object"]).columns[0] if len(df.select_dtypes(include=["object"]).columns) > 0 else df.columns[0]
            sub1 = df[cat_col].value_counts().head(8).reset_index()
            sub1.columns = [cat_col, "count"]
            fig1 = px.bar(sub1, x=cat_col, y="count")
            create_styled_chart(fig1, f"Distribution of {cat_col}")
            st.plotly_chart(fig1, use_container_width=True, key="chart_cat1")

    # 2. Chart 2: Product / Category ranking (Top items)
    with cols_grid_2:
        st.markdown("""
        <div class="dash-card">
            <div class="card-title-row">
                <span class="card-title">Top Products by Profit</span>
                <span class="card-badge">Top Products</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if "product" in df.columns and "profit_inr" in df.columns:
            sub2 = df.groupby("product")["profit_inr"].sum().reset_index().sort_values("profit_inr", ascending=False)
            fig2 = px.bar(sub2, x="product", y="profit_inr", labels={"product": "", "profit_inr": "Profit (INR)"})
            create_styled_chart(fig2, "Top Products by Profit")
            st.plotly_chart(fig2, use_container_width=True, key="chart_product")
        else:
            num_cols = df.select_dtypes(include=["number"]).columns
            target_metric = num_cols[0] if len(num_cols) > 0 else df.columns[-1]
            cat_cols = df.select_dtypes(include=["object"]).columns
            dim = cat_cols[1] if len(cat_cols) > 1 else (cat_cols[0] if len(cat_cols) > 0 else df.columns[0])
            sub2 = df.groupby(dim)[target_metric].sum().reset_index().sort_values(target_metric, ascending=False).head(8)
            fig2 = px.bar(sub2, x=dim, y=target_metric)
            create_styled_chart(fig2, f"{target_metric} by {dim}")
            st.plotly_chart(fig2, use_container_width=True, key="chart_cat2")

    # Second row in grid
    cols_grid_3, cols_grid_4 = st.columns(2)

    # 3. Chart 3: Trends or Monthly Growth
    with cols_grid_3:
        st.markdown("""
        <div class="dash-card">
            <div class="card-title-row">
                <span class="card-title">Revenue Trend Over Time</span>
                <span class="card-badge">Timeline</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        date_candidates = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]
        rev_col = "revenue_inr" if "revenue_inr" in df.columns else ("revenue" if "revenue" in df.columns else None)
        if date_candidates and rev_col:
            df_temp = df.copy()
            df_temp["_parsed_date"] = pd.to_datetime(df_temp[date_candidates[0]], errors="coerce")
            df_temp = df_temp.dropna(subset=["_parsed_date"]).sort_values("_parsed_date")
            df_monthly = df_temp.set_index("_parsed_date").resample("ME")[rev_col].sum().reset_index()
            df_monthly["_parsed_date"] = df_monthly["_parsed_date"].dt.strftime("%b %Y")
            fig3 = px.bar(df_monthly, x="_parsed_date", y=rev_col, labels={"_parsed_date": "Month", rev_col: "Revenue"})
            create_styled_chart(fig3, "Monthly Trend")
            st.plotly_chart(fig3, use_container_width=True, key="chart_trend")
        else:
            num_cols = df.select_dtypes(include=["number"]).columns
            target = num_cols[-1] if len(num_cols) > 0 else df.columns[0]
            fig3 = px.histogram(df, x=target, nbins=15)
            create_styled_chart(fig3, f"Distribution of {target}")
            st.plotly_chart(fig3, use_container_width=True, key="chart_dist")

    # 4. Chart 4: Segment / Sales Channel Comparison
    with cols_grid_4:
        st.markdown("""
        <div class="dash-card">
            <div class="card-title-row">
                <span class="card-title">Sales by Channel & Segment</span>
                <span class="card-badge">Breakdown</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if "sales_channel" in df.columns and ("revenue_inr" in df.columns or "revenue" in df.columns):
            metric_target = "revenue_inr" if "revenue_inr" in df.columns else "revenue"
            sub4 = df.groupby("sales_channel")[metric_target].sum().reset_index().sort_values(metric_target, ascending=False)
            fig4 = px.bar(sub4, x="sales_channel", y=metric_target, labels={"sales_channel": "", metric_target: "Revenue"})
            create_styled_chart(fig4, "Sales by Channel")
            st.plotly_chart(fig4, use_container_width=True, key="chart_channel")
        else:
            num_cols = df.select_dtypes(include=["number"]).columns
            if len(num_cols) >= 2:
                fig4 = px.scatter(df.head(100), x=num_cols[0], y=num_cols[1])
                create_styled_chart(fig4, "Scatter")
                st.plotly_chart(fig4, use_container_width=True, key="chart_scatter")
            else:
                st.info("Additional dimensional data unavailable.")
