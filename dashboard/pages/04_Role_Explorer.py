import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import data_access as da
import components as ui
from scoring import calculate_role_match_score

st.set_page_config(page_title="Role Explorer", page_icon="🔭", layout="wide")
ui.apply_custom_css()

st.title("Personalized Role Explorer 🔭")
st.markdown("Jobs ranked by fit for **your profile**.")

# --- Inputs ---
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    days_back = st.selectbox("Added in last", [3, 7, 14, 30], index=3)

with col2:
    match_filter = st.multiselect(
        "Match Strength", 
        ["Strong", "Good", "Okay", "Weak"], 
        default=["Strong", "Good"]
    )

with col3:
    companies = da.get_companies()
    slugs = sorted([c["slug"] for c in companies]) if companies else []
    selected_companies = st.multiselect("Filter by Company", slugs)

search_query = st.text_input("Search (refine within results)", placeholder="e.g. 'platform' or 'remote'")

# --- Fetch & Score Data ---
with st.spinner(f"Scanning & scoring roles from last {days_back} days..."):
    all_jobs = da.get_recent_added_jobs(days_back=days_back)
    
    scored_jobs = []
    today = datetime.now().date()
    
    for job in all_jobs:
        added_date_str = job.get("_date_added")
        days_ago = 0
        if added_date_str:
            try:
                added_dt = datetime.strptime(added_date_str, "%Y-%m-%d").date()
                days_ago = (today - added_dt).days
            except: pass
                
        match = calculate_role_match_score(job, days_ago_added=days_ago)
        
        # Location: ensure human-friendly string (avoid raw dict rendering)
        loc_raw = job.get("locations", [])
        loc_str = ""
        if isinstance(loc_raw, list):
            # If list of dicts, extract names; if list of strings, join
            parts = []
            for l in loc_raw:
                if isinstance(l, dict):
                    raw = l.get("raw")
                    name = l.get("name") or raw
                    if not name:
                        city = l.get("city")
                        state = l.get("state")
                        cc = l.get("country_code") or l.get("country")
                        name = ", ".join([p for p in [city, state, cc] if p]) or str(l)
                    parts.append(name)
                else:
                    parts.append(str(l))
            loc_str = ", ".join(parts[:2])
            if len(parts) > 2: loc_str += f" +{len(parts)-2}"
        else:
            loc_str = str(loc_raw)
            
        fl = job.copy()
        fl["match_score"] = match["score"]
        fl["match_label"] = match["label"]
        fl["match_reasons"] = ", ".join(match["match_reasons"])
        fl["location_clean"] = loc_str # Use this for display
        scored_jobs.append(fl)

df = pd.DataFrame(scored_jobs)

if df.empty:
    st.info("No jobs found in the selected time range.")
    st.stop()

# --- Filtering ---
if match_filter:
    df = df[df["match_label"].isin(match_filter)]

if selected_companies:
    df = df[df["_company"].isin(selected_companies)]

if search_query:
    q = search_query.lower()
    df["loc_search"] = df["location_clean"].str.lower()
    mask = (
        df["title"].str.lower().str.contains(q, na=False) | 
        df["_company"].str.lower().str.contains(q, na=False) |
        df["loc_search"].str.contains(q, na=False)
    )
    df = df[mask]

# --- Sorting ---
df = df.sort_values(by=["match_score", "_date_added"], ascending=[False, False])

# --- Display ---
total = len(df)
st.caption(f"Showing **{total}** matches.")

page_cols = st.columns([1, 1, 3])
with page_cols[0]:
    page_size = st.selectbox("Rows per page", [50, 100, 200], index=1)
with page_cols[1]:
    max_pages = max(1, (total + page_size - 1) // page_size)
    page = st.number_input("Page", min_value=1, max_value=max_pages, value=1, step=1)

start = (int(page) - 1) * int(page_size)
end = min(start + int(page_size), total)
st.caption(f"Rows {start + 1}-{end} of {total}")

df_page = df.iloc[start:end].copy()

if not df_page.empty:
    st.dataframe(
        df_page,
        column_order=["match_label", "match_score", "url", "title", "_company", "_date_added", "location_clean", "match_reasons"],
        column_config={
            "match_label": st.column_config.TextColumn("Fit", help="Strong/Good/Okay/Weak"),
            "match_score": st.column_config.ProgressColumn("Score", format="%d", min_value=-50, max_value=50),
            "url": st.column_config.LinkColumn("Apply", display_text="Open"),
            "title": "Role",
            "_company": "Company",
            "_date_added": "Added",
            "location_clean": "Location",
            "match_reasons": st.column_config.TextColumn("Why", help="Matched keywords/seniority/location"),
        },
        width="stretch",
        hide_index=True,
        height=720,
    )
else:
    st.write("No matching jobs found with current filters.")
