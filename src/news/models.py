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
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
