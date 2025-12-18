from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import math
import statistics

from src.news.models import get_connection


WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _date_from_run_timestamp(run_timestamp: str) -> str:
    ts_obj = datetime.strptime(run_timestamp, "%Y-%m-%dT%H-%M-%SZ")
    return ts_obj.strftime("%Y-%m-%d")


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


@dataclass(frozen=True)
class CompanySignal:
    company_slug: str
    date: str
    lookback_days: int
    momentum_state: str
    momentum_label: str
    momentum_score: float
    is_mover: bool
    mover_reason: str
    timing_hint: str
    timing_confidence: str
    best_post_weekday: Optional[int]
    best_remove_weekday: Optional[int]
    headline_title: Optional[str]
    headline_url: Optional[str]


def _weekday_int_from_sqlite_w(sqlite_w: str) -> int:
    # SQLite: 0=Sunday..6=Saturday. Convert to 0=Mon..6=Sun.
    w = int(sqlite_w)
    if w == 0:
        return 6
    return w - 1


def _best_weekday(mean_by_weekday: Dict[int, float]) -> Optional[int]:
    if not mean_by_weekday:
        return None
    return max(mean_by_weekday.items(), key=lambda x: x[1])[0]


def _timing_hint(median_days: Optional[float], pct_close_7d: Optional[float], pct_open_gt_30d: Optional[float]) -> Tuple[str, str]:
    if median_days is None and pct_close_7d is None:
        return ("Unknown; gather more history", "low")

    fast = False
    if median_days is not None and median_days <= 7:
        fast = True
    if pct_close_7d is not None and pct_close_7d >= 0.5:
        fast = True

    if fast:
        return ("Apply within 48h", "high" if (median_days is not None and median_days <= 5) else "med")

    if median_days is not None and median_days <= 14:
        return ("Apply within 3–5 days", "med")

    if pct_open_gt_30d is not None and pct_open_gt_30d >= 0.4:
        return ("Networking-first; timing less critical", "med")

    return ("Apply within 7 days", "low")


def compute_company_signal(company_slug: str, run_date: str, *, lookback_days: int = 7) -> CompanySignal:
    conn = get_connection()
    try:
        c = conn.cursor()

        # Open-now: latest value on/before run_date
        row = c.execute(
            """
            SELECT open_now_count
            FROM company_open_now_daily
            WHERE company_slug=? AND date <= ?
            ORDER BY date DESC
            LIMIT 1
            """,
            (company_slug, run_date),
        ).fetchone()
        open_now = int(row[0]) if row else 0

        end = datetime.strptime(run_date, "%Y-%m-%d").date()
        start = (end - timedelta(days=lookback_days - 1)).strftime("%Y-%m-%d")
        prev_start = (end - timedelta(days=2 * lookback_days - 1)).strftime("%Y-%m-%d")
        prev_end = (end - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

        sums = c.execute(
            """
            SELECT
                COALESCE(SUM(added_count), 0),
                COALESCE(SUM(removed_count), 0)
            FROM job_diffs_daily
            WHERE company_slug=? AND date >= ? AND date <= ?
            """,
            (company_slug, start, run_date),
        ).fetchone()
        added_7d = int(sums[0] or 0)
        removed_7d = int(sums[1] or 0)
        net_7d = added_7d - removed_7d

        prev = c.execute(
            """
            SELECT
                COALESCE(SUM(added_count), 0),
                COALESCE(SUM(removed_count), 0)
            FROM job_diffs_daily
            WHERE company_slug=? AND date >= ? AND date <= ?
            """,
            (company_slug, prev_start, prev_end),
        ).fetchone()
        prev_added = int(prev[0] or 0)
        prev_removed = int(prev[1] or 0)
        prev_net = prev_added - prev_removed

        # Volatility: std dev of daily net over lookback window
        daily = c.execute(
            """
            SELECT date, added_count, removed_count
            FROM job_diffs_daily
            WHERE company_slug=? AND date >= ? AND date <= ?
            ORDER BY date ASC
            """,
            (company_slug, start, run_date),
        ).fetchall()
        daily_net = [(int(a) - int(r)) for _, a, r in daily]
        volatility = statistics.pstdev(daily_net) if len(daily_net) >= 2 else 0.0

        # Open-now direction (lookback vs previous window)
        open_rows = c.execute(
            """
            SELECT date, open_now_count
            FROM company_open_now_daily
            WHERE company_slug=? AND date >= ? AND date <= ?
            ORDER BY date ASC
            """,
            (company_slug, prev_start, run_date),
        ).fetchall()
        open_by_date = {d: int(v) for d, v in open_rows}
        open_start = open_by_date.get(start)
        open_end = open_by_date.get(run_date)
        open_delta = (open_end - open_start) if (open_start is not None and open_end is not None) else None

        # Discipline mix shift (simple): last window vs prev window
        disc_rows = c.execute(
            """
            SELECT date, discipline, added_count
            FROM job_diffs_discipline_daily
            WHERE company_slug=? AND date >= ? AND date <= ?
            """,
            (company_slug, prev_start, run_date),
        ).fetchall()
        disc_last: Dict[str, int] = {}
        disc_prev: Dict[str, int] = {}
        for d, disc, cnt in disc_rows:
            disc = disc or "Other"
            if start <= d <= run_date:
                disc_last[disc] = disc_last.get(disc, 0) + int(cnt or 0)
            elif prev_start <= d <= prev_end:
                disc_prev[disc] = disc_prev.get(disc, 0) + int(cnt or 0)

        def _top_share(dmap: Dict[str, int]) -> Tuple[Optional[str], float, int]:
            total = sum(dmap.values())
            if total <= 0:
                return (None, 0.0, 0)
            top_disc, top_cnt = max(dmap.items(), key=lambda x: x[1])
            return (top_disc, top_cnt / total, total)

        top_last, share_last, tot_last = _top_share(disc_last)
        top_prev, share_prev, tot_prev = _top_share(disc_prev)
        mix_shift = False
        mix_shift_reason = None
        if top_last and tot_last >= 6 and tot_prev >= 6:
            if (top_last != top_prev) or (share_last - share_prev >= 0.25):
                mix_shift = True
                mix_shift_reason = f"New mix focus: {top_last} ({share_last:.0%} of adds)"

        # Baseline add/remove rate over last 28d
        baseline_start = (end - timedelta(days=27)).strftime("%Y-%m-%d")
        baseline = c.execute(
            """
            SELECT
                AVG(added_count),
                AVG(removed_count)
            FROM job_diffs_daily
            WHERE company_slug=? AND date >= ? AND date <= ?
            """,
            (company_slug, baseline_start, run_date),
        ).fetchone()
        base_add = float(baseline[0] or 0.0)
        base_rem = float(baseline[1] or 0.0)

        # Lifespan stats (precomputed)
        life = c.execute(
            """
            SELECT median_days, pct_close_within_7d, pct_open_gt_30d
            FROM company_lifespan_daily
            WHERE company_slug=? AND date=? AND window_days=180
            """,
            (company_slug, run_date),
        ).fetchone()
        median_days = float(life[0]) if life and life[0] is not None else None
        pct_close_7d = float(life[1]) if life and life[1] is not None else None
        pct_open_gt_30d = float(life[2]) if life and life[2] is not None else None

        timing_hint, timing_conf = _timing_hint(median_days, pct_close_7d, pct_open_gt_30d)

        # Best weekdays from last 12 weeks
        weekday_start = (end - timedelta(days=83)).strftime("%Y-%m-%d")
        wk_rows = c.execute(
            """
            SELECT strftime('%w', date) as wd, AVG(added_count) as a_mean, AVG(removed_count) as r_mean
            FROM job_diffs_daily
            WHERE company_slug=? AND date >= ? AND date <= ?
            GROUP BY wd
            """,
            (company_slug, weekday_start, run_date),
        ).fetchall()
        add_mean = {_weekday_int_from_sqlite_w(wd): float(a or 0.0) for wd, a, _ in wk_rows}
        rem_mean = {_weekday_int_from_sqlite_w(wd): float(r or 0.0) for wd, _, r in wk_rows}
        best_post = _best_weekday(add_mean)
        best_remove = _best_weekday(rem_mean)

        # Headline: latest major news within lookback window, else latest headline
        news = c.execute(
            """
            SELECT top_headline_title, top_headline_url
            FROM company_news_daily
            WHERE company_slug=?
              AND date >= ? AND date <= ?
              AND (has_major_event=1 OR article_count > 0)
            ORDER BY (has_major_event=1) DESC, date DESC
            LIMIT 1
            """,
            (company_slug, start, run_date),
        ).fetchone()
        headline_title = news[0] if news else None
        headline_url = news[1] if news else None

        # State + label
        slope = net_7d - prev_net
        churn = added_7d + removed_7d
        open_norm = max(open_now, 1)
        net_ratio = net_7d / open_norm

        state = "Stable"
        if net_7d <= -max(5, int(0.15 * open_norm)) or (removed_7d >= added_7d + 10 and net_7d < 0):
            state = "Freezing"
        elif volatility >= max(5.0, 0.25 * abs(net_7d) + 3.0) or churn >= max(15, int(0.6 * open_norm)):
            state = "Volatile"
        elif net_7d >= max(5, int(0.15 * open_norm)) and slope >= max(3, int(0.05 * open_norm)):
            state = "Accelerating"
        elif net_7d > 0 and slope <= -max(3, int(0.05 * open_norm)):
            state = "Slowing"
        elif abs(net_7d) <= 2 and churn <= max(5, int(0.2 * open_norm)):
            state = "Stable"
        else:
            state = "Steady"

        label = "Quiet"
        if state == "Accelerating":
            label = "Booming"
        elif state == "Freezing":
            label = "Freezing"
        elif state == "Volatile":
            label = "Volatile"
        elif state in ("Steady", "Stable"):
            label = "Stable"
        else:
            label = "Stable"

        # "Mover" gating
        triggers: List[str] = []
        abs_net_trigger = abs(net_7d) >= max(10, int(0.2 * open_norm))
        if abs_net_trigger:
            triggers.append(f"Net {lookback_days}d = {net_7d:+d}")
        if added_7d >= int(max(10.0, base_add * lookback_days * 1.8)):
            triggers.append(f"Adds spike ({added_7d} vs baseline ~{base_add:.1f}/day)")
        if removed_7d >= int(max(10.0, base_rem * lookback_days * 1.8)):
            triggers.append(f"Removals spike ({removed_7d} vs baseline ~{base_rem:.1f}/day)")
        if state == "Volatile":
            triggers.append(f"High churn ({churn} changes)")
        if open_delta is not None and abs(open_delta) >= max(5, int(0.15 * open_norm)):
            triggers.append(f"Open roles shift ({open_delta:+d} in {lookback_days}d)")
        if mix_shift and mix_shift_reason:
            triggers.append(mix_shift_reason)

        is_mover = len(triggers) > 0
        mover_reason = "; ".join(triggers) if triggers else "Low signal this week"

        # Add networking context to the timing hint (keeps UX compact)
        if mix_shift:
            timing_hint = f"Network now (new focus); {timing_hint}"
            timing_conf = "med" if timing_conf == "low" else timing_conf
        if state in ("Accelerating", "Volatile") and "Apply" in timing_hint:
            timing_hint = f"{timing_hint}; network now"
        if state == "Freezing":
            timing_hint = "Network now; apply strategically (freeze risk)"
            timing_conf = "med"

        # Momentum score (0-100, simple + explainable)
        score = 50.0
        score += 60.0 * math.tanh(net_ratio * 3.0)  # net vs open_now
        score += 10.0 * math.tanh((added_7d / max(lookback_days, 1)) / 10.0)
        score -= 10.0 * math.tanh((removed_7d / max(lookback_days, 1)) / 10.0)
        score -= 10.0 * math.tanh(volatility / 10.0)
        score = _clamp(score, 0.0, 100.0)

        return CompanySignal(
            company_slug=company_slug,
            date=run_date,
            lookback_days=lookback_days,
            momentum_state=state,
            momentum_label=label,
            momentum_score=score,
            is_mover=is_mover,
            mover_reason=mover_reason,
            timing_hint=timing_hint,
            timing_confidence=timing_conf,
            best_post_weekday=best_post,
            best_remove_weekday=best_remove,
            headline_title=headline_title,
            headline_url=headline_url,
        )
    finally:
        conn.close()


def compute_and_store_signals(run_timestamp: str, *, lookback_days: int = 7) -> None:
    run_date = _date_from_run_timestamp(run_timestamp)
    conn = get_connection()
    try:
        c = conn.cursor()
        # Use config-backed universe when available; fall back to DB.
        companies = c.execute("SELECT DISTINCT company_slug FROM job_diffs_daily").fetchall()
        slugs = [r[0] for r in companies] if companies else []

        now_iso = datetime.utcnow().isoformat()
        for slug in slugs:
            sig = compute_company_signal(slug, run_date, lookback_days=lookback_days)
            c.execute(
                """
                INSERT OR REPLACE INTO company_signals_daily (
                    company_slug, date, lookback_days,
                    momentum_state, momentum_label, momentum_score,
                    is_mover, mover_reason,
                    timing_hint, timing_confidence,
                    best_post_weekday, best_remove_weekday,
                    headline_title, headline_url,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sig.company_slug,
                    sig.date,
                    int(sig.lookback_days),
                    sig.momentum_state,
                    sig.momentum_label,
                    float(sig.momentum_score),
                    1 if sig.is_mover else 0,
                    sig.mover_reason,
                    sig.timing_hint,
                    sig.timing_confidence,
                    sig.best_post_weekday,
                    sig.best_remove_weekday,
                    sig.headline_title,
                    sig.headline_url,
                    now_iso,
                ),
            )

        conn.commit()
        logging.info(f"Computed signals for {len(slugs)} companies on {run_date}")
    except Exception as e:
        logging.error(f"Signal engine failed: {e}")
        conn.rollback()
    finally:
        conn.close()
