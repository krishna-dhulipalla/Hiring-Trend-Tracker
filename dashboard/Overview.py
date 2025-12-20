import streamlit as st
import pandas as pd

import data_access as da
from components import apply_custom_css

st.set_page_config(
    page_title="Momentum Board",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_css()

WEEKDAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _weekday_name(i: int | None) -> str:
    if i is None:
        return "—"
    if 0 <= int(i) <= 6:
        return WEEKDAY[int(i)]
    return "—"


def _go_company(slug: str) -> None:
    st.session_state["selected_company"] = slug
    st.switch_page("pages/02_Company_Detail.py")


st.title("Momentum Board")
st.caption("Weekly focus: who is moving, why, and what that implies for timing.")

with st.sidebar:
    st.header("Board Controls")
    lookback_days = st.slider("Lookback window (days)", 7, 21, 7)
    include_starred_in_movers = st.checkbox("Starred always in Movers", value=True)
    starred_only = st.checkbox("Starred only", value=False)
    score_min, score_max = st.slider("Momentum score range", 0, 100, (0, 100))
    state_filter = st.multiselect(
        "Momentum state",
        ["Accelerating", "Steady", "Slowing", "Freezing", "Volatile", "Stable"],
        default=[],
    )
    sort_by = st.selectbox("Sort", ["Momentum score", "Net change", "Open now", "Median lifespan"], index=0)
    search = st.text_input("Search company", placeholder="e.g. Stripe")

board = da.get_momentum_board(lookback_days=lookback_days)
if board.empty:
    st.error("No board data found yet. Run the scraper, or run `scripts/backfill_analytics.py` to populate signals from existing snapshots.")
    st.stop()

pulse = da.get_global_pulse(board)

# Apply filters
df = board.copy()
if starred_only and "is_starred" in df.columns:
    df = df[df["is_starred"] == True]
if search:
    q = search.strip().lower()
    df = df[df["name"].str.lower().str.contains(q, na=False)]
df = df[(df["momentum_score"] >= score_min) & (df["momentum_score"] <= score_max)]
if state_filter and "momentum_state" in df.columns:
    df = df[df["momentum_state"].isin(state_filter)]

if sort_by == "Momentum score":
    df = df.sort_values(["is_mover", "momentum_score"], ascending=[False, False])
elif sort_by == "Net change":
    df = df.sort_values(["is_mover", "net_window"], ascending=[False, False])
elif sort_by == "Open now":
    df = df.sort_values(["is_mover", "open_jobs_count"], ascending=[False, False])
else:
    df = df.sort_values(["is_mover", "median_days"], ascending=[False, True], na_position="last")

# Movers vs others
movers = df[df["is_mover"] == 1].copy()
others = df[df["is_mover"] != 1].copy()
if include_starred_in_movers and "is_starred" in df.columns:
    movers = pd.concat([movers, others[others["is_starred"] == True]], ignore_index=True).drop_duplicates(subset=["company_slug"])
    others = others[~others["company_slug"].isin(set(movers["company_slug"]))]

# ------------------------------------------------------------
# Top answers (what you see on open)
# ------------------------------------------------------------
col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Movers (this week)", pulse["movers"])
col_b.metric("Open roles now", pulse["total_open_now"])
col_c.metric(f"Net change ({lookback_days}d)", pulse["total_net"])
col_d.metric("Booming / Freezing", f"{pulse['booming']} / {pulse['freezing']}")

urgent = 0
if not movers.empty and "timing_hint" in movers.columns:
    urgent = int(movers["timing_hint"].fillna("").str.contains("48h", case=False).sum())
st.caption(f"Timing implication: {urgent} mover(s) look fast-close (apply window ~48h).")

st.divider()

# ------------------------------------------------------------
# Section A — This Week: Movers (expanded)
# ------------------------------------------------------------
st.subheader("This Week: Movers")
st.caption("Meaningful momentum signals only; each row includes the why + timing hint.")

if movers.empty:
    st.info("No movers matched the current filters.")
else:
    for _, row in movers.iterrows():
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2.2, 2.3, 1.4, 2.1, 1.0])

            name = row.get("name", row.get("company_slug"))
            star = "★ " if bool(row.get("is_starred", False)) else ""
            label = row.get("momentum_label") or "—"
            state = row.get("momentum_state") or "—"

            c1.markdown(f"### {star}{name}")
            c1.caption(f"{label} • {state} • score {row.get('momentum_score', 0):.0f}")

            c2.markdown(
                f"""
                **Open now:** {int(row.get('open_jobs_count', 0))}  
                **Net ({lookback_days}d):** {int(row.get('net_window', 0)):+d}  
                **Added / Removed:** {int(row.get('added_window', 0))} / {int(row.get('removed_window', 0))}
                """
            )

            median_days = row.get("median_days")
            median_str = f"{median_days:.0f}d" if pd.notna(median_days) else "—"
            median_open_age = row.get("median_open_age_days")
            open_age_str = f"{median_open_age:.0f}d" if pd.notna(median_open_age) else "—"
            c3.markdown(
                f"""
                **Median lifespan:** {median_str}  
                **Median age (open):** {open_age_str}  
                **Post day:** {_weekday_name(row.get('best_post_weekday'))}  
                **Removal day:** {_weekday_name(row.get('best_remove_weekday'))}
                """
            )

            c4.markdown(f"**Timing hint:** {row.get('timing_hint') or '—'} ({row.get('timing_confidence') or 'low'})")
            c4.caption(row.get("mover_reason") or "")

            headline = row.get("headline_title")
            url = row.get("headline_url")
            if headline and url:
                c4.markdown(f"[{headline}]({url})")
            elif headline:
                c4.caption(headline)

            if c5.button("Open", key=f"open_{row['company_slug']}", width="stretch"):
                _go_company(row["company_slug"])

# ------------------------------------------------------------
# Section B — All Others (collapsed by default)
# ------------------------------------------------------------
st.divider()
st.subheader("All Others")
st.caption("Nobody disappears; movers get attention. Expand a group to browse the rest.")

if others.empty:
    st.info("No remaining companies matched the current filters.")
else:
    others["group"] = others["momentum_label"].fillna("Quiet")
    group_order = ["Stable", "Quiet", "Volatile", "Freezing", "Booming"]
    for grp in group_order:
        grp_df = others[others["group"] == grp].copy()
        if grp_df.empty:
            continue
        with st.expander(f"{grp} ({len(grp_df)})", expanded=False):
            show = grp_df[[
                "name",
                "open_jobs_count",
                "net_window",
                "momentum_score",
                "timing_hint",
                "median_days",
            ]].copy()
            show = show.rename(columns={
                "name": "Company",
                "open_jobs_count": "Open now",
                "net_window": f"Net {lookback_days}d",
                "momentum_score": "Score",
                "timing_hint": "Timing",
                "median_days": "Median lifespan (d)",
            })
            st.dataframe(show, width="stretch", hide_index=True)

            open_slug = st.selectbox(
                "Open company",
                options=grp_df["company_slug"].tolist(),
                format_func=lambda s: grp_df.loc[grp_df["company_slug"] == s, "name"].iloc[0],
                key=f"open_select_{grp}",
            )
            if st.button("Open selected", key=f"open_selected_{grp}"):
                _go_company(open_slug)
