import streamlit as st
import altair as alt
import pandas as pd
from datetime import datetime, timedelta

import data_access as da
import components as ui

st.set_page_config(page_title="Company Intelligence", page_icon="🏢", layout="wide")
ui.apply_custom_css()

WEEKDAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _weekday_name(i: int | None) -> str:
    if i is None:
        return "—"
    if 0 <= int(i) <= 6:
        return WEEKDAY[int(i)]
    return "—"


def _safe_int(v, default=0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _latest_date(*dfs: pd.DataFrame) -> str | None:
    dates = []
    for df in dfs:
        if df is None or df.empty or "date" not in df.columns:
            continue
        try:
            dates.append(str(df["date"].max()))
        except Exception:
            continue
    return max(dates) if dates else None


rich = da.get_all_companies_rich()
if not rich:
    st.error("No companies found.")
    st.stop()

rich.sort(key=lambda x: (not x.get("is_starred", False), x.get("name", "")))
slug_map = {c["slug"]: c for c in rich}
slugs = list(slug_map.keys())

if "selected_company" not in st.session_state:
    st.session_state["selected_company"] = slugs[0]
elif st.session_state["selected_company"] not in slugs:
    st.session_state["selected_company"] = slugs[0]


with st.sidebar:
    st.header("Company")
    selected_slug = st.selectbox(
        "Select company",
        slugs,
        format_func=lambda s: ("★ " if slug_map[s].get("is_starred") else "") + slug_map[s].get("name", s),
        key="selected_company",
    )
    days_choice = st.selectbox("Window", [30, 90, 180], index=0)
    lookback_days = st.selectbox("Signal lookback", [7, 14], index=0)

end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=int(days_choice))).strftime("%Y-%m-%d")

# Star toggle
top_l, top_r = st.columns([3, 1])
with top_l:
    st.title(f"{slug_map[selected_slug].get('name', selected_slug)}")
with top_r:
    is_starred = slug_map[selected_slug].get("is_starred", False)
    btn_label = "Unstar" if is_starred else "Star"
    if st.button(btn_label, width="stretch"):
        da.toggle_star(selected_slug)
        st.rerun()

# Data
df_diff = da.get_job_diffs_daily(company_slug=selected_slug, start_date=start_date, end_date=end_date)
df_open = da.get_open_now_daily(company_slug=selected_slug, start_date=start_date, end_date=end_date)
df_sig = da.get_company_signals(company_slug=selected_slug, start_date=start_date, end_date=end_date, lookback_days=int(lookback_days))
df_news = da.get_company_news_daily(company_slug=selected_slug, start_date=start_date, end_date=end_date)

as_of_date = _latest_date(df_diff, df_open, df_sig) or end_date

# Header: latest signal summary
latest_sig = df_sig.iloc[0].to_dict() if not df_sig.empty else {}
label = latest_sig.get("momentum_label") or "—"
state = latest_sig.get("momentum_state") or "—"
score = latest_sig.get("momentum_score")
score_str = f"{float(score):.0f}" if score is not None else "—"

st.caption(f"As of {as_of_date} • {label} • {state} • score {score_str}")

# ------------------------------------------------------------
# Momentum timeline (open roles + adds/removes + rolling net)
# ------------------------------------------------------------
st.subheader("Momentum Timeline")

if df_diff.empty and df_open.empty:
    st.info("No hiring history found for this window yet.")
else:
    # Normalize dates
    if not df_diff.empty:
        df_diff = df_diff.copy()
        df_diff["date"] = pd.to_datetime(df_diff["date"])
        df_diff["net"] = df_diff["added_count"] - df_diff["removed_count"]
        df_diff = df_diff.sort_values("date")
        df_diff["rolling_net_7d"] = df_diff["net"].rolling(7, min_periods=1).sum()

    if not df_open.empty:
        df_open = df_open.copy()
        df_open["date"] = pd.to_datetime(df_open["date"])
        df_open = df_open.sort_values("date")

    base = alt.Chart(df_diff).encode(x=alt.X("date:T", axis=alt.Axis(title=None, format="%b %d")))

    bars_df = pd.DataFrame()
    if not df_diff.empty:
        bars_df = pd.concat(
            [
                df_diff[["date", "added_count"]].rename(columns={"added_count": "count"}).assign(kind="Added"),
                df_diff[["date", "removed_count"]].rename(columns={"removed_count": "count"}).assign(kind="Removed"),
            ],
            ignore_index=True,
        )
        bars_df.loc[bars_df["kind"] == "Removed", "count"] *= -1

    bars = alt.Chart(bars_df).mark_bar().encode(
        x=alt.X("date:T", axis=alt.Axis(title=None, format="%b %d")),
        y=alt.Y("count:Q", axis=alt.Axis(title="Adds / Removes (daily)", orient="left")),
        color=alt.Color("kind:N", scale=alt.Scale(domain=["Added", "Removed"], range=["#10b981", "#ef4444"]), legend=alt.Legend(orient="top")),
        tooltip=["date:T", "kind:N", "count:Q"],
    )

    layers = [bars]

    if not df_open.empty:
        open_line = alt.Chart(df_open).mark_line(color="#94a3b8", strokeWidth=2).encode(
            x="date:T",
            y=alt.Y(
                "open_now_count:Q",
                axis=alt.Axis(title="Open roles", orient="right", titleColor="#94a3b8", labelColor="#cbd5e1"),
            ),
            tooltip=[alt.Tooltip("date:T", title="Date"), alt.Tooltip("open_now_count:Q", title="Open now")],
        )
        layers.append(open_line)

    if not df_diff.empty:
        roll = alt.Chart(df_diff).mark_line(color="#f59e0b", strokeWidth=2).encode(
            x="date:T",
            y=alt.Y(
                "rolling_net_7d:Q",
                axis=alt.Axis(
                    title="Rolling net (7d)",
                    orient="right",
                    offset=60,
                    titleColor="#f59e0b",
                    labelColor="#cbd5e1",
                ),
            ),
            tooltip=[alt.Tooltip("date:T", title="Date"), alt.Tooltip("rolling_net_7d:Q", title="Rolling net (7d)")],
        )
        layers.append(roll)

    chart = alt.layer(*layers).resolve_scale(y="independent").properties(height=360)
    st.altair_chart(chart.interactive(), width="stretch")

    # Quick stats
    open_now_latest = _safe_int(df_open["open_now_count"].iloc[0], 0) if not df_open.empty else 0
    added_total = _safe_int(df_diff["added_count"].sum(), 0) if not df_diff.empty else 0
    removed_total = _safe_int(df_diff["removed_count"].sum(), 0) if not df_diff.empty else 0
    net_total = added_total - removed_total

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Open now", open_now_latest)
    m2.metric("Added (window)", added_total)
    m3.metric("Removed (window)", removed_total)
    m4.metric("Net (window)", net_total)

# ------------------------------------------------------------
# Lifespan + durability
# ------------------------------------------------------------
st.divider()
st.subheader("Lifespan (Role Durability)")

life = da.get_company_lifespan(selected_slug, as_of_date, window_days=180)
life_row = life.iloc[0].to_dict() if not life.empty else {}

median_open_age = life_row.get("median_open_age_days")
if median_open_age is None and life_row:
    # Fallback: older DB rows may have NULL until the next scrape/backfill.
    median_open_age = da.compute_median_open_age_days(selected_slug, as_of_date)

lc1, lc2, lc3, lc4 = st.columns(4)
lc1.metric("Median days open", _safe_int(life_row.get("median_days"), 0) if life_row.get("median_days") is not None else "—")
lc2.metric("Median age (open roles)", _safe_int(median_open_age, 0) if median_open_age is not None else "—")
lc3.metric("% close ≤7d", f"{(float(life_row.get('pct_close_within_7d') or 0)*100):.0f}%" if life_row else "—")
lc4.metric("% open >30d", f"{(float(life_row.get('pct_open_gt_30d') or 0)*100):.0f}%" if life_row else "—")

st.caption(f"P25/P75 lifespan: {_safe_int(life_row.get('p25_days'), 0)} / {_safe_int(life_row.get('p75_days'), 0)} days" if life_row else "")

bucket_cols = [
    ("0–3d", "age_bucket_0_3"),
    ("4–7d", "age_bucket_4_7"),
    ("8–14d", "age_bucket_8_14"),
    ("15–30d", "age_bucket_15_30"),
    ("30+d", "age_bucket_30_plus"),
]
if life_row:
    bdf = pd.DataFrame([{"bucket": name, "count": _safe_int(life_row.get(col), 0)} for name, col in bucket_cols])
    bchart = alt.Chart(bdf).mark_bar(color="#6366f1").encode(
        x=alt.X("bucket:N", title="Age bucket (open roles)"),
        y=alt.Y("count:Q", title="Count"),
        tooltip=["bucket", "count"],
    ).properties(height=220)
    st.altair_chart(bchart, width="stretch")
else:
    st.caption("No lifecycle history yet (run scraper more days, or run backfill).")

with st.expander("Lifespan by discipline (optional)", expanded=False):
    by_disc = da.get_company_lifespan_by_discipline(selected_slug, as_of_date, window_days=180)
    if by_disc.empty:
        st.caption("Not enough closed-role history to compute discipline lifespans yet.")
    else:
        st.dataframe(by_disc, width="stretch", hide_index=True)

with st.expander("Lifespan by seniority (optional)", expanded=False):
    by_sen = da.get_company_lifespan_by_seniority(selected_slug, as_of_date, window_days=180)
    if by_sen.empty:
        st.caption("Not enough closed-role history to compute seniority lifespans yet.")
    else:
        st.dataframe(by_sen, width="stretch", hide_index=True)

# ------------------------------------------------------------
# Timing + signals
# ------------------------------------------------------------
st.divider()
st.subheader("Timing Intelligence")

t1, t2, t3 = st.columns([2, 2, 3])
t1.metric("Best posting day", _weekday_name(latest_sig.get("best_post_weekday")))
t2.metric("Best removal day", _weekday_name(latest_sig.get("best_remove_weekday")))
hint = (latest_sig.get("timing_hint") or "—").strip()
primary, sep, rest = hint.partition(";")
primary = (primary or hint).strip()
t3.metric("Apply window hint", primary)
if sep and rest.strip():
    t3.caption(rest.strip())

st.caption(latest_sig.get("mover_reason") or "")

st.subheader("Signal Feed")
st.caption("Only signal days (not a raw news list).")

if df_sig.empty:
    st.info("No signals computed yet for this company.")
else:
    feed = df_sig[df_sig["is_mover"] == 1].copy()
    if feed.empty:
        st.caption("No mover-level signals in this window.")
    else:
        for _, r in feed.head(12).iterrows():
            dt = r.get("date")
            hdr = f"{dt}: {r.get('momentum_label')} • {r.get('momentum_state')} (score {float(r.get('momentum_score') or 0):.0f})"
            st.markdown(f"**{hdr}**")
            st.caption(r.get("mover_reason") or "")
            if r.get("headline_title") and r.get("headline_url"):
                st.markdown(f"[{r.get('headline_title')}]({r.get('headline_url')})")
            st.divider()

# ------------------------------------------------------------
# News context (only near spikes/major events)
# ------------------------------------------------------------
st.subheader("News Context (signal-linked)")

if df_news.empty:
    st.caption("No aggregated news found for this window.")
else:
    df_news = df_news.copy()
    df_news["date"] = pd.to_datetime(df_news["date"])
    df_news = df_news.sort_values("date", ascending=False)

    # Keep only major events or days with headlines (limit noise)
    df_news = df_news[(df_news["has_major_event"] == 1) | (df_news["article_count"] > 0)]
    if df_news.empty:
        st.caption("No major/summary headlines found for this window.")
    else:
        for _, r in df_news.head(10).iterrows():
            title = r.get("top_headline_title")
            url = r.get("top_headline_url")
            if not title:
                continue
            dt = str(r.get("date").date())
            prefix = "Major event" if r.get("has_major_event") else "Headline"
            st.markdown(f"**{dt} • {prefix}**")
            st.markdown(f"[{title}]({url})" if url else title)
            st.caption(r.get("major_event_types") or "")
