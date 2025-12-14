import streamlit as st
import altair as alt
import pandas as pd
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import data_access as da
import components as ui
from scoring import classify_company_momentum

st.set_page_config(page_title="Visual Insights", page_icon="💡", layout="wide")
ui.apply_custom_css()

st.title("Market Insights 💡")
st.markdown("Visualizing hiring trends, momentum, and opportunities.")

# --- Sidebar Controls ---
with st.sidebar:
    st.header("Analysis Settings")
    days_back = st.slider("Lookback Window", 7, 90, 30)
    
    # Global Filter: Starred Only
    filter_starred = st.checkbox("Starred Companies Only", value=False)

# --- Data Loading ---
# 1. Daily Granular Data (Trends, Heatmap)
df_daily = da.get_daily_company_stats(days_back=days_back)

# 2. Company Rich Data (Open Now, Names)
rich_companies = da.get_all_companies_rich()
df_rich = pd.DataFrame(rich_companies)

if df_daily.empty:
    st.info("No data available for the selected window. Try generating more data or increasing the lookback.")
    st.stop()

# Merge Name/Stars into Daily
df_daily = df_daily.merge(df_rich[["slug", "name", "is_starred", "open_jobs_count"]], left_on="company_slug", right_on="slug", how="left")

# --- Filtering ---
if filter_starred:
    df_daily = df_daily[df_daily["is_starred"] == True]
    df_rich = df_rich[df_rich["is_starred"] == True]

if df_daily.empty:
    st.warning("No data matches current filters.")
    st.stop()

# --- Chart 1: Market Trend Timeline ---
st.subheader("1. Market Trend Timeline")
# Aggregate daily
market_trend = df_daily.groupby("date")[["added_count", "removed_count", "net_change"]].sum().reset_index()

base = alt.Chart(market_trend).encode(x="date:T")
line_added = base.mark_line(color="#10b981").encode(y="added_count", tooltip=["date", "added_count"])
line_removed = base.mark_line(color="#ef4444").encode(y="removed_count", tooltip=["date", "removed_count"])

chart_trend = (line_added + line_removed).properties(height=300, title="Daily Added (Green) vs Removed (Red)")
st.altair_chart(chart_trend, use_container_width=True)

# --- Chart 2: Opportunity Map ---
st.subheader("2. Opportunity Map")
c1, c2 = st.columns([3, 1])

with c1:
    # Aggregate stats per company for the window
    company_aggs = df_daily.groupby("slug").agg({
        "added_count": "sum",
        "net_change": "sum",
        "name": "first",
        "open_jobs_count": "first" # Matches current snapshot, effectively
    }).reset_index()
    
    # Compute Momentum Label for Color
    def get_mom(row):
        return classify_company_momentum({"added_total": row["added_count"], "net_change": row["net_change"]}, row["open_jobs_count"])
        
    company_aggs["momentum"] = company_aggs.apply(get_mom, axis=1)
    
    # Scatter Plot
    # X=Open Now, Y=Net Change, Size=Added
    scatter = alt.Chart(company_aggs).mark_circle().encode(
        x=alt.X("open_jobs_count", title="Open Jobs Now"),
        y=alt.Y("net_change", title="Net Change (Window)"),
        size=alt.Size("added_count", title="Total Added", scale=alt.Scale(range=[50, 500])),
        color=alt.Color("momentum", title="Momentum", scale=alt.Scale(domain=["🔥 Hot", "🙂 Warming", "😐 Flat", "🧊 Cooling"], range=["#ef4444", "#f97316", "#64748b", "#3b82f6"])),
        tooltip=["name", "open_jobs_count", "net_change", "added_count", "momentum"]
    ).properties(height=400).interactive()
    
    # Interaction Selection
    # Using Altair selection is tricky for simple Streamlit interactivity.
    # We'll use a simple dropdown for "Drill Down" below or rely on the user finding the company.
    st.altair_chart(scatter, use_container_width=True)

with c2:
    st.markdown("##### Drill Down")
    # sorted by open jobs
    opts = company_aggs.sort_values("open_jobs_count", ascending=False)["slug"].tolist()
    
    # Helper to map slug to name
    name_map = dict(zip(company_aggs["slug"], company_aggs["name"]))
    
    selected = st.selectbox("Select Company to Analyze", opts, format_func=lambda x: name_map.get(x, x))
    
    if selected:
        st.session_state["selected_company"] = selected
        st.markdown(f"**{name_map[selected]}**")
        st.caption(f"{company_aggs[company_aggs['slug']==selected]['momentum'].iloc[0]}")
        
        if st.button("Go to Detail"):
            st.switch_page("pages/02_Company_Detail.py")
        if st.button("Go to Diff Viewer"):
             st.session_state["diff_viewer_slug"] = selected
             st.switch_page("pages/03_Diff_Viewer.py")

st.divider()

# --- Chart 3: Hiring Heatmap ---
st.subheader("3. Hiring Heatmap (Last 30 Days)")
# Filter to top N active companies to avoid overcrowding
top_N_slugs = company_aggs.sort_values("added_count", ascending=False).head(20)["slug"]
heatmap_df = df_daily[df_daily["slug"].isin(top_N_slugs)].copy()

heatmap = alt.Chart(heatmap_df).mark_rect().encode(
    x=alt.X("date:T", title=None, axis=alt.Axis(format="%d")),
    y=alt.Y("name:O", title=None),
    color=alt.Color("net_change", scale=alt.Scale(scheme="redyellowgreen"), title="Net Change"),
    tooltip=["name", "date", "added_count", "removed_count", "net_change"]
).properties(height=max(300, len(top_N_slugs)*20))

st.altair_chart(heatmap, use_container_width=True)

# --- Chart 4: Mix Charts ---
st.subheader("4. Hiring Mix (Global Window)")

mix_cols = st.columns(2)
# Seniority Mix
total_added = df_daily["added_count"].sum()
senior_added = df_daily["senior_plus_added_count"].sum()
mid_added = max(0, total_added - senior_added)

mix_df = pd.DataFrame([
    {"type": "Mid/Junior", "count": mid_added},
    {"type": "Senior+", "count": senior_added}
])

with mix_cols[0]:
    st.markdown("**Seniority**")
    base_pie = alt.Chart(mix_df).encode(theta=alt.Theta("count", stack=True))
    pie = base_pie.mark_arc(outerRadius=120).encode(
        color=alt.Color("type"),
        tooltip=["type", "count"]
    )
    text = base_pie.mark_text(radius=140).encode(
        text=alt.Text("count"),
        order=alt.Order("type"),
        color=alt.value("white")  
    )
    st.altair_chart(pie + text, use_container_width=True)

# Remote Mix
remote_added = df_daily["us_remote_added_count"].sum()
onsite_added = max(0, total_added - remote_added) # Approximation (Total - Remote)

mix_remote_df = pd.DataFrame([
    {"type": "Remote/Hybrid", "count": remote_added},
    {"type": "Onsite/Other", "count": onsite_added}
])

with mix_cols[1]:
    st.markdown("**Remote vs Onsite**")
    base_pie_r = alt.Chart(mix_remote_df).encode(theta=alt.Theta("count", stack=True))
    pie_r = base_pie_r.mark_arc(outerRadius=120).encode(
        color=alt.Color("type", scale=alt.Scale(domain=["Remote/Hybrid", "Onsite/Other"], range=["#a855f7", "#cbd5e1"])),
        tooltip=["type", "count"]
    )
    text_r = base_pie_r.mark_text(radius=140).encode(
        text=alt.Text("count"),
        order=alt.Order("type"),
        color=alt.value("white")
    )
    st.altair_chart(pie_r + text_r, use_container_width=True)
