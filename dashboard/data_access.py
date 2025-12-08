import os
import json
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# Constants
DB_PATH = "news.db"
COMPANIES_PATH = "src/companies.json"
DATA_DIFFS_DIR = "data/diffs"

def get_connection():
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def get_companies():
    """Returns a list of companies from src/companies.json."""
    if not os.path.exists(COMPANIES_PATH):
        return []
    with open(COMPANIES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_all_companies():
    """Alias for get_companies for consistency."""
    return get_companies()

def get_job_diffs_daily(company_slug=None, start_date=None, end_date=None):
    conn = get_connection()
    query = "SELECT * FROM job_diffs_daily WHERE 1=1"
    params = []
    if company_slug:
        query += " AND company_slug = ?"
        params.append(company_slug)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " ORDER BY date DESC"
    try:
        df = pd.read_sql_query(query, conn, params=params)
    except Exception as e:
        print(f"Error reading job_diffs_daily: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

def get_company_news_daily(company_slug=None, start_date=None, end_date=None):
    conn = get_connection()
    query = "SELECT * FROM company_news_daily WHERE 1=1"
    params = []
    if company_slug:
        query += " AND company_slug = ?"
        params.append(company_slug)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " ORDER BY date DESC"
    try:
        df = pd.read_sql_query(query, conn, params=params)
    except Exception as e:
        print(f"Error reading company_news_daily: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

def get_diff_for(company_slug, date_str):
    found_file = None
    if os.path.exists(DATA_DIFFS_DIR):
        for ats in os.listdir(DATA_DIFFS_DIR):
            ats_dir = os.path.join(DATA_DIFFS_DIR, ats)
            if not os.path.isdir(ats_dir): continue
            slug_dir = os.path.join(ats_dir, company_slug)
            if os.path.isdir(slug_dir):
                for filename in os.listdir(slug_dir):
                    if filename.endswith(".json") and date_str in filename:
                        found_file = os.path.join(slug_dir, filename)
                        break
            if found_file: break
    if found_file and os.path.exists(found_file):
        try:
            with open(found_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading diff file {found_file}: {e}")
            return None
    return None

def get_available_diff_dates(company_slug):
    dates = set()
    if os.path.exists(DATA_DIFFS_DIR):
        for ats in os.listdir(DATA_DIFFS_DIR):
            ats_dir = os.path.join(DATA_DIFFS_DIR, ats)
            if not os.path.isdir(ats_dir): continue
            slug_dir = os.path.join(ats_dir, company_slug)
            if os.path.isdir(slug_dir):
                for filename in os.listdir(slug_dir):
                    if not filename.endswith(".json"): continue
                    try:
                        parts = filename.replace(".json", "").split("_")
                        ts_str = parts[-1] 
                        if len(ts_str) >= 10:
                            dates.add(ts_str[:10])
                    except: pass
    return sorted(list(dates), reverse=True)

def get_recent_added_jobs(days_back=7):
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    all_added_jobs = []
    companies = get_companies()
    for company in companies:
        slug = company["slug"]
        ats = company["ats"]
        slug_dir = os.path.join(DATA_DIFFS_DIR, ats, slug)
        if not os.path.exists(slug_dir): continue
        for filename in os.listdir(slug_dir):
            if not filename.endswith(".json"): continue
            try:
                parts = filename.replace(".json", "").split("_")
                ts_str = parts[-1]
                if len(ts_str) < 10: continue
                file_date = ts_str[:10]
                if file_date >= start_date:
                    filepath = os.path.join(slug_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            added = data.get("added", [])
                            if not added:
                                added = data.get("details", {}).get("added", [])
                            for job in added:
                                job["_company"] = slug
                                job["_date_added"] = file_date
                                all_added_jobs.append(job)
                    except Exception as e:
                        print(f"Error reading {filepath}: {e}")
                        continue
            except Exception: continue
    return all_added_jobs

def get_global_stats(days_back=14):
    """
    Returns aggregated stats for all companies over the lookback window.
    """
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    df = get_job_diffs_daily(start_date=start_date)
    
    if df.empty:
        return {
            "total_added": 0,
            "total_removed": 0,
            "net_change": 0,
            "active_companies": 0
        }
    
    return {
        "total_added": int(df["added_count"].sum()),
        "total_removed": int(df["removed_count"].sum()),
        "net_change": int(df["added_count"].sum() - df["removed_count"].sum()),
        "active_companies": int(df["company_slug"].nunique())
    }

def get_leaderboard(days_back=14):
    """
    Returns a DataFrame of companies ranked by activity in window.
    """
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    conn = get_connection()
    query = """
    SELECT 
        company_slug,
        SUM(added_count) as added_count,
        SUM(removed_count) as removed_count,
        (SUM(added_count) - SUM(removed_count)) as net_change
    FROM job_diffs_daily
    WHERE date >= ?
    GROUP BY company_slug
    ORDER BY added_count DESC
    """
    try:
        df = pd.read_sql_query(query, conn, params=[start_date])
    except Exception as e:
        print(f"Error reading leaderboard: {e}")
        df = pd.DataFrame(columns=["company_slug", "added_count", "removed_count", "net_change"])
    finally:
        conn.close()
    return df

def get_market_trend(days_back=14):
    """
    Returns daily aggregate added/removed counts for trend chart.
    """
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    conn = get_connection()
    query = """
    SELECT 
        date,
        SUM(added_count) as added_count,
        SUM(removed_count) as removed_count
    FROM job_diffs_daily
    WHERE date >= ?
    GROUP BY date
    ORDER BY date ASC
    """
    try:
        df = pd.read_sql_query(query, conn, params=[start_date])
    except Exception as e:
        print(f"Error reading market trend: {e}")
        df = pd.DataFrame(columns=["date", "added_count", "removed_count"])
    finally:
        conn.close()
    return df
