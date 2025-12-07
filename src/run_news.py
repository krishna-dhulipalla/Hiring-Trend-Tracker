import os
import json
import logging
import argparse
from datetime import datetime
from src.news.models import init_db
from src.news.fetchers.gnews import GNewsFetcher
from src.news.fetchers.finnhub import FinnhubFetcher
from src.news.processor import NewsProcessor

# Setup Logging
def setup_logging():
    # Similar to main.py
    run_timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    log_dir = os.path.join("logs", run_timestamp)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, "news_summary.txt")
    
    # Configure root logger to file
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return log_file

def load_companies():
    path = os.path.join(os.path.dirname(__file__), "companies.json")
    with open(path, 'r') as f:
        return json.load(f)

def main():
    parser = argparse.ArgumentParser(description="Run News Ingestion")
    parser.add_argument("--init-db", action="store_true", help="Initialize the database")
    parser.add_argument("--days", type=int, default=7, help="Days back to fetch")
    args = parser.parse_args()

    log_file = setup_logging()
    logging.info(f"Starting News Run. Logs at {log_file}")
    logging.info(f"Arguments: {args}")

    if args.init_db:
        init_db()
        logging.info("Database initialized.")

    companies = load_companies()
    
    gnews = GNewsFetcher()
    finnhub = FinnhubFetcher()
    processor = NewsProcessor()

    total_new = 0
    stats = {
        "processed_companies": 0,
        "gnews_fetched": 0,
        "finnhub_fetched": 0,
        "gnews_failures": 0,
        "finnhub_failures": 0
    }

    for company in companies:
        slug = company.get("slug")
        name = slug.replace("-", " ").title() # Simple heuristic for name
        ticker = company.get("ticker")
        
        logging.info(f"Processing {name} ({slug})...")
        stats["processed_companies"] += 1

        # 1. GNews
        try:
            articles = gnews.fetch_company_news(name, days_back=args.days)
            if articles:
                count = processor.process_and_store(articles, slug, "gnews")
                logging.info(f"  GNews: Found {len(articles)}, New {count}")
                stats["gnews_fetched"] += len(articles)
                total_new += count
        except Exception as e:
            logging.error(f"  GNews failed for {slug}: {e}")
            stats["gnews_failures"] += 1

        # 2. Finnhub
        if ticker:
            try:
                articles = finnhub.fetch_company_news(ticker, days_back=args.days)
                if articles:
                    count = processor.process_and_store(articles, slug, "finnhub")
                    logging.info(f"  Finnhub: Found {len(articles)}, New {count}")
                    stats["finnhub_fetched"] += len(articles)
                    total_new += count
            except Exception as e:
                logging.error(f"  Finnhub failed for {slug}: {e}")
                stats["finnhub_failures"] += 1
        else:
            logging.info("  Skipping Finnhub (no ticker)")

    logging.info(f"Done. Total new articles stored: {total_new}")
    
    # Log Summary
    logging.info("-" * 20)
    logging.info("RUN SUMMARY")
    logging.info(f"Companies Processed: {stats['processed_companies']}")
    logging.info(f"Total New Articles: {total_new}")
    logging.info(f"GNews: Fetched {stats['gnews_fetched']}, Failures {stats['gnews_failures']}")
    logging.info(f"Finnhub: Fetched {stats['finnhub_fetched']}, Failures {stats['finnhub_failures']}")
    logging.info("-" * 20)



if __name__ == "__main__":
    main()
