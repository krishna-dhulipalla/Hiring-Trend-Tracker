import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import data_access as da
from scoring import calculate_company_opportunity_score, USER_PROFILE
from components import render_metric_card as metrics_card, apply_custom_css

st.set_page_config(page_title="Market Overview", page_icon="📈", layout="wide")
apply_custom_css()

st.title("My Opportunity Radar 🎯")
st.markdown("Your personalized pulse on the job market.")

# -------------------------------------------------------------------------
# Sidebar
# -------------------------------------------------------------------------
with st.sidebar:
    st.header("Search Parameters")
    days_back = st.slider("Lookback Window (Days)", 7, 60, 14)
    st.caption(f"Analyzing trends over the last {days_back} days.")

# -------------------------------------------------------------------------
# Data Preparation
# -------------------------------------------------------------------------
global_stats = da.get_global_stats(days_back=days_back)
rich_companies = da.get_all_companies_rich() # Includes open_jobs_count and is_starred

scored_companies = []

for company in rich_companies:
    slug = company["slug"]
    open_now = company.get("open_jobs_count", 0)
    is_starred = company.get("is_starred", False)
    
    # 1. Get Hiring Stats
    df_diffs = da.get_job_diffs_daily(slug)
    if df_diffs.empty:
        stats = {"added_total": 0, "net_change": 0, "senior_plus_added_count": 0}
    else:
        cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        mask = df_diffs["date"] >= cutoff
        filtered = df_diffs[mask]
        stats = {
            "added_total": filtered["added_count"].sum(),
            "net_change": filtered["added_count"].sum() - filtered["removed_count"].sum(),
            "senior_plus_added_count": filtered["senior_plus_added_count"].sum()
        }
        
    # 2. Get News Stats
    df_news = da.get_company_news_daily(slug)
    if df_news.empty:
        news_counts = {}
    else:
        cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        mask = df_news["date"] >= cutoff
        filtered_news = df_news[mask]
        news_counts = {
            "funding": filtered_news["funding_count"].sum(),
            "ai_announcement": filtered_news["ai_announcement_count"].sum(),
            "layoff": filtered_news["layoff_count"].sum()
        }
        
    # 3. Score
    score_data = calculate_company_opportunity_score(stats, news_counts, open_now_count=open_now)
    
    scored_companies.append({
        "name": company["name"],
        "slug": slug,
        "is_starred": is_starred,
        "score": score_data["score"],
        "label": score_data["label"], # Hot/Warming/etc
        "reason": score_data["reason"],
        "breakdown": score_data["breakdown"],
        "open_now": open_now,
        "added": stats["added_total"],
        "net": stats["net_change"],
        "news_counts": news_counts
    })

# Sorting
scored_companies.sort(key=lambda x: x["score"], reverse=True)

# Split lists
opportunities = [c for c in scored_companies if c["open_now"] > 0]
# Limit to top 8 opportunities
top_opportunities = opportunities[:8]

# Watchlist: Starred companies
watchlist_list = [c for c in scored_companies if c["is_starred"]]

# -------------------------------------------------------------------------
# Feature E: Weekly Playbook (Short & Actionable)
# -------------------------------------------------------------------------
st.subheader("Weekly Playbook 📖")
col_pb1, col_pb2, col_pb3 = st.columns(3)

with col_pb1:
    st.markdown("##### 🚀 Apply Now")
    if top_opportunities:
        for c in top_opportunities[:5]:
            st.markdown(f"- **{c['name']}**: {c['open_now']} open • {c['label']}")
    else:
        st.caption("No active opportunities found.")

with col_pb2:
    st.markdown("##### ⭐ Watchlist")
    if watchlist_list:
        for c in watchlist_list:
            st.markdown(f"- **{c['name']}**: {c['open_now']} open • {c['label']}")
    else:
        st.caption("No starred companies.")

with col_pb3:
    st.markdown("##### 🌍 Market Pulse")
    st.markdown(f"- **Added**: {global_stats['total_added']}")
    st.markdown(f"- **Net**: {global_stats['net_change']}")
    st.markdown(f"- **Active**: {global_stats['active_companies']}")

st.divider()

# -------------------------------------------------------------------------
# Feature A: Top Opportunities
# -------------------------------------------------------------------------
st.subheader("Top Opportunities (Actionable)")
if not top_opportunities:
    st.info("No companies have open filtered jobs right now. Check your filters or backfill data.")
else:
    cols = st.columns(4)
    for i, comp in enumerate(top_opportunities):
        with cols[i % 4]:
            with st.container(border=True):
                # Header
                st.markdown(f"**{comp['name']}**")
                
                # Badges
                lbl_color = "red" if "Hot" in comp['label'] else "orange" if "Warming" in comp['label'] else "gray"
                st.markdown(f":{lbl_color}[{comp['label']} (Score: {comp['score']})]")
                
                # Metrics
                m1, m2 = st.columns(2)
                m1.metric("Open Now", comp["open_now"])
                m2.metric("Added", comp["added"], delta=int(comp["net"]))
                
                # Breakdown helper
                with st.expander("Why?", expanded=False):
                    for reason in comp["breakdown"]:
                        st.markdown(f"- {reason}")
                
                if st.button("Analyze", key=f"btn_opp_{comp['slug']}"):
                    st.session_state["selected_company"] = comp["slug"]
                    st.switch_page("pages/02_Company_Detail.py")

# -------------------------------------------------------------------------
# Watchlist Section (Explicit)
# -------------------------------------------------------------------------
if watchlist_list:
    st.divider()
    st.subheader("Starred Watchlist ⭐")
    w_cols = st.columns(4)
    for i, comp in enumerate(watchlist_list):
        with w_cols[i % 4]:
            with st.container(border=True):
                st.markdown(f"**{comp['name']}**")
                st.caption(f"{comp['open_now']} jobs open")
                if st.button("Analyze", key=f"btn_watch_{comp['slug']}"):
                    st.session_state["selected_company"] = comp["slug"]
                    st.switch_page("pages/02_Company_Detail.py")

st.divider()

# -------------------------------------------------------------------------
# Advanced Metrics
# -------------------------------------------------------------------------
with st.expander("Show Raw Leaderboard", expanded=False):
    leaderboard = da.get_leaderboard(days_back=days_back)
    st.dataframe(leaderboard, use_container_width=True)
