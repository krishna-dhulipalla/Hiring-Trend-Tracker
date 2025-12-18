
import os
import json
import argparse
import datetime
from src.utils import setup_logging
from src.pipelines import jobs, news
from src.news.models import init_db
from src.analytics.signal_engine import compute_and_store_signals

def load_companies():
    """Loads companies from src/config/companies.json."""
    path = os.path.join(os.path.dirname(__file__), "config", "companies.json")
    with open(path, 'r') as f:
        return json.load(f)

def main():
    parser = argparse.ArgumentParser(description="Hiring Trend Tracker - Unified Scraper")
    parser.add_argument("--jobs", action="store_true", help="Run Job Scraper")
    parser.add_argument("--news", action="store_true", help="Run News Scraper")
    parser.add_argument("--all", action="store_true", help="Run Both (default)")
    parser.add_argument("--init-db", action="store_true", help="Init News DB")
    parser.add_argument("--days", type=int, default=7, help="Days back for news")
    
    args = parser.parse_args()
    
    # Default to run all if nothing specific selected
    if not (args.jobs or args.news):
        args.all = True

    # 1. Timestamp & Logging
    run_timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    logger, log_file = setup_logging(run_timestamp)
    
    print(f"Starting Run: {run_timestamp}")
    print(f"Log File: {log_file}")
    
    try:
        companies = load_companies()
    except Exception as e:
        logger.critical(f"Failed to load companies config: {e}")
        return

    init_db()
    if args.init_db:
        logger.info("Database initialized.")

    # 2. Run Jobs
    if args.jobs or args.all:
        print("\n--- Running Job Scraper ---")
        job_results = jobs.run(run_timestamp, companies)
        print(f"Jobs Done: {job_results['raw']} raw, {job_results['filtered']} filtered")

    # 3. Run News
    if args.news or args.all:
        print("\n--- Running News Scraper ---")
        news_results = news.run(run_timestamp, companies, days_back=args.days, do_init_db=False)
        print(f"News Done: +{news_results['new_articles']} new articles")

    # 4. Momentum/timing signals (used by the dashboard)
    try:
        compute_and_store_signals(run_timestamp, lookback_days=7)
    except Exception as e:
        logger.error(f"Signal computation failed: {e}")

    print("\nAll Tasks Completed.")

if __name__ == "__main__":
    main()
