
import logging
from src.news.fetchers.gnews import GNewsFetcher
from src.news.fetchers.finnhub import FinnhubFetcher
from src.news.processor import NewsProcessor
from src.news.models import init_db

def run(run_timestamp, companies, days_back=7, do_init_db=False):
    logger = logging.getLogger("news")
    logger.info("--- Starting News Pipeline ---")

    if do_init_db:
        init_db()
        logger.info("Database initialized.")

    gnews = GNewsFetcher()
    finnhub = FinnhubFetcher()
    processor = NewsProcessor()

    total_new = 0
    stats = {
        "processed": 0,
        "gnews_fetched": 0,
        "finnhub_fetched": 0,
        "failures": 0
    }

    for company in companies:
        slug = company.get("slug")
        name = slug.replace("-", " ").title()
        ticker = company.get("ticker")
        
        logger.info(f"Processing News: {name}")
        stats["processed"] += 1

        # 1. GNews
        try:
            articles = gnews.fetch_company_news(name, days_back=days_back)
            if articles:
                count = processor.process_and_store(articles, slug, "gnews")
                if count > 0:
                    logger.info(f"  GNews: +{count} new")
                stats["gnews_fetched"] += len(articles)
                total_new += count
        except Exception as e:
            logger.error(f"  GNews failed for {slug}: {e}")
            stats["failures"] += 1

        # 2. Finnhub
        if ticker:
            try:
                articles = finnhub.fetch_company_news(ticker, days_back=days_back)
                if articles:
                    count = processor.process_and_store(articles, slug, "finnhub")
                    if count > 0:
                        logger.info(f"  Finnhub: +{count} new")
                    stats["finnhub_fetched"] += len(articles)
                    total_new += count
            except Exception as e:
                logger.error(f"  Finnhub failed for {slug}: {e}")
                stats["failures"] += 1
        
    # Analytics Aggregation
    try:
        from src.analytics.daily_sync import agg_daily_news
        agg_daily_news(days_back=30)
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Analytics Aggregation failed: {e}")

    logger.info(f"--- News Pipeline Complete (+{total_new} articles) ---")
    return {
        "new_articles": total_new,
        "stats": stats
    }
