import os
import json
import logging
from datetime import datetime
from src.news.models import get_connection


def _run_date(run_timestamp: str) -> str:
    ts_obj = datetime.strptime(run_timestamp, "%Y-%m-%dT%H-%M-%SZ")
    return ts_obj.strftime("%Y-%m-%d")


def sync_job_diff(diff_data, company_slug, run_timestamp):
    """
    Syncs a job diff record into the job_diffs_daily table.
    """
    try:
        # Parse timestamp to date
        date_str = _run_date(run_timestamp)  # UTC date

        added_count = diff_data.get("summary", {}).get("added", 0)
        removed_count = diff_data.get("summary", {}).get("removed", 0)
        changed_count = diff_data.get("summary", {}).get("changed", 0)
        us_added_count = diff_data.get("summary", {}).get("us_added", 0)
        us_remote_added_count = diff_data.get("summary", {}).get("us_remote_added", 0)
        
        # Calculate senior+ added
        # Support both structures: top-level (diff.py) and nested "details" (dashboard assumption)
        added_jobs = diff_data.get("added", [])
        if not added_jobs:
            added_jobs = diff_data.get("details", {}).get("added", [])

        removed_jobs = diff_data.get("removed", [])
        if not removed_jobs:
            removed_jobs = diff_data.get("details", {}).get("removed", [])
            
        keywords = ["senior", "staff", "principal", "lead", "director", "head", "vp", "architect"]
        senior_plus_added_count = 0
        for job in added_jobs:
            title = job.get("title", "").lower()
            if any(k in title for k in keywords):
                senior_plus_added_count += 1

        conn = get_connection()
        c = conn.cursor()
        
        c.execute("""
            INSERT OR REPLACE INTO job_diffs_daily 
            (company_slug, date, run_timestamp, added_count, removed_count, changed_count, us_added_count, us_remote_added_count, senior_plus_added_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (company_slug, date_str, run_timestamp, added_count, removed_count, changed_count, us_added_count, us_remote_added_count, senior_plus_added_count))

        # Discipline breakdown for mix-shift + domain pulse
        disc_added = {}
        disc_removed = {}
        for job in added_jobs:
            disc = job.get("discipline") or "Other"
            disc_added[disc] = disc_added.get(disc, 0) + 1
        for job in removed_jobs:
            disc = job.get("discipline") or "Other"
            disc_removed[disc] = disc_removed.get(disc, 0) + 1

        disciplines = set(disc_added.keys()) | set(disc_removed.keys())
        for disc in disciplines:
            c.execute(
                """
                INSERT OR REPLACE INTO job_diffs_discipline_daily
                    (company_slug, date, discipline, added_count, removed_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (company_slug, date_str, disc, int(disc_added.get(disc, 0)), int(disc_removed.get(disc, 0))),
            )
        
        conn.commit()
        conn.close()
        logging.info(f"Synced job stats for {company_slug} on {date_str}")
        
    except Exception as e:
        logging.error(f"Failed to sync job diff for {company_slug}: {e}")


def agg_daily_news(days_back=30):
    """
    Aggregates news into company_news_daily for the last N days.
    """
    conn = get_connection()
    c = conn.cursor()
    
    # Simple strategy: clear recent days and re-aggregate to avoid complex updates
    # Actually, REPLACE works fine if we compute everything.
    
    # Get range
    # In SQLite, we can use date() on the ISO string
    
    # Fix: Don't use alias in WHERE clause
    query = """
    SELECT 
        company_slug, 
        date(published_at) as day_date,
        COUNT(*) as total,
        SUM(CASE WHEN news_category='funding' THEN 1 ELSE 0 END) as funding,
        SUM(CASE WHEN news_category='earnings' THEN 1 ELSE 0 END) as earnings,
        SUM(CASE WHEN news_category='product' THEN 1 ELSE 0 END) as product,
        SUM(CASE WHEN news_category='ai_announcement' THEN 1 ELSE 0 END) as ai,
        SUM(CASE WHEN news_category='layoff' THEN 1 ELSE 0 END) as layoff,
        SUM(CASE WHEN news_category='hiring' THEN 1 ELSE 0 END) as hiring,
        SUM(CASE WHEN news_category='regulatory' THEN 1 ELSE 0 END) as regulatory
    FROM normalized_news
    WHERE date(published_at) >= date('now', ?)
    GROUP BY company_slug, day_date
    """
    
    days_arg = f"-{days_back} days"
    rows = c.execute(query, (days_arg,)).fetchall()
    
    for r in rows:
        slug, day_date, total, fund, earn, prod, ai, lay, hire, reg = r
        
        # Major event logic
        has_major = (fund + lay + earn) > 0
        major_types = []
        if fund > 0: major_types.append("funding")
        if lay > 0: major_types.append("layoff")
        if earn > 0: major_types.append("earnings")
        major_types_str = ",".join(major_types)
        
        # Top headline (simplistic: get max title)
        # Ideally, we'd get the one with highest "importance" or just most recent
        top_art = c.execute("SELECT title, source_url FROM normalized_news WHERE company_slug=? AND date(published_at)=? ORDER BY published_at DESC LIMIT 1", (slug, day_date)).fetchone()
        top_title = top_art[0] if top_art else None
        top_url = top_art[1] if top_art else None

        c.execute("""
            INSERT OR REPLACE INTO company_news_daily
            (company_slug, date, article_count, funding_count, earnings_count, product_count, ai_announcement_count, layoff_count, hiring_count, regulatory_count, has_major_event, major_event_types, top_headline_title, top_headline_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (slug, day_date, total, fund, earn, prod, ai, lay, hire, reg, has_major, major_types_str, top_title, top_url))
        
    conn.commit()
    conn.close()
    logging.info(f"Aggregated news for last {days_back} days.")
