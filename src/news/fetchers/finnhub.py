import os
import logging
import finnhub
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class FinnhubFetcher:
    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY")
        self.client = None
        if self.api_key:
            self.client = finnhub.Client(api_key=self.api_key)
        else:
            logging.warning("FINNHUB_API_KEY not found")

    def fetch_company_news(self, ticker: str, days_back: int = 7):
        if not self.client or not ticker:
            return []
            
        today = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        try:
            # Finnhub company news API
            return self.client.company_news(ticker, _from=start_date, to=today)
        except Exception as e:
            logging.error(f"Finnhub Fetch Error for {ticker}: {e}")
            return []
