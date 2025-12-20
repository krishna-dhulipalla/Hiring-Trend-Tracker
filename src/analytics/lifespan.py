from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import Any, Dict, Iterable, List, Optional, Tuple
import logging

from src.news.models import get_connection
from src.jobs.diff import _parse_discipline, _parse_seniority


def _run_date(run_timestamp: str) -> str:
    ts_obj = datetime.strptime(run_timestamp, "%Y-%m-%dT%H-%M-%SZ")
    return ts_obj.strftime("%Y-%m-%d")


def _job_key(job: Dict[str, Any]) -> Optional[str]:
    return job.get("job_key") or job.get("id") or job.get("url")


def _percentile(sorted_vals: List[float], p: float) -> Optional[float]:
    if not sorted_vals:
        return None
    if p <= 0:
        return float(sorted_vals[0])
    if p >= 100:
        return float(sorted_vals[-1])
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return float(sorted_vals[f])
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return float(d0 + d1)


@dataclass(frozen=True)
class LifespanSummary:
    closed_roles_count: int
    median_days: Optional[float]
    p25_days: Optional[float]
    p75_days: Optional[float]
    median_open_age_days: Optional[float]
    pct_close_within_7d: Optional[float]
    pct_open_gt_30d: Optional[float]
    pct_open_gt_60d: Optional[float]
    age_bucket_0_3: int
    age_bucket_4_7: int
    age_bucket_8_14: int
    age_bucket_15_30: int
    age_bucket_30_plus: int


def sync_open_now(company_slug: str, run_timestamp: str, open_now_count: int) -> None:
    date_str = _run_date(run_timestamp)
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute(
            """
            INSERT OR REPLACE INTO company_open_now_daily (company_slug, date, run_timestamp, open_now_count)
            VALUES (?, ?, ?, ?)
            """,
            (company_slug, date_str, run_timestamp, int(open_now_count)),
        )
        conn.commit()
    finally:
        conn.close()


def sync_job_lifecycle(
    company_slug: str,
    run_timestamp: str,
    current_snapshot_jobs: List[Dict[str, Any]],
    diff_data: Optional[Dict[str, Any]],
    *,
    window_days: int = 180,
) -> None:
    date_str = _run_date(run_timestamp)

    conn = get_connection()
    try:
        c = conn.cursor()

        # 1) Upsert current open roles (present in snapshot)
        for job in current_snapshot_jobs:
            key = _job_key(job)
            if not key:
                continue
            title = job.get("title") or ""
            url = job.get("url")
            discipline = _parse_discipline(title)
            seniority = _parse_seniority(title)

            c.execute(
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
                (company_slug, str(key), date_str, date_str, title, url, discipline, seniority),
            )

        # 2) Mark removals as closed on this date
        if diff_data:
            removed = diff_data.get("removed", []) or diff_data.get("details", {}).get("removed", [])
            for card in removed:
                key = card.get("job_key") or card.get("id") or card.get("url")
                if not key:
                    continue
                title = card.get("title") or ""
                url = card.get("url")
                discipline = card.get("discipline") or _parse_discipline(title)
                seniority = card.get("seniority") or _parse_seniority(title)

                # Ensure record exists, then close it
                c.execute(
                    """
                    INSERT INTO job_lifecycle
                        (company_slug, job_key, first_seen_date, last_seen_date, closed_date, title, url, discipline, seniority)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(company_slug, job_key) DO UPDATE SET
                        last_seen_date=excluded.last_seen_date,
                        closed_date=excluded.closed_date,
                        title=excluded.title,
                        url=excluded.url,
                        discipline=excluded.discipline,
                        seniority=excluded.seniority
                    """,
                    (company_slug, str(key), date_str, date_str, date_str, title, url, discipline, seniority),
                )

        # 3) Precompute lifespan summary for dashboard speed
        summary = compute_company_lifespan_summary(company_slug, date_str, window_days=window_days, conn=conn)
        c.execute(
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
                company_slug,
                date_str,
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

        conn.commit()
    except Exception as e:
        logging.error(f"Lifespan sync failed for {company_slug}: {e}")
        conn.rollback()
    finally:
        conn.close()


def compute_company_lifespan_summary(
    company_slug: str,
    as_of_date: str,
    *,
    window_days: int = 180,
    conn=None,
) -> LifespanSummary:
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        c = conn.cursor()
        as_of = datetime.strptime(as_of_date, "%Y-%m-%d").date()
        start = (as_of - timedelta(days=window_days - 1)).strftime("%Y-%m-%d")

        rows = c.execute(
            """
            SELECT first_seen_date, closed_date
            FROM job_lifecycle
            WHERE company_slug=?
              AND closed_date IS NOT NULL
              AND closed_date >= ?
              AND closed_date <= ?
            """,
            (company_slug, start, as_of_date),
        ).fetchall()

        durations: List[float] = []
        close_within_7 = 0
        for first_seen, closed_date in rows:
            try:
                fs = datetime.strptime(first_seen, "%Y-%m-%d").date()
                cd = datetime.strptime(closed_date, "%Y-%m-%d").date()
            except Exception:
                continue
            days_open = float((cd - fs).days + 1)
            if days_open <= 0:
                continue
            durations.append(days_open)
            if days_open <= 7:
                close_within_7 += 1

        durations.sort()
        closed_roles_count = len(durations)
        median_days = _percentile(durations, 50) if durations else None
        p25_days = _percentile(durations, 25) if durations else None
        p75_days = _percentile(durations, 75) if durations else None
        pct_close_within_7d = (close_within_7 / closed_roles_count) if closed_roles_count > 0 else None

        # Open-role age buckets as-of date
        open_rows = c.execute(
            """
            SELECT first_seen_date
            FROM job_lifecycle
            WHERE company_slug=?
              AND (closed_date IS NULL OR closed_date > ?)
            """,
            (company_slug, as_of_date),
        ).fetchall()

        age_bucket_0_3 = age_bucket_4_7 = age_bucket_8_14 = age_bucket_15_30 = age_bucket_30_plus = 0
        open_gt_30 = 0
        open_gt_60 = 0
        open_count = 0
        open_ages: List[float] = []
        for (first_seen,) in open_rows:
            try:
                fs = datetime.strptime(first_seen, "%Y-%m-%d").date()
            except Exception:
                continue
            age = (as_of - fs).days + 1
            if age <= 0:
                continue
            open_count += 1
            open_ages.append(float(age))
            if age <= 3:
                age_bucket_0_3 += 1
            elif age <= 7:
                age_bucket_4_7 += 1
            elif age <= 14:
                age_bucket_8_14 += 1
            elif age <= 30:
                age_bucket_15_30 += 1
            else:
                age_bucket_30_plus += 1

            if age > 30:
                open_gt_30 += 1
            if age > 60:
                open_gt_60 += 1

        pct_open_gt_30d = (open_gt_30 / open_count) if open_count > 0 else None
        pct_open_gt_60d = (open_gt_60 / open_count) if open_count > 0 else None
        open_ages.sort()
        median_open_age_days = _percentile(open_ages, 50) if open_ages else None

        return LifespanSummary(
            closed_roles_count=closed_roles_count,
            median_days=median_days,
            p25_days=p25_days,
            p75_days=p75_days,
            median_open_age_days=median_open_age_days,
            pct_close_within_7d=pct_close_within_7d,
            pct_open_gt_30d=pct_open_gt_30d,
            pct_open_gt_60d=pct_open_gt_60d,
            age_bucket_0_3=age_bucket_0_3,
            age_bucket_4_7=age_bucket_4_7,
            age_bucket_8_14=age_bucket_8_14,
            age_bucket_15_30=age_bucket_15_30,
            age_bucket_30_plus=age_bucket_30_plus,
        )
    finally:
        if close_conn:
            conn.close()
