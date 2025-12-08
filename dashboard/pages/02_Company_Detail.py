import streamlit as st
import altair as alt
import sys
import os
from datetime import datetime, timedelta
import pandas as pd

# Add parent directory to path to import peers
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import data_access as da
import components as ui
from scoring import classify_company_momentum

st.set_page_config(page_title="Company Detail", page_icon="🏢", layout="wide")
ui.apply_custom_css()

# --- Session State Config for Favorites ---
if "favorites" not in st.session_state:
    st.session_state["favorites"] = []

def toggle_favorite(slug):
    if slug in st.session_state["favorites"]:
        st.session_state["favorites"].remove(slug)
    else:
        st.session_state["favorites"].append(slug)

# --- Selection Logic ---
# Check if redirected from Overview
preselected = st.session_state.get("selected_company", None)

st.title("Company Detail 🏢")

col1, col2 = st.columns([1, 1])

with col1:
    companies = da.get_companies()
    if not companies:
        st.error("No companies found in companies.json")
        st.stop()
        
    slugs = sorted([c["slug"] for c in companies])
    
    # Sort favorites to top
    favs = st.session_state["favorites"]
    slugs = sorted(slugs, key=lambda x: (x not in favs, x))
    
    # Format labels to show star
    format_func = lambda s: f"⭐ {s}" if s in favs else s
    
    # Determine index
    default_ix = 0
    if preselected and preselected in slugs:
        default_ix = slugs.index(preselected)
        # Clear it so it doesn't stick
        st.session_state["selected_company"] = None
        
    selected_slug = st.selectbox("Select Company", slugs, index=default_ix, format_func=format_func)
    
    # Favorites Toggle
    is_fav = selected_slug in favs
    btn_label = "Unstar Company" if is_fav else "Star Company"
    if st.button(btn_label):
        toggle_favorite(selected_slug)
        st.rerun()

with col2:
    days_choice = st.selectbox("Time Window", [30, 90, 180], index=0)

# Calculate Dates
end_date = datetime.now().strftime("%Y-%m-%d")
start_date_obj = datetime.now() - timedelta(days=days_choice)
start_date = start_date_obj.strftime("%Y-%m-%d")

# --- Data Loading ---
df_diff = da.get_job_diffs_daily(company_slug=selected_slug, start_date=start_date, end_date=end_date)
df_news = da.get_company_news_daily(company_slug=selected_slug, start_date=start_date, end_date=end_date)

if df_diff.empty:
    st.info(f"No job activity recorded for **{selected_slug}** in the last {days_choice} days.")
    # Still show news if available?
else:
    # --- Momentum & Feature C ---
    total_added = df_diff["added_count"].sum()
    total_removed = df_diff["removed_count"].sum()
    net = total_added - total_removed
    senior_added = df_diff["senior_plus_added_count"].sum()
    mid_added = max(0, total_added - senior_added)
    
    momentum = classify_company_momentum({
        "added_total": total_added,
        "net_change": net
    })
    
    # Display Pulse Header
    st.markdown(f"### Momentum: {momentum}")
    st.markdown(f"""
    - **Added {total_added} roles** ({mid_added} Mid-level, {senior_added} Senior+) in the last {days_choice} days.
    - **Net Change**: {net:+d}.
    """)
    
    if not df_news.empty:
         major_events = df_news[df_news["has_major_event"] == 1]["major_event_types"].unique()
         if len(major_events) > 0:
             st.markdown(f"- **Recent Events**: {', '.join(major_events)}")

    st.divider()

    m1, m2, m3, m4 = st.columns(4)
    with m1: ui.render_metric_card("Added", total_added, net, delta_color="normal")
    with m2: ui.render_metric_card("Removed", total_removed) 
    with m3: ui.render_metric_card("Net Change", net, delta_color="normal")
    with m4: ui.render_metric_card("Senior+ Added", senior_added)
    
    # --- Feature D: Spike Button ---
    # Find day with max added
    max_added_row = df_diff.loc[df_diff["added_count"].idxmax()]
    max_date = max_added_row["date"]
    max_count = max_added_row["added_count"]
    
    if max_count > 0:
        st.info(f"Biggest hiring spike: **{max_date}** (+{max_count} roles)")
        if st.button(f"Inspect Spike on {max_date}"):
            st.session_state["diff_viewer_slug"] = selected_slug
            st.session_state["diff_viewer_date"] = max_date
            st.switch_page("pages/03_Diff_Viewer.py")
            
    st.divider()
    
    # --- Chart ---
    st.subheader("Hiring Activity & News")
    
    # Transform for Altair
    chart_df = df_diff.copy()
    chart_df["date"] = chart_df["date"].astype(str)
    
    # Base chart: Bar for Added
    bars = alt.Chart(chart_df).mark_bar(opacity=0.7).encode(
        x=alt.X("date", title="Date", axis=alt.Axis(format="%b %d", labelAngle=-45)),
        y=alt.Y("added_count", title="Jobs Added"),
        tooltip=["date", "added_count", "removed_count"]
    ).properties(height=350)
    
    line_senior = alt.Chart(chart_df).mark_line(color="#E9D5FF").encode(
        x="date",
        y="senior_plus_added_count"
    )
    
    # News Markers
    news_df_chart = df_news[df_news["has_major_event"] == 1].copy()
    if not news_df_chart.empty:
        news_df_chart["date"] = news_df_chart["date"].astype(str)
        max_y = chart_df["added_count"].max()
        news_df_chart["y_val"] = max_y * 1.1 
        
        news_points = alt.Chart(news_df_chart).mark_point(
            shape="triangle-down", size=100, color="orange", filled=True
        ).encode(
            x="date",
            y=alt.Y("y_val", title=None),
            tooltip=["date", "major_event_types", "top_headline_title"]
        )
        
        final_chart = (bars + line_senior + news_points).interactive()
    else:
        final_chart = (bars + line_senior).interactive()
        
    st.altair_chart(final_chart, use_container_width=True)

# --- News List ---
st.subheader("Recent News")
if not df_news.empty:
    for i, row in df_news.iterrows():
        if row["article_count"] > 0:
            date_str = row["date"]
            headline = row["top_headline_title"]
            url = row["top_headline_url"]
            major = row["major_event_types"] if row["has_major_event"] else ""
            
            with st.container():
                st.markdown(f"**{date_str}**")
                if major:
                    st.caption(f"🚨 {major}")
                st.markdown(f"[{headline}]({url})" if url else headline)
                st.divider()
else:
    st.write("No news found.")
