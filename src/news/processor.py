import json
import uuid
import logging
import sqlite3
from datetime import datetime
from src.news.models import get_connection

# Categories buckets
CATEGORIES = {
    "layoff": ["layoff", "job cut", "reducing workforce", "hiring freeze", "downsizing", "let go", "reduction in force"],
    "earnings": ["earnings", "revenue", "profit", "quarterly results", "financial results", "fiscal"],
    "funding": ["funding", "raised", "series a", "series b", "series c", "investment", "capital", "venture"],
    "acquisition": ["acquire", "bought", "merger", "acquisition"],
    "ai_announcement": ["ai model", "artificial intelligence", "llm", "generative ai", "gpt", "chatbot", "gemini", "claude"],
    "product": ["launch", "release", "new feature", "announced", "unveiled", "product"],
    "hiring": ["hiring", "expanding", "new roles", "growing team", "recruiting"],
    "regulatory": ["regulatory", "lawsuit", "compliance", "fine", "investigation", "gdpr", "ftc"],
}

class NewsProcessor:
    def __init__(self):
        pass

    def categorize(self, text):
        text_lower = text.lower()
        for cat, keywords in CATEGORIES.items():
            if any(k in text_lower for k in keywords):
                return cat
        return "other"

    def process_and_store(self, articles, company_slug, source_name):
        conn = get_connection()
        c = conn.cursor()
        
        count = 0
        for art in articles:
            # Map fields based on source
            raw_id = str(uuid.uuid4())
            try:
                if source_name == "gnews":
                    source_article_id = art.get('url')
                    title = art.get('title')
                    desc = art.get('description')
                    pub_at = art.get('publishedAt')
                    source_domain = art.get('source', {}).get('name')
                    raw_json = json.dumps(art)
                    url = art.get('url')
                elif source_name == "finnhub":
                    source_article_id = str(art.get('id'))
                    title = art.get('headline')
                    desc = art.get('summary')
                    # Finnhub returns timestamp int
                    ts = art.get('datetime')
                    pub_at = datetime.utcfromtimestamp(ts).isoformat() + "Z" if ts else None
                    source_domain = art.get('source')
                    raw_json = json.dumps(art)
                    url = art.get('url')
                
                # Deduplication check
                # Check if exists
                c.execute("SELECT id FROM raw_news WHERE source_id=? AND source_article_id=?", (source_name, source_article_id))
                existing = c.fetchone()
                
                if existing:
                    continue

                # Insert Raw
                c.execute('''
                    INSERT INTO raw_news (id, source_id, source_article_id, article_url, title, description, published_at, ingested_at, source_domain, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (raw_id, source_name, source_article_id, url, title, desc, pub_at, datetime.utcnow().isoformat(), source_domain, raw_json))
                
                # Normalize
                norm_id = str(uuid.uuid4())
                full_text = f"{title}. {desc}"
                category = self.categorize(full_text)
                
                c.execute('''
                    INSERT INTO normalized_news (id, raw_news_id, company_slug, news_category, published_at, title, summary, source_url, processed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (norm_id, raw_id, company_slug, category, pub_at, title, desc, url, datetime.utcnow().isoformat()))
                
                count += 1
            except Exception as e:
                logging.error(f"Error processing article: {e}")
                
        conn.commit()
        conn.close()
        return count
