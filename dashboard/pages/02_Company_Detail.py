import streamlit as st
import altair as alt
import sys
import os
from datetime import datetime, timedelta
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import data_access as da
import components as ui
from scoring import classify_company_momentum

st.set_page_config(page_title="Company Detail", page_icon="🏢", layout="wide")
ui.apply_custom_css()

# --- Selection Logic ---
preselected = st.session_state.get("selected_company", None)

st.title("Company Detail 🏢")

col1, col2 = st.columns([1, 1])

# Fetch rich companies (names, stars, etc) makes sorting easier
rich_companies = da.get_all_companies_rich()
if not rich_companies:
    st.error("No companies found.")
    st.stop()
    
# Sort: Starred first, then name
rich_companies.sort(key=lambda x: (not x["is_starred"], x["name"]))

slugs = [c["slug"] for c in rich_companies]
slug_map = {c["slug"]: c for c in rich_companies}

with col1:
    # Resolve default index
    default_ix = 0
    if preselected and preselected in slugs:
        default_ix = slugs.index(preselected)
        st.session_state["selected_company"] = None # Clear
        
    def format_func(slug):
        c = slug_map[slug]
        prefix = "⭐ " if c["is_starred"] else ""
        return f"{prefix}{c['name']}"
        
    selected_slug = st.selectbox("Select Company", slugs, index=default_ix, format_func=format_func)
    
    # Persistent Star Button
    is_starred = slug_map[selected_slug]["is_starred"]
    btn_label = "Unstar Company" if is_starred else "Star Company"
    if st.button(btn_label):
        da.toggle_star(selected_slug)
        st.rerun()

with col2:
    days_choice = st.selectbox("Time Window", [30, 90, 180], index=0)

# Calculate Dates
end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=days_choice)).strftime("%Y-%m-%d")

# --- Data Loading ---
df_diff = da.get_job_diffs_daily(company_slug=selected_slug, start_date=start_date, end_date=end_date)
df_news = da.get_company_news_daily(company_slug=selected_slug, start_date=start_date, end_date=end_date)
open_now = da.get_open_job_count(selected_slug) # Current snapshot

# --- Metrics Feature E ---
total_added = df_diff["added_count"].sum() if not df_diff.empty else 0
total_removed = df_diff["removed_count"].sum() if not df_diff.empty else 0
net = total_added - total_removed
senior_added = df_diff["senior_plus_added_count"].sum() if not df_diff.empty else 0

momentum = classify_company_momentum({
    "added_total": total_added,
    "net_change": net
}, open_now_count=open_now)

st.markdown(f"### Momentum: {momentum}")
st.markdown(f"**Open Now**: {open_now} filtered jobs")

st.divider()

m1, m2, m3, m4 = st.columns(4)
with m1: ui.render_metric_card("Open Jobs", open_now, delta_color="normal")
with m2: ui.render_metric_card("Added (Window)", total_added, delta_color="normal")
with m3: ui.render_metric_card("Net Change", net, delta_color="normal")
with m4: ui.render_metric_card("Senior+ Added", senior_added)

# --- Feature D: Spike Button ---
if not df_diff.empty:
    max_added_row = df_diff.loc[df_diff["added_count"].idxmax()]
    max_count = max_added_row["added_count"]
    
    # Only show button if spike is meaningful (>0)
    if max_count > 0:
        max_date = max_added_row["date"]
        st.info(f"Biggest hiring spike: **{max_date}** (+{max_count} roles)")
        if st.button(f"Inspect Spike on {max_date}"):
            st.session_state["diff_viewer_slug"] = selected_slug
            st.session_state["diff_viewer_date"] = max_date # Ensure this is YYYY-MM-DD
            st.switch_page("pages/03_Diff_Viewer.py")
else:
    st.info("No activity in window.")

st.divider()

# --- Chart ---
st.subheader("Hiring Activity & News")

if not df_diff.empty:
    chart_df = df_diff.copy()
    chart_df["date"] = chart_df["date"].astype(str)
    
    bars = alt.Chart(chart_df).mark_bar(opacity=0.7).encode(
        x=alt.X("date", title="Date", axis=alt.Axis(format="%b %d", labelAngle=-45)),
        y=alt.Y("added_count", title="Jobs Added"),
        tooltip=["date", "added_count", "removed_count"]
    ).properties(height=350)
    
    st.altair_chart(bars.interactive(), use_container_width=True)
else:
    st.write("No data for chart.")

# --- News ---
st.subheader("Recent News")
if not df_news.empty:
    for i, row in df_news.iterrows():
        if row["article_count"] > 0:
            date_str = row["date"]
            headline = row["top_headline_title"]
            url = row["top_headline_url"]
            major = row["major_event_types"] if row["has_major_event"] else ""
            
            with st.container():
                st.markdown(f"**{date_str}** {('🚨 ' + major) if major else ''}")
                st.markdown(f"[{headline}]({url})" if url else headline)
                st.divider()
else:
    st.write("No news found.")
