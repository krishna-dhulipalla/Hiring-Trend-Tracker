import streamlit as st
import sys
import os
import json

# Add parent directory to path to import peers
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import data_access as da
import components as ui
from scoring import calculate_role_match_score

st.set_page_config(page_title="Diff Viewer", page_icon="🔍", layout="wide")
ui.apply_custom_css()

st.title("Diff Viewer 🔍")

# --- Selection Logic with Session State Support ---
col1, col2 = st.columns([1, 1])

# Check for redirect params
pre_slug = st.session_state.get("diff_viewer_slug")
pre_date = st.session_state.get("diff_viewer_date")

with col1:
    companies = da.get_companies()
    if not companies:
        st.error("No companies found.")
        st.stop()
    slugs = sorted([c["slug"] for c in companies])
    
    ix = 0
    if pre_slug and pre_slug in slugs:
        ix = slugs.index(pre_slug)
        # Clear state
        st.session_state["diff_viewer_slug"] = None
        
    selected_slug = st.selectbox("Select Company", slugs, index=ix)

with col2:
    # Get available dates
    df_dates = da.get_job_diffs_daily(company_slug=selected_slug)
    if not df_dates.empty:
        available_dates = sorted(df_dates["date"].unique().tolist(), reverse=True)
    else:
        # Fallback to file scan
        available_dates = da.get_available_diff_dates(selected_slug)
    
    if available_dates:
        d_ix = 0
        if pre_date and pre_date in available_dates:
            d_ix = available_dates.index(pre_date)
            # Clear state
            st.session_state["diff_viewer_date"] = None
            
        selected_date = st.selectbox("Select Date", available_dates, index=d_ix)
    else:
        selected_date = None
        st.warning("No diff history found for this company.")

if not selected_date:
    st.info("Select a company and date to view changes.")
    st.stop()

# --- Load Diff ---
diff_data = da.get_diff_for(selected_slug, selected_date)

if not diff_data:
    st.error(f"Could not load diff file for {selected_slug} on {selected_date}.")
    st.stop()

# --- Display Diff ---
summary = diff_data.get("summary", {})
# Support top-level or details-nested
added_list = diff_data.get("added", [])
if not added_list:
    added_list = diff_data.get("details", {}).get("added", [])
    
removed_list = diff_data.get("removed", [])
if not removed_list:
    removed_list = diff_data.get("details", {}).get("removed", [])
    
changed_list = diff_data.get("changed", [])
if not changed_list:
    changed_list = diff_data.get("details", {}).get("changed", [])

# Top Metrics
m1, m2, m3, m4 = st.columns(4)
with m1: ui.render_metric_card("Added", summary.get("added", 0), delta_color="normal")
with m2: ui.render_metric_card("Removed", summary.get("removed", 0))
with m3: ui.render_metric_card("Changed", summary.get("changed", 0))
with m4: ui.render_metric_card("Senior+ Added", summary.get("senior_plus_added", 0))

st.divider()

col_diffs, col_news = st.columns([3, 1])

with col_diffs:
    tab_added, tab_removed, tab_changed = st.tabs(["Added 🟢", "Removed 🔴", "Changed 🟡"])
    
    with tab_added:
        if added_list:
            # Score and Sort
            scored_jobs = []
            for job in added_list:
                match = calculate_role_match_score(job, days_ago_added=0)
                scored_jobs.append((job, match))
            
            # Sort by score desc
            scored_jobs.sort(key=lambda x: x[1]["score"], reverse=True)
            
            # Filter Toggles
            filter_mode = st.radio("Show matches:", ["Strong/Good", "All"], horizontal=True, index=1)
            
            count_shown = 0
            for job, match in scored_jobs:
                if filter_mode == "Strong/Good" and match["label"] in ["Okay", "Weak"]:
                    continue
                
                count_shown += 1
                
                # Render custom card with match info
                with st.container(border=True):
                    c_head, c_badge = st.columns([3, 1])
                    c_head.markdown(f"#### [{job['title']}]({job.get('url', '#')})")
                    
                    # Badge Color
                    b_color = "green" if match["label"] == "Strong" else "blue" if match["label"] == "Good" else "gray"
                    c_badge.markdown(f":{b_color}[**{match['label']}** ({match['score']})]")
                    
                    st.caption(f"📍 {job.get('location_display', 'Unknown')} • {job.get('seniority', 'Mid')} • {job.get('discipline', 'Other')}")
                    
                    if match["match_reasons"]:
                        st.markdown(f"**Why**: {', '.join(match['match_reasons'])}")
                        
            if count_shown == 0:
                st.info("No jobs match the current filter.")
                
        else:
            st.write("No jobs added.")
            
    with tab_removed:
        if removed_list:
            for job in removed_list:
                ui.render_job_card(job, type="removed")
        else:
            st.write("No jobs removed.")
            
    with tab_changed:
        if changed_list:
            for item in changed_list:
                key = item.get("job_key", "Unknown Job")
                changes = item.get("changes", {})
                
                with st.container(border=True):
                    st.markdown(f"**{key}**")
                    for field, vals in changes.items():
                        old = vals.get("old")
                        new = vals.get("new")
                        st.markdown(f"- **{field}**: `{old}` ➝ `{new}`")
        else:
            st.write("No jobs changed.")

with col_news:
    st.subheader("News Context")
    news_df = da.get_company_news_daily(company_slug=selected_slug, start_date=selected_date, end_date=selected_date)
    if not news_df.empty:
         # It's possible to have multiple rows for same date if DB schema allowed, but here PK is (slug, date)
         row = news_df.iloc[0]
         if row["article_count"] > 0:
            if row["has_major_event"]:
                st.warning(f"Major Event: {row['major_event_types']}")
            
            headline = row["top_headline_title"]
            url = row["top_headline_url"]
            if headline:
                st.markdown(f"**Headline**: [{headline}]({url})" if url else f"**Headline**: {headline}")
         else:
             st.caption("No news counts recorded.")
    else:
        st.caption("No news data found for this date.")
