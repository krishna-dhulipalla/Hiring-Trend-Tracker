import streamlit as st
import altair as alt
import pandas as pd
from datetime import datetime, timedelta

import data_access as da
import components as ui

st.set_page_config(page_title="Global Pulse", page_icon="🌐", layout="wide")
ui.apply_custom_css()

st.title("Global Pulse")
st.caption("Actionable market + domain signals (no chart clutter).")

with st.sidebar:
    st.header("Scope")
    days_back = st.slider("Lookback window (days)", 14, 120, 45)
    signal_lookback = st.selectbox("Signal lookback (days)", [7, 14], index=0)

end_date = datetime.now().date()
start_date = (end_date - timedelta(days=int(days_back) - 1)).strftime("%Y-%m-%d")
end_date_str = end_date.strftime("%Y-%m-%d")

# ------------------------------------------------------------
# Panel 1: Open roles + net change trend
# ------------------------------------------------------------
st.subheader("1) Market pulse: Open roles + net change")

df_open = da.get_open_now_daily(start_date=start_date, end_date=end_date_str)
df_diffs = da.get_job_diffs_daily(start_date=start_date, end_date=end_date_str)

open_trend = pd.DataFrame()
if not df_open.empty:
    df_open = df_open.copy()
    df_open["date"] = pd.to_datetime(df_open["date"])
    open_trend = df_open.groupby("date")["open_now_count"].sum().reset_index().sort_values("date")

net_trend = pd.DataFrame()
if not df_diffs.empty:
    df_diffs = df_diffs.copy()
    df_diffs["date"] = pd.to_datetime(df_diffs["date"])
    df_diffs["net"] = df_diffs["added_count"] - df_diffs["removed_count"]
    net_trend = df_diffs.groupby("date")[["added_count", "removed_count", "net"]].sum().reset_index().sort_values("date")

if open_trend.empty and net_trend.empty:
    st.info("Not enough data yet. Run the scraper for a few days (or backfill).")
else:
    layers = []
    if not open_trend.empty:
        layers.append(
            alt.Chart(open_trend).mark_line(color="#94a3b8", strokeWidth=2).encode(
                x=alt.X("date:T", axis=alt.Axis(title=None, format="%b %d")),
                y=alt.Y("open_now_count:Q", title="Total open roles"),
                tooltip=[alt.Tooltip("date:T", title="Date"), alt.Tooltip("open_now_count:Q", title="Open roles")],
            )
        )
    if not net_trend.empty:
        layers.append(
            alt.Chart(net_trend).mark_bar(color="#10b981", opacity=0.35).encode(
                x="date:T",
                y=alt.Y("net:Q", title="Net change (daily)"),
                tooltip=[alt.Tooltip("date:T", title="Date"), alt.Tooltip("net:Q", title="Net")],
            )
        )
    st.altair_chart(alt.layer(*layers).resolve_scale(y="independent").properties(height=320).interactive(), width="stretch")

# Summary metrics (as-of latest available)
col1, col2, col3 = st.columns(3)
col1.metric("Open roles now", int(open_trend["open_now_count"].iloc[-1]) if not open_trend.empty else 0)
col2.metric("Net (today)", int(net_trend["net"].iloc[-1]) if not net_trend.empty else 0)
col3.metric("Total added (window)", int(net_trend["added_count"].sum()) if not net_trend.empty else 0)

# ------------------------------------------------------------
# Panel 2: Movers distribution trend
# ------------------------------------------------------------
st.divider()
st.subheader("2) Booming vs freezing companies")

df_sig = da.get_company_signals(start_date=start_date, end_date=end_date_str, lookback_days=int(signal_lookback))
if df_sig.empty:
    st.caption("No signals computed yet (run scraper; signals are computed after a run).")
else:
    df_sig = df_sig.copy()
    df_sig["date"] = pd.to_datetime(df_sig["date"])
    movers_only = df_sig[df_sig["is_mover"] == 1]
    dist = movers_only.groupby(["date", "momentum_label"]).size().reset_index(name="count")
    chart = alt.Chart(dist).mark_line(point=True).encode(
        x=alt.X("date:T", axis=alt.Axis(title=None, format="%b %d")),
        y=alt.Y("count:Q", title="Mover count"),
        color=alt.Color("momentum_label:N", title="Label"),
        tooltip=["date:T", "momentum_label:N", "count:Q"],
    ).properties(height=260)
    st.altair_chart(chart.interactive(), width="stretch")

# ------------------------------------------------------------
# Panel 3: Weekday effect heatmap
# ------------------------------------------------------------
st.divider()
st.subheader("3) Weekday effect (adds / removes / net)")

if df_diffs.empty:
    st.caption("No job diffs found for this window.")
else:
    w = df_diffs.copy()
    w["date"] = pd.to_datetime(w["date"])
    w["weekday"] = w["date"].dt.day_name().str[:3]
    w["net"] = w["added_count"] - w["removed_count"]
    wk = w.groupby("weekday")[["added_count", "removed_count", "net"]].sum().reset_index()
    order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    wk["weekday"] = pd.Categorical(wk["weekday"], categories=order, ordered=True)
    wk = wk.sort_values("weekday")

    melt = wk.melt(id_vars=["weekday"], value_vars=["added_count", "removed_count", "net"], var_name="metric", value_name="value")
    heat = alt.Chart(melt).mark_rect().encode(
        x=alt.X("weekday:N", title=None),
        y=alt.Y("metric:N", title=None),
        color=alt.Color("value:Q", scale=alt.Scale(scheme="redyellowgreen"), title="Sum"),
        tooltip=["weekday:N", "metric:N", "value:Q"],
    ).properties(height=160)
    st.altair_chart(heat, width="stretch")

# ------------------------------------------------------------
# Panel 4: Domain mix shift (discipline)
# ------------------------------------------------------------
st.divider()
st.subheader("4) Domain mix shift (discipline)")

disc = da.get_discipline_diffs_daily(start_date=start_date, end_date=end_date_str)
if disc.empty:
    st.caption("No discipline breakdown found yet (will populate on new runs, or via backfill).")
else:
    disc = disc.copy()
    disc["date"] = pd.to_datetime(disc["date"])
    latest = disc["date"].max().date()
    last7_start = latest - timedelta(days=6)
    prev7_start = latest - timedelta(days=13)
    prev7_end = latest - timedelta(days=7)

    last7 = disc[(disc["date"].dt.date >= last7_start) & (disc["date"].dt.date <= latest)].groupby("discipline")["added_count"].sum()
    prev7 = disc[(disc["date"].dt.date >= prev7_start) & (disc["date"].dt.date <= prev7_end)].groupby("discipline")["added_count"].sum()

    df_mix = pd.DataFrame({"last7_added": last7, "prev7_added": prev7}).fillna(0).reset_index()
    tot_last = df_mix["last7_added"].sum()
    tot_prev = df_mix["prev7_added"].sum()
    if tot_last == 0 or tot_prev == 0:
        st.caption("Not enough recent additions to compute mix shift.")
    else:
        df_mix["last7_share"] = df_mix["last7_added"] / tot_last
        df_mix["prev7_share"] = df_mix["prev7_added"] / tot_prev
        df_mix["delta_share"] = df_mix["last7_share"] - df_mix["prev7_share"]
        df_mix = df_mix.sort_values("delta_share", ascending=False)

        bar = alt.Chart(df_mix).mark_bar().encode(
            x=alt.X("delta_share:Q", title="Share change (last 7d vs prior 7d)", axis=alt.Axis(format="%")),
            y=alt.Y("discipline:N", title=None, sort="-x"),
            color=alt.Color("delta_share:Q", scale=alt.Scale(scheme="redyellowgreen")),
            tooltip=["discipline:N", alt.Tooltip("last7_added:Q", title="Last7 added"), alt.Tooltip("prev7_added:Q", title="Prev7 added"), alt.Tooltip("delta_share:Q", title="Δ share", format=".1%")],
        ).properties(height=220)
        st.altair_chart(bar, width="stretch")

# ------------------------------------------------------------
# Panel 5: Concentration (avoid false optimism)
# ------------------------------------------------------------
st.divider()
st.subheader("5) Concentration: top companies drive the adds")

if df_diffs.empty:
    st.caption("No diffs for this window.")
else:
    latest_date = df_diffs["date"].max()
    if isinstance(latest_date, pd.Timestamp):
        latest_dt = latest_date.date()
    else:
        latest_dt = datetime.strptime(str(latest_date), "%Y-%m-%d").date()
    lb_start = latest_dt - timedelta(days=int(signal_lookback) - 1)

    recent = df_diffs.copy()
    recent["date"] = pd.to_datetime(recent["date"])
    recent = recent[(recent["date"].dt.date >= lb_start) & (recent["date"].dt.date <= latest_dt)]
    adds = recent.groupby("company_slug")["added_count"].sum().sort_values(ascending=False)
    total_adds = float(adds.sum())
    if total_adds <= 0:
        st.caption("No additions in this window.")
    else:
        top5 = adds.head(5)
        share = float(top5.sum()) / total_adds
        st.metric("Top 5 share of new roles", f"{share*100:.0f}%")
        st.dataframe(top5.reset_index().rename(columns={"company_slug": "Company", "added_count": "Added"}), width="stretch", hide_index=True)
