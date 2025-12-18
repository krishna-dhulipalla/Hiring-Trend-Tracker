import streamlit as st
import altair as alt
import pandas as pd

def apply_custom_css():
    """
    Applies custom CSS to enhance the dashboard aesthetics.
    """
    st.markdown("""
        <style>
        /* Card Styling */
        .metric-card {
            background-color: #1E1E1E;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .metric-label {
            font-size: 0.85rem;
            color: #aaa;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: #fff;
            margin: 4px 0;
        }
        .metric-delta {
            font-size: 0.9rem;
            display: flex;
            align-items: center;
        }
        .metric-delta.positive { color: #4CAF50; }
        .metric-delta.negative { color: #F44336; }
        
        /* Diff Card Styling */
        .diff-card {
            background-color: #262730;
            border-left: 4px solid #555;
            border-radius: 4px;
            padding: 12px;
            margin-bottom: 10px;
        }
        .diff-card.added { border-left-color: #4CAF50; }
        .diff-card.removed { border-left-color: #F44336; }
        .diff-card.changed { border-left-color: #FFC107; }
        
        .job-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 4px;
            display: block;
            color: #EEE;
            text-decoration: none;
        }
        .job-meta {
            font-size: 0.85rem;
            color: #BBB;
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            align-items: center;
        }
        .chip {
            background: #333;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.8rem;
        }
        .chip.us { background: #1E3A8A; color: #93C5FD; }
        .chip.senior { background: #371B58; color: #E9D5FF; }
        </style>
    """, unsafe_allow_html=True)

def render_metric_card(label, value, delta=None, delta_color="normal"):
    """
    Renders a styled metric card using HTML/CSS for more control than st.metric.
    delta_color: "normal" (green=pos, red=neg) or "inverse" (red=pos, green=neg)
    """
    delta_html = ""
    if delta is not None:
        is_pos = delta >= 0
        if delta_color == "inverse":
            color_class = "negative" if is_pos else "positive"
        else:
            color_class = "positive" if is_pos else "negative"
            
        sign = "+" if is_pos else ""
        arrow = "↑" if is_pos else "↓"
        delta_html = f'<div class="metric-delta {color_class}">{arrow} {sign}{delta}</div>'

    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
        </div>
    """, unsafe_allow_html=True)

def render_timeline_chart(df, x_col, y_col, category_col=None, title="Title"):
    """
    Renders an Altair chart.
    df: DataFrame
    x_col: date column
    y_col: numeric column
    category_col: column for color
    """
    base = alt.Chart(df).encode(
        x=alt.X(x_col, title="Date", axis=alt.Axis(format="%b %d")),
        tooltip=[x_col, y_col]
    )
    
    if category_col:
        chart = base.mark_bar().encode(
            y=alt.Y(y_col, title=title),
            color=category_col,
            tooltip=[x_col, y_col, category_col]
        )
    else:
        chart = base.mark_line(point=True).encode(
            y=alt.Y(y_col, title=title)
        )
        
    st.altair_chart(chart, width="stretch")

def render_job_card(job, type="added"):
    """
    Renders a job card for the diff viewer.
    type: "added", "removed", "changed"
    """
    title = job.get('title', 'Unknown Title')
    url = job.get('url', '#')
    locations = job.get('locations', [])
    
    # Extract meta tags
    is_us = False
    is_remote = False
    loc_str_list = []
    
    for loc in locations:
        if isinstance(loc, dict):
            name = loc.get('name', '')
            if loc.get('is_us'): is_us = True
            if loc.get('is_remote'): is_remote = True
            loc_str_list.append(name)
        else:
            loc_str_list.append(str(loc))
            
    loc_display = ", ".join(loc_str_list[:2])
    if len(loc_str_list) > 2:
        loc_display += f" +{len(loc_str_list)-2}"
        
    # Seniority check (simple keyword based for visual tag)
    title_lower = title.lower()
    is_senior = any(x in title_lower for x in ['senior', 'staff', 'principal', 'lead', 'director'])
    
    tags = []
    if is_us: tags.append('<span class="chip us">US</span>')
    if is_remote: tags.append('<span class="chip">Remote</span>')
    if is_senior: tags.append('<span class="chip senior">Senior+</span>')
    
    tags_html = "".join(tags)
    
    st.markdown(f"""
        <div class="diff-card {type}">
            <a href="{url}" target="_blank" class="job-title">{title}</a>
            <div class="job-meta">
                <span>📍 {loc_display}</span>
                {tags_html}
            </div>
        </div>
    """, unsafe_allow_html=True)
