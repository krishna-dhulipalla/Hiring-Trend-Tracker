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
import time
import random
from datetime import datetime, timedelta


class GNewsAPIError(Exception):
    pass


class GNewsQuotaExceeded(GNewsAPIError):
    pass


class ManualGNewsFetcher:
    def __init__(self):
        self.api_key = os.getenv("GNEWS_API_KEY")
        self.base_url = "https://gnews.io/api/v4/search" # v4 is current
        self.session = requests.Session()

        # GNews often enforces short-window rate limits in addition to daily quotas.
        # Default is conservative to avoid burst 429s when looping many companies.
        try:
            rpm = float(os.getenv("GNEWS_REQUESTS_PER_MINUTE", "18"))
            self.min_interval_seconds = 60.0 / max(rpm, 1.0)
        except ValueError:
            self.min_interval_seconds = 60.0 / 18.0

        try:
            self.max_retries = int(os.getenv("GNEWS_MAX_RETRIES", "3"))
        except ValueError:
            self.max_retries = 3

        self._last_request_at = 0.0

    def _throttle(self) -> None:
        if self.min_interval_seconds <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_request_at
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_request_at = time.monotonic()

    def _extract_error_text(self, resp: requests.Response) -> str:
        try:
            payload = resp.json()
            if isinstance(payload, dict):
                # GNews commonly returns {"errors": [...]} or {"message": "..."}.
                if "message" in payload and isinstance(payload["message"], str):
                    return payload["message"]
                if "errors" in payload:
                    return str(payload["errors"])
            return str(payload)
        except Exception:
            return (resp.text or "").strip()

    def _looks_like_daily_quota(self, text: str) -> bool:
        t = (text or "").lower()
        # Avoid treating short-window throttling as "quota exhausted".
        return ("quota" in t) or ("daily" in t) or ("per day" in t)
    
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
            headers = {
                "User-Agent": "HiringTrendTracker/1.0"
            }

            for attempt in range(self.max_retries + 1):
                self._throttle()
                resp = self.session.get(self.base_url, params=params, headers=headers, timeout=10)

                if resp.status_code == 429:
                    error_text = self._extract_error_text(resp)
                    retry_after = resp.headers.get("Retry-After")

                    # If GNews is telling us the daily quota is exhausted, retries won't help.
                    if self._looks_like_daily_quota(error_text) and attempt == 0:
                        raise GNewsQuotaExceeded(error_text or "GNews quota exceeded (HTTP 429)")

                    if attempt >= self.max_retries:
                        logging.warning(f"GNews rate limited for {company_name} (HTTP 429): {error_text}")
                        return []

                    # Respect Retry-After when present, otherwise exponential backoff with jitter.
                    wait_seconds = None
                    if retry_after:
                        try:
                            wait_seconds = max(0.0, float(retry_after))
                        except ValueError:
                            wait_seconds = None
                    if wait_seconds is None:
                        wait_seconds = min(60.0, (2.0 ** attempt) + random.uniform(0.0, 0.5))

                    time.sleep(wait_seconds)
                    continue

                if resp.status_code >= 400:
                    error_text = self._extract_error_text(resp)
                    logging.error(f"GNews HTTP {resp.status_code} for {company_name}: {error_text}")
                    return []

                data = resp.json()
                return data.get('articles', [])
        except Exception as e:
            logging.error(f"GNews Fetch Error for {company_name}: {e}")
            return []

# Expose the manual one as main class
GNewsFetcher = ManualGNewsFetcher
