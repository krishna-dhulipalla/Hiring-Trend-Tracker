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
# Sidebar & Configuration
# -------------------------------------------------------------------------
with st.sidebar:
    st.header("Search Parameters")
    days_back = st.slider("Lookback Window (Days)", 7, 60, 14)
    st.caption(f"Analyzing trends over the last {days_back} days.")

# -------------------------------------------------------------------------
# Data Preparation
# -------------------------------------------------------------------------
# Metric 1: Global Stats
global_stats = da.get_global_stats(days_back=days_back)

# Prepare Company Data for Opportunity Board
# We need to iterate all companies and compute scores
all_companies = da.get_all_companies()
scored_companies = []

for company in all_companies:
    slug = company["slug"]
    
    # 1. Get Hiring Stats for window
    df_diffs = da.get_job_diffs_daily(slug)
    if df_diffs.empty:
        stats = {"added_total": 0, "net_change": 0, "senior_plus_added_count": 0}
    else:
        # Filter by date
        cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        mask = df_diffs["date"] >= cutoff
        filtered = df_diffs[mask]
        stats = {
            "added_total": filtered["added_count"].sum(),
            "net_change": filtered["added_count"].sum() - filtered["removed_count"].sum(),
            "senior_plus_added_count": filtered["senior_plus_added_count"].sum()
        }
        
    # 2. Get News Stats for window
    df_news = da.get_company_news_daily(slug)
    if df_news.empty:
        news_counts = {}
    else:
        cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        mask = df_news["date"] >= cutoff
        filtered_news = df_news[mask]
        news_counts = {
            "funding": filtered_news["funding_count"].sum(),
            "product": filtered_news["product_count"].sum(),
            "ai_announcement": filtered_news["ai_announcement_count"].sum(),
            "layoff": filtered_news["layoff_count"].sum()
        }
        
    # 3. Calculate Score
    score_data = calculate_company_opportunity_score(stats, news_counts)
    
    scored_companies.append({
    "name": company.get("name", company["slug"].replace("-", " ").title()),
        "slug": slug,
        "score": score_data["score"],
        "label": score_data["label"],
        "reason": score_data["reason"],
        "added": stats["added_total"],
        "net": stats["net_change"],
        "mid_level": max(0, stats["added_total"] - stats["senior_plus_added_count"]),
        "news_counts": news_counts
    })

# Sort by Score Descending
scored_companies.sort(key=lambda x: x["score"], reverse=True)
top_opportunities = scored_companies[:8] # Top 8

# -------------------------------------------------------------------------
# Feature E: Weekly Playbook (Top of page)
# -------------------------------------------------------------------------
st.subheader("Your Weekly Playbook 📖")

# 1. Priority Companies
priorities = [f"{c['name']} ({c['reason']})" for c in top_opportunities[:3]]
priority_str = "; ".join(priorities) if priorities else "None yet"

# 2. Watchlist (High news but maybe low score? or just next 3)
watchlist = [c["name"] for c in scored_companies[3:6]]
watchlist_str = ", ".join(watchlist) if watchlist else "None"

col_pb1, col_pb2, col_pb3 = st.columns(3)
with col_pb1:
    st.info(f"**Focus Here**: {priority_str}")
with col_pb2:
    st.warning(f"**Watchlist**: {watchlist_str}")
with col_pb3:
    st.success(f"**Market Pulse**: {global_stats['total_added']} new roles in {days_back} days.")

st.divider()

# -------------------------------------------------------------------------
# Feature A: My Opportunity Board
# -------------------------------------------------------------------------
st.subheader("Top Opportunities (Based on your profile)")

# Display as grid of cards
cols = st.columns(4)
for i, comp in enumerate(top_opportunities):
    with cols[i % 4]:
        with st.container(border=True):
            st.markdown(f"**{comp['name']}**")
            st.caption(f"{comp['label']} (Score: {comp['score']})")
            
            # Mini stats
            c1, c2 = st.columns(2)
            c1.metric("Added", comp["added"])
            c2.metric("Net", comp["net"])
            
            # News Badges
            badges = []
            if comp["news_counts"].get("funding", 0) > 0: badges.append("💰")
            if comp["news_counts"].get("ai_announcement", 0) > 0: badges.append("🤖")
            if comp["news_counts"].get("layoff", 0) > 0: badges.append("⚠️")
            
            if badges:
                st.markdown(" ".join(badges))
            
            if st.button(f"Analyze", key=f"btn_{comp['slug']}"):
                # Set session state for Page 2
                st.session_state["selected_company"] = comp["slug"]
                st.switch_page("pages/02_Company_Detail.py")

st.divider()

# -------------------------------------------------------------------------
# Advanced Metrics / Generic Leaderboard (Moved to expander)
# -------------------------------------------------------------------------
with st.expander("Show Advanced Market Metrics & Raw Leaderboard", expanded=False):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Jobs Added", global_stats["total_added"])
    col2.metric("Total Jobs Removed", global_stats["total_removed"])
    col3.metric("Net Change", global_stats["net_change"])
    col4.metric("Companies Tracked", global_stats["active_companies"])

    st.subheader("Hiring Leaderboard")
    leaderboard = da.get_leaderboard(days_back=days_back)
    
    st.dataframe(
        leaderboard,
        column_config={
            "company_slug": "Company",
            "added_count": st.column_config.ProgressColumn("Added", format="%d", min_value=0, max_value=int(max(leaderboard["added_count"].max(), 1))),
            "net_change": st.column_config.NumberColumn("Net Change", format="%d")
        },
        use_container_width=True,
        hide_index=True
    )
    
    st.subheader("Market Trend")
    trend_df = da.get_market_trend(days_back=days_back)
    if not trend_df.empty:
        chart = alt.Chart(trend_df).mark_line(point=True).encode(
            x='date:T',
            y='added_count:Q',
            tooltip=['date', 'added_count', 'removed_count']
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Not enough data for trend chart.")
