import streamlit as st
import altair as alt
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import math

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import data_access as da
import components as ui
from scoring import classify_company_momentum

st.set_page_config(page_title="Company Detail", page_icon="🏢", layout="wide")
ui.apply_custom_css()

# --- Data Loading (Global Helpers) ---
rich_companies = da.get_all_companies_rich()
if not rich_companies:
    st.error("No companies found.")
    st.stop()

# Sort: Starred first, then name
rich_companies.sort(key=lambda x: (not x["is_starred"], x["name"]))
slugs = [c["slug"] for c in rich_companies]
slug_map = {c["slug"]: c for c in rich_companies}

# --- State Management ---
if "selected_company" not in st.session_state:
    st.session_state["selected_company"] = slugs[0] if slugs else None
elif st.session_state["selected_company"] not in slugs:
    st.session_state["selected_company"] = slugs[0] if slugs else None

def format_func(slug):
    c = slug_map[slug]
    prefix = "⭐ " if c["is_starred"] else ""
    return f"{prefix}{c['name']}"

# Title
col_title, col_sel = st.columns([2, 2])
with col_title:
    st.title("Company Detail 🏢")

with col_sel:
    selected_slug = st.selectbox(
        "Select Company", 
        slugs, 
        format_func=format_func,
        key="selected_company"
    )

# --- Controls ---
c_star, c_days, c_pad = st.columns([1, 1, 3])
with c_star:
    is_starred = slug_map[selected_slug]["is_starred"]
    btn_label = "Unstar" if is_starred else "Star"
    if st.button(btn_label, use_container_width=True):
        da.toggle_star(selected_slug)
        st.rerun()

with c_days:
    days_choice = st.selectbox("Lookback", [30, 90, 180], index=0)

end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=days_choice)).strftime("%Y-%m-%d")

# --- Fetch Data ---
df_diff = da.get_job_diffs_daily(company_slug=selected_slug, start_date=start_date, end_date=end_date)
df_news = da.get_company_news_daily(company_slug=selected_slug, start_date=start_date, end_date=end_date)
open_now = da.get_open_job_count(selected_slug) 

# --- Header Metrics ---
total_added = df_diff["added_count"].sum() if not df_diff.empty else 0
total_removed = df_diff["removed_count"].sum() if not df_diff.empty else 0
net = total_added - total_removed
senior_added = df_diff["senior_plus_added_count"].sum() if not df_diff.empty else 0

momentum = classify_company_momentum({
    "added_total": total_added,
    "net_change": net
}, open_now_count=open_now)

st.divider()
st.markdown(f"### {slug_map[selected_slug]['name']} • {momentum}")

m1, m2, m3, m4 = st.columns(4)
with m1: ui.render_metric_card("Open Jobs", open_now, delta_color="normal")
with m2: ui.render_metric_card("Added", total_added, delta_color="normal")
with m3: ui.render_metric_card("Net Change", net, delta_color="normal")
with m4: ui.render_metric_card("Senior+ Added", senior_added)

# --- Spike Button ---
if not df_diff.empty:
    max_added_row = df_diff.loc[df_diff["added_count"].idxmax()]
    max_count = max_added_row["added_count"]
    if max_count > 0:
        max_date = str(max_added_row["date"])
        def go_to_spike():
            st.session_state["diff_viewer_slug"] = selected_slug
            st.session_state["diff_viewer_date"] = max_date
        
        st.caption(f"Biggest hiring spike: {max_date} (+{max_count})")
        if st.button("Inspect Spike", on_click=go_to_spike):
            st.switch_page("pages/03_Diff_Viewer.py")

st.divider()

# --- Integrated Timeline Chart ---
st.subheader("Hiring Activity & News")

if not df_diff.empty:
    chart_df = df_diff.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"])
    chart_df = chart_df.sort_values("date", ascending=True)
    
    if "changed_count" not in chart_df.columns:
        chart_df["changed_count"] = 0
        
    # 1. Back-calculate Total Open History (Line Layer)
    total_net_in_window = (chart_df["added_count"] - chart_df["removed_count"]).sum()
    initial_open = open_now - total_net_in_window
    chart_df["daily_net"] = chart_df["added_count"] - chart_df["removed_count"]
    chart_df["total_open"] = initial_open + chart_df["daily_net"].cumsum()
    
    # 2. Prepare Stacked Data (Negative Removed)
    plot_data = []
    # Helper to track max height for icon placement
    # We map date -> height
    height_map = {}
    
    for _, row in chart_df.iterrows():
        d = row["date"]
        # Calculate positive height for stacking icons
        pos_height = row["added_count"] + row["changed_count"]
        # If no positive bars, we might want to float it above 0 or above the line?
        # Let's verify line height.
        line_height = row["total_open"]
        # Place icon a bit above the highest element (Bar or Line)
        # Actually, standard UX: Place above the positive stack if exists, else 0.
        icon_y = max(pos_height, 0)
        height_map[d] = icon_y
        
        plot_data.append({"date": d, "type": "Added", "count": row["added_count"], "order": 1})
        plot_data.append({"date": d, "type": "Changed", "count": row["changed_count"], "order": 2})
        plot_data.append({"date": d, "type": "Removed", "count": -row["removed_count"], "order": 0})
        
    df_plot = pd.DataFrame(plot_data)
    
    # 3. Prepare News Icons
    icon_data = []
    if not df_news.empty:
        for _, row in df_news.iterrows():
            if row["article_count"] > 0:
                dt = pd.to_datetime(row["date"])
                if dt in height_map:
                    base_y = height_map[dt]
                else:
                    base_y = 0 # Should match date exists in chart_df mostly
                
                # Determine Category & Icon
                # Simple keyword matching on headline or major_event_types
                # Categories: Layoff, Funding, AI, Earnings, General
                hl = (row["top_headline_title"] or "").lower()
                evt = (row["major_event_types"] or "").lower()
                
                category = "General News"
                icon = "📰"
                
                if "layoff" in hl or "reduction" in hl or "cut" in hl:
                    category = "Layoff/Cuts"
                    icon = "📉"
                elif "funding" in hl or "raise" in hl or "series" in hl:
                    category = "Funding"
                    icon = "💰"
                elif "ai " in hl or "intelligence" in hl or "gpt" in hl:
                    category = "AI Update"
                    icon = "🤖"
                elif "earning" in hl or "revenue" in hl or "profit" in hl:
                    category = "Earnings"
                    icon = "📊"
                
                # Offset Y slightly for visual clearance
                # We need to render this.
                
                icon_data.append({
                    "date": dt,
                    "category": category, # For Legend
                    "icon": icon,         # For Text Mark
                    "y_pos": base_y + (base_y * 0.1) + 5, # 10% + 5px buffer
                    "headline": row["top_headline_title"],
                    "url": row["top_headline_url"]
                })

    df_icons = pd.DataFrame(icon_data)
    
    # --- Layer 1: Stacked Bars ---
    base = alt.Chart(df_plot).encode(x=alt.X("date:T", axis=alt.Axis(format="%b %d", title=None)))
    
    bars = base.mark_bar().encode(
        y=alt.Y("count:Q", title=None), # Axis title via line or unified?
        color=alt.Color("type:N", 
                        scale=alt.Scale(domain=["Added", "Changed", "Removed"], 
                                      range=["#10b981", "#f59e0b", "#ef4444"]),
                        legend=alt.Legend(title="Hiring Activity", orient="top")),
        tooltip=["date:T", "type", "count"]
    )
    
    # --- Layer 2: Open Jobs Line ---
    line = alt.Chart(chart_df).mark_line(color="#94a3b8", strokeWidth=2).encode(
        x="date:T",
        y=alt.Y("total_open:Q", axis=alt.Axis(title="Active Roles", titleColor="#64748b")),
        tooltip=[
            alt.Tooltip("date:T", title="Date"),
            alt.Tooltip("total_open:Q", title="Total Open"),
        ],
    )
    
    # --- Layer 3: News Icons ---
    if not df_icons.empty:
        # We use mark_text for Emojis
        # We need the 'category' for Legend?? 
        # Altair mark_text doesn't support 'color' legend easily if we use literal colored emojis.
        # But we can use a circle mark behind it for legend?
        # User asked for Legend max 5.
        
        # Let's use mark_point with custom shapes or just circles mapped to category colors
        # and render the emoji as labels?
        # Simpler: Just use Colored Circles for Legend and Emoji for Text.
        
        # Actually, user wants "icons for markers". Emojis are perfect.
        # We can map Category -> Emoji in the legend by using a dummy layer?
        # Let's just use Text Mark with 'text' channel mapped to 'icon'.
        # And use 'color' channel mapped to 'category' to force a legend, even if text manages color itself (emojis have color).
        # Actually text color overrides emoji color in some renderers.
        # Let's just assume Emojis stand alone and add a manual usage note/legend if needed.
        # OR: Use mark_point(shape) mapped to category.
        
        # User requested: "icons will stack top over the bar... clickable"
        
        icons = alt.Chart(df_icons).mark_text(size=20, baseline="bottom").encode(
            x="date:T",
            y=alt.Y("y_pos:Q"),
            text="icon", # The emoji
            href="url",
            tooltip=["date:T", "category", "headline"]
        )
        
        # To get a Legend for Categories:
        # We overlay invisible points?
        # Or just let the tooltip handle it. User asked for Legend.
        # Let's add an invisible Point layer mapped to Category to generate the Legend.
        
        legend_gen = alt.Chart(df_icons).mark_point(opacity=0).encode(
            x="date:T",
            y="y_pos:Q",
            color=alt.Color("category:N", legend=alt.Legend(title="News Type", orient="top", symbolType="circle"))
        )
        
        combined = alt.layer(bars, line, legend_gen, icons).resolve_scale(y="independent").properties(height=400)
    else:
        combined = alt.layer(bars, line).resolve_scale(y="independent").properties(height=400)
        
    st.altair_chart(combined.interactive(), use_container_width=True)

else:
    st.info("No hiring activity data found for selected window.")

# --- News List (Detailed) ---
st.subheader("News Feed")
if not df_news.empty:
     active_news = df_news[df_news["article_count"] > 0].sort_values("date", ascending=False)
     if not active_news.empty:
         for _, row in active_news.iterrows():
             with st.container(border=True):
                 st.markdown(f"**{row['date']}**")
                 if row["top_headline_url"]:
                     st.markdown(f"[{row['top_headline_title']}]({row['top_headline_url']})")
                 else:
                     st.write(row['top_headline_title'])
     else:
         st.write("No news found.")
