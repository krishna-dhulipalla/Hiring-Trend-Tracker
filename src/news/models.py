import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "news.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Raw News Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS raw_news (
            id TEXT PRIMARY KEY,
            source_id TEXT,
            source_article_id TEXT,
            article_url TEXT,
            title TEXT,
            description TEXT,
            published_at TEXT,
            ingested_at TEXT,
            source_domain TEXT,
            author TEXT,
            image_url TEXT,
            raw_json TEXT,  -- JSON string
            UNIQUE(source_id, source_article_id)
        )
    ''')

    # Normalized News Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS normalized_news (
            id TEXT PRIMARY KEY,
            raw_news_id TEXT,
            company_slug TEXT,
            company_name TEXT,
            news_category TEXT,
            published_at TEXT,
            title TEXT,
            summary TEXT,
            source_url TEXT,
            processed_at TEXT,
            FOREIGN KEY(raw_news_id) REFERENCES raw_news(id),
            UNIQUE(raw_news_id)
        )
    ''')

    # Analytics: Job Diffs Daily
    c.execute('''
        CREATE TABLE IF NOT EXISTS job_diffs_daily (
            company_slug TEXT,
            date TEXT, -- YYYY-MM-DD
            run_timestamp TEXT,
            added_count INTEGER,
            removed_count INTEGER,
            changed_count INTEGER,
            us_added_count INTEGER,
            us_remote_added_count INTEGER,
            senior_plus_added_count INTEGER,
            PRIMARY KEY (company_slug, date)
        )
    ''')
    
    # Analytics: Company News Daily
    c.execute('''
        CREATE TABLE IF NOT EXISTS company_news_daily (
            company_slug TEXT,
            date TEXT, -- YYYY-MM-DD
            article_count INTEGER,
            funding_count INTEGER,
            earnings_count INTEGER,
            product_count INTEGER,
            ai_announcement_count INTEGER,
            layoff_count INTEGER,
            hiring_count INTEGER,
            regulatory_count INTEGER,
            has_major_event BOOLEAN,
            major_event_types TEXT,
            top_headline_title TEXT,
            top_headline_url TEXT,
            PRIMARY KEY (company_slug, date)
        )
    ''')

    # Analytics: Open Roles Daily (from filtered snapshots)
    c.execute('''
        CREATE TABLE IF NOT EXISTS company_open_now_daily (
            company_slug TEXT,
            date TEXT, -- YYYY-MM-DD
            run_timestamp TEXT,
            open_now_count INTEGER,
            PRIMARY KEY (company_slug, date)
        )
    ''')

    # Analytics: Diff Breakdown by Discipline (adds/removes)
    c.execute('''
        CREATE TABLE IF NOT EXISTS job_diffs_discipline_daily (
            company_slug TEXT,
            date TEXT, -- YYYY-MM-DD
            discipline TEXT,
            added_count INTEGER,
            removed_count INTEGER,
            PRIMARY KEY (company_slug, date, discipline)
        )
    ''')

    # Analytics: Job Lifecycles (open -> closed) inferred from snapshots
    c.execute('''
        CREATE TABLE IF NOT EXISTS job_lifecycle (
            company_slug TEXT,
            job_key TEXT,
            first_seen_date TEXT, -- YYYY-MM-DD
            last_seen_date TEXT,  -- YYYY-MM-DD (last snapshot containing the job)
            closed_date TEXT,     -- YYYY-MM-DD (null if still open)
            title TEXT,
            url TEXT,
            discipline TEXT,
            seniority TEXT,
            PRIMARY KEY (company_slug, job_key)
        )
    ''')
    c.execute("CREATE INDEX IF NOT EXISTS idx_job_lifecycle_company_closed ON job_lifecycle(company_slug, closed_date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_job_lifecycle_company_first_seen ON job_lifecycle(company_slug, first_seen_date)")

    # Analytics: Lifespan Summary (precomputed for dashboard speed)
    c.execute('''
        CREATE TABLE IF NOT EXISTS company_lifespan_daily (
            company_slug TEXT,
            date TEXT, -- YYYY-MM-DD
            window_days INTEGER,
            closed_roles_count INTEGER,
            median_days REAL,
            p25_days REAL,
            p75_days REAL,
            pct_close_within_7d REAL,
            pct_open_gt_30d REAL,
            pct_open_gt_60d REAL,
            age_bucket_0_3 INTEGER,
            age_bucket_4_7 INTEGER,
            age_bucket_8_14 INTEGER,
            age_bucket_15_30 INTEGER,
            age_bucket_30_plus INTEGER,
            PRIMARY KEY (company_slug, date, window_days)
        )
    ''')

    # Analytics: Momentum & Timing Signals
    c.execute('''
        CREATE TABLE IF NOT EXISTS company_signals_daily (
            company_slug TEXT,
            date TEXT, -- YYYY-MM-DD
            lookback_days INTEGER,
            momentum_state TEXT,        -- Accelerating/Steady/Slowing/Freezing/Volatile/Stable
            momentum_label TEXT,        -- Booming/Freezing/Volatile/Stable/Quiet
            momentum_score REAL,
            is_mover INTEGER,           -- 0/1
            mover_reason TEXT,
            timing_hint TEXT,
            timing_confidence TEXT,     -- high/med/low
            best_post_weekday INTEGER,  -- 0=Mon ... 6=Sun
            best_remove_weekday INTEGER,
            headline_title TEXT,
            headline_url TEXT,
            created_at TEXT,
            PRIMARY KEY (company_slug, date, lookback_days)
        )
    ''')
    c.execute("CREATE INDEX IF NOT EXISTS idx_company_signals_date_mover ON company_signals_daily(date, is_mover)")
    
    # User Preferences: Starred Companies
    c.execute('''
        CREATE TABLE IF NOT EXISTS starred_companies (
            company_slug TEXT PRIMARY KEY,
            starred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
