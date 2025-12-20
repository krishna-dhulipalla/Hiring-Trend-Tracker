import os
import json
import glob
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.news.models import init_db, get_connection
from src.jobs.diff import _parse_discipline, _parse_seniority
from src.analytics.lifespan import compute_company_lifespan_summary
from src.analytics.signal_engine import compute_company_signal


def _iter_snapshot_dirs(base_dir: str) -> List[Tuple[str, str]]:
    """
    Returns list of (company_slug, snapshot_dir) pairs found under data/filtered/**/{slug}.
    """
    pairs: List[Tuple[str, str]] = []
    if not os.path.isdir(base_dir):
        return pairs
    for ats in os.listdir(base_dir):
        ats_dir = os.path.join(base_dir, ats)
        if not os.path.isdir(ats_dir):
            continue
        for slug in os.listdir(ats_dir):
            slug_dir = os.path.join(ats_dir, slug)
            if os.path.isdir(slug_dir):
                pairs.append((slug, slug_dir))
    return pairs


def _job_key(job: Dict[str, Any]) -> Optional[str]:
    return job.get("job_key") or job.get("id") or job.get("url")


def _run_date_from_ts(ts: str) -> str:
    dt = datetime.strptime(ts, "%Y-%m-%dT%H-%M-%SZ")
    return dt.strftime("%Y-%m-%d")


def backfill_from_snapshots(filtered_root: str = "data/filtered") -> None:
    init_db()

    conn = get_connection()
    try:
        cur = conn.cursor()

        pairs = _iter_snapshot_dirs(filtered_root)
        print(f"Found {len(pairs)} company snapshot dirs under {filtered_root}")

        for company_slug, snapshot_dir in sorted(pairs, key=lambda x: x[0]):
            files = sorted(glob.glob(os.path.join(snapshot_dir, "*.json")))
            if not files:
                continue

            prev_keys: set[str] = set()
            latest_ts_by_date: Dict[str, str] = {}
            latest_open_by_date: Dict[str, int] = {}

            print(f"Backfilling {company_slug}: {len(files)} snapshots")

            for path in files:
                ts = os.path.basename(path).replace(".json", "")
                try:
                    date_str = _run_date_from_ts(ts)
                except Exception:
                    continue

                try:
                    with open(path, "r", encoding="utf-8") as f:
                        jobs = json.load(f)
                except Exception:
                    continue

                if not isinstance(jobs, list):
                    continue

                # Open-now per day: keep latest timestamp
                if (date_str not in latest_ts_by_date) or (ts > latest_ts_by_date[date_str]):
                    latest_ts_by_date[date_str] = ts
                    latest_open_by_date[date_str] = len(jobs)

                # Lifecycle updates
                curr_cards = []
                curr_keys: set[str] = set()
                for job in jobs:
                    if not isinstance(job, dict):
                        continue
                    key = _job_key(job)
                    if not key:
                        continue
                    title = job.get("title") or ""
                    url = job.get("url")
                    curr_keys.add(str(key))
                    curr_cards.append((company_slug, str(key), date_str, date_str, title, url, _parse_discipline(title), _parse_seniority(title)))

                # Upsert all present jobs (open)
                cur.executemany(
                    """
                    INSERT INTO job_lifecycle
                        (company_slug, job_key, first_seen_date, last_seen_date, closed_date, title, url, discipline, seniority)
                    VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?)
                    ON CONFLICT(company_slug, job_key) DO UPDATE SET
                        last_seen_date=excluded.last_seen_date,
                        closed_date=NULL,
                        title=excluded.title,
                        url=excluded.url,
                        discipline=excluded.discipline,
                        seniority=excluded.seniority
                    """,
                    curr_cards,
                )

                # Detect closures between prev and current snapshot
                if prev_keys:
                    removed = prev_keys - curr_keys
                    if removed:
                        close_rows = [(company_slug, rk, date_str, date_str) for rk in removed]
                        cur.executemany(
                            """
                            UPDATE job_lifecycle
                            SET last_seen_date=?, closed_date=?
                            WHERE company_slug=? AND job_key=?
                            """,
                            [(date_str, date_str, company_slug, rk) for rk in removed],
                        )

                prev_keys = curr_keys

            # Upsert open-now daily rows for this company
            open_rows = [(company_slug, d, latest_ts_by_date[d], latest_open_by_date[d]) for d in latest_ts_by_date.keys()]
            cur.executemany(
                """
                INSERT OR REPLACE INTO company_open_now_daily (company_slug, date, run_timestamp, open_now_count)
                VALUES (?, ?, ?, ?)
                """,
                open_rows,
            )

        conn.commit()
        print("Backfill complete: open-now + lifecycles")
    finally:
        conn.close()


def compute_latest_summaries(window_days: int = 180, lookback_days: int = 7) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        latest_date_row = cur.execute("SELECT MAX(date) FROM job_diffs_daily").fetchone()
        latest_date = latest_date_row[0] if latest_date_row else None
        if not latest_date:
            print("No job_diffs_daily data found; cannot compute summaries.")
            return

        slugs = [r[0] for r in cur.execute("SELECT DISTINCT company_slug FROM job_diffs_daily").fetchall()]
        print(f"Computing lifespan + signals for {len(slugs)} companies as-of {latest_date}")

        for slug in slugs:
            summary = compute_company_lifespan_summary(slug, latest_date, window_days=window_days)
            cur.execute(
                """
                INSERT OR REPLACE INTO company_lifespan_daily (
                    company_slug, date, window_days, closed_roles_count,
                    median_days, p25_days, p75_days,
                    median_open_age_days,
                    pct_close_within_7d, pct_open_gt_30d, pct_open_gt_60d,
                    age_bucket_0_3, age_bucket_4_7, age_bucket_8_14, age_bucket_15_30, age_bucket_30_plus
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    slug,
                    latest_date,
                    int(window_days),
                    int(summary.closed_roles_count),
                    summary.median_days,
                    summary.p25_days,
                    summary.p75_days,
                    summary.median_open_age_days,
                    summary.pct_close_within_7d,
                    summary.pct_open_gt_30d,
                    summary.pct_open_gt_60d,
                    int(summary.age_bucket_0_3),
                    int(summary.age_bucket_4_7),
                    int(summary.age_bucket_8_14),
                    int(summary.age_bucket_15_30),
                    int(summary.age_bucket_30_plus),
                ),
            )

            sig = compute_company_signal(slug, latest_date, lookback_days=lookback_days)
            cur.execute(
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
                    datetime.utcnow().isoformat(),
                ),
            )

        conn.commit()
        print("Computed lifespan summaries + signals (latest date)")
    finally:
        conn.close()


if __name__ == "__main__":
    # 1) Reconstruct open-now + lifecycles from snapshot history (data/filtered)
    backfill_from_snapshots()

    # 2) Compute latest lifespan + signals (for dashboard usefulness immediately)
    compute_latest_summaries(window_days=180, lookback_days=7)
