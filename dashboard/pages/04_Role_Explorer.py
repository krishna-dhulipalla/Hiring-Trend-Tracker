import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime

# Add parent directory to path to import peers
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
        default=["Strong", "Good"] # Default to high signal
    )

with col3:
    companies = da.get_companies()
    slugs = sorted([c["slug"] for c in companies]) if companies else []
    selected_companies = st.multiselect("Filter by Company", slugs)

search_query = st.text_input("Search (refine within results)", placeholder="e.g. 'platform' or 'remote'")

# --- Fetch & Score Data ---
with st.spinner(f"Scanning & scoring roles from last {days_back} days..."):
    # get_recent_added_jobs returns a list of dictionaries
    all_jobs = da.get_recent_added_jobs(days_back=days_back)
    
    scored_jobs = []
    today = datetime.now().date()
    
    for job in all_jobs:
        # Calculate days ago
        added_date_str = job.get("_date_added")
        days_ago = 0
        if added_date_str:
            try:
                added_dt = datetime.strptime(added_date_str, "%Y-%m-%d").date()
                days_ago = (today - added_dt).days
            except:
                pass
                
        match = calculate_role_match_score(job, days_ago_added=days_ago)
        
        # Enrich flattened dict for dataframe
        fl = job.copy()
        fl["match_score"] = match["score"]
        fl["match_label"] = match["label"]
        fl["match_reasons"] = ", ".join(match["match_reasons"])
        scored_jobs.append(fl)

# Convert to DataFrame
df = pd.DataFrame(scored_jobs)

if df.empty:
    st.info("No jobs found in the selected time range.")
    st.stop()

# --- Filtering ---
# 1. Match Strength
if match_filter:
    df = df[df["match_label"].isin(match_filter)]

# 2. Company Filter
if selected_companies:
    df = df[df["_company"].isin(selected_companies)]

# 3. Search Query
if search_query:
    q = search_query.lower()
    df["loc_str"] = df["locations"].apply(lambda x: str(x).lower())
    mask = (
        df["title"].str.lower().str.contains(q, na=False) | 
        df["_company"].str.lower().str.contains(q, na=False) |
        df["loc_str"].str.contains(q, na=False)
    )
    df = df[mask]

# --- Sorting ---
# Sort by Score Descending, then Date Descending
df = df.sort_values(by=["match_score", "_date_added"], ascending=[False, False])

# --- Display ---
st.caption(f"Showing **{len(df)}** matches.")

if not df.empty:
    # Custom rendering for list
    # We can use dataframe for dense view, but cards for "Personal" feel is better?
    # Let's stick to Dataframe for scannability, but add colored columns.
    
    # Configure columns
    st.dataframe(
        df,
        column_order=["match_label", "match_score", "title", "_company", "_date_added", "locations", "url"],
        column_config={
            "match_label": st.column_config.TextColumn("Fit", help="Strong/Good/Okay/Weak based on profile"),
            "match_score": st.column_config.ProgressColumn("Score", format="%d", min_value=-50, max_value=50),
            "title": "Role",
            "_company": "Company",
            "_date_added": "Added",
            "locations": "Location",
            "url": st.column_config.LinkColumn("Apply", display_text="LINK")
        },
        use_container_width=True,
        hide_index=True,
        height=800
    )
    
else:
    st.write("No matching jobs found with current filters.")
