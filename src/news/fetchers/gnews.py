import os
import logging
from gnews import GNews
from dotenv import load_dotenv

load_dotenv()

class GNewsFetcher:
    def __init__(self):
        self.api_key = os.getenv("GNEWS_API_KEY")
        if not self.api_key:
            logging.warning("GNEWS_API_KEY not found in environment")
        
        self.client = GNews(language='en', country='US', max_results=10)
        # Monkey patch if needed, or just set the key if the library supports it directly. 
        # The library usually needs set up slightly differently depending on version.
        # Assuming standard usage based on docs or simple usage:
        # It seems 'gnews' library might be a wrapper. 
        # Actually simplest is to use requests directly as per PRD plan because wrappers vary.
        # But 'gnews' pip package exists. Let's stick to the PRD plan which suggested requests for control
        # OR use the library if it's convenient.
        # PRD said: "Implement GNews API wrapper - Query building...".
        # Let's use `requests` to be safe and avoid library quirks, aligning with PRD code example.
        pass

import requests
from datetime import datetime, timedelta

class ManualGNewsFetcher:
    def __init__(self):
        self.api_key = os.getenv("GNEWS_API_KEY")
        self.base_url = "https://gnews.io/api/v4/search" # v4 is current
    
    def fetch_company_news(self, company_name: str, days_back: int = 7):
        if not self.api_key:
            print("No GNews API Key")
            return []

        from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Query: "Company Name" AND (funding OR layoff OR ...)
        # Using strict phrases can help
        keywords = "funding OR layoff OR acquisition OR launch OR hiring OR raised"
        q = f'"{company_name}" AND ({keywords})'
        
        params = {
            'q': q,
            'token': self.api_key,
            'lang': 'en',
            'country': 'us',
            'max': 10,
            'sortby': 'publishedAt',
            'from': from_date
        }
        
        try:
            resp = requests.get(self.base_url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data.get('articles', [])
        except Exception as e:
            logging.error(f"GNews Fetch Error for {company_name}: {e}")
            return []

# Expose the manual one as main class
GNewsFetcher = ManualGNewsFetcher
