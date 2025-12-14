import os
import json
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import glob

# Constants
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "news.db")
COMPANIES_PATH = os.path.join(BASE_DIR, "src", "config", "companies.json")
DATA_DIFFS_DIR = os.path.join(BASE_DIR, "data", "diffs")
DATA_FILTERED_DIR = os.path.join(BASE_DIR, "data", "filtered")

def get_connection():
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def get_companies():
    """Returns a list of companies from src/companies.json."""
    if not os.path.exists(COMPANIES_PATH):
        return []
    with open(COMPANIES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_starred_companies():
    """Returns a list of starred company slugs."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT company_slug FROM starred_companies")
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"Error fetching stars: {e}")
        return []
    finally:
        conn.close()

def toggle_star(slug):
    """Toggles star status for a company."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM starred_companies WHERE company_slug = ?", (slug,))
        if cur.fetchone():
            cur.execute("DELETE FROM starred_companies WHERE company_slug = ?", (slug,))
        else:
            cur.execute("INSERT INTO starred_companies (company_slug) VALUES (?)", (slug,))
        conn.commit()
    except Exception as e:
        print(f"Error toggling star: {e}")
    finally:
        conn.close()

def get_open_job_count(slug, ats_type=None):
    """
    Returns total open filtered jobs by finding the latest snapshot in data/filtered.
    If ats_type is not provided, tries to find it.
    """
    slug_safe = slug.replace(" ", "_").lower()
    
    # If we don't know ATS, searching might be slow, but let's try assuming structure:
    # data/filtered/{ats}/{slug}/[timestamp].json
    
    # Find slug dir
    target_dir = None
    if ats_type:
        path = os.path.join(DATA_FILTERED_DIR, ats_type, slug)
        if os.path.isdir(path):
            target_dir = path
    
    if not target_dir:
        # Search all ATS
        if os.path.exists(DATA_FILTERED_DIR):
            for ats in os.listdir(DATA_FILTERED_DIR):
                 path = os.path.join(DATA_FILTERED_DIR, ats, slug)
                 if os.path.isdir(path):
                     target_dir = path
                     break
    
    if not target_dir:
        return 0
        
    # Find latest json file
    # Files are named by timestamp, so mapping sort works
    try:
        files = glob.glob(os.path.join(target_dir, "*.json"))
        if not files:
            return 0
            
        # Get latest file by string creation time or filename (iso format sorts correctly)
        latest_file = max(files, key=os.path.basename)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return len(data)
            return 0
    except Exception as e:
        print(f"Error reading open jobs for {slug}: {e}")
        return 0

def get_all_companies_rich():
    """
    Returns companies list enriched with:
    - is_starred (bool)
    - open_jobs_count (int)
    - name (str)
    """
    raw = get_companies()
    starred = set(get_starred_companies())
    rich = []
    
    for c in raw:
        slug = c["slug"]
        c["name"] = c.get("name", slug.replace("-", " ").title())
        c["is_starred"] = slug in starred
        c["open_jobs_count"] = get_open_job_count(slug, c.get("ats"))
        rich.append(c)
        
    return rich

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
    # Ensure correct parsing of dates
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
                # Safer parsing
                parts = filename.replace(".json", "").split("_")
                ts_str = parts[-1]
                if len(ts_str) < 10: continue
                file_date = ts_str[:10]
                
                if file_date >= start_date:
                    filepath = os.path.join(slug_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Support top-level or nested added
                        added = data.get("added", [])
                        if not added:
                            added = data.get("details", {}).get("added", [])
                            
                        for job in added:
                            # Parse locations to string here to avoid display bugs later?
                            # Or just pass raw.
                            job["_company"] = slug
                            job["_date_added"] = file_date
                            all_added_jobs.append(job)
                            
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

def get_daily_company_stats(days_back=30):
    """
    Returns a DataFrame with daily stats per company for the last N days.
    Used for Heatmaps, Scatter plots, and Trend lines.
    """
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    conn = get_connection()
    query = """
    SELECT 
        company_slug,
        date,
        added_count,
        removed_count,
        (added_count - removed_count) as net_change,
        senior_plus_added_count,
        us_remote_added_count
    FROM job_diffs_daily
    WHERE date >= ?
    ORDER BY date DESC
    """
    try:
        df = pd.read_sql_query(query, conn, params=[start_date])
    except Exception as e:
        print(f"Error reading daily stats: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

