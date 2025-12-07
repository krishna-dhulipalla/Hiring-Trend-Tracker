# Implementation Plan: News Feature for REATS

## Quick Start (Next 48 Hours)

### Step 1: API Registrations (30 min)
```
1. GNews API
   └─ Go to https://gnews.io
   └─ Click "Get Free API Key"
   └─ Enter email, get key instantly
   └─ No credit card needed

2. Finnhub
   └─ Go to https://finnhub.io
   └─ Sign up (GitHub OAuth available)
   └─ Get API key from dashboard
   └─ No credit card needed

3. layoffs.fyi
   └─ Visit https://layoffs.fyi
   └─ Bookmark for scraper development
```

### Step 2: Test API Calls (1 hour)
```bash
# Test GNews
curl "https://gnews.io/api/search?q=OpenAI%20funding&token=YOUR_KEY&max=5"

# Test Finnhub (need ticker)
curl "https://finnhub.io/api/v1/company-news?symbol=AAPL&from=2025-01-01&token=YOUR_KEY"
```

### Step 3: Choose your Stack (30 min)
Based on your project setup, pick one:

**Option A: Python (If Backend is Python)**
```
Framework: 
  - If using FastAPI/Django: Add news ingestion as background task
  - If using Airflow: Add DAG for news pipeline
  - If using Celery: Add periodic task

Libraries:
  - gnews (pip install gnews)
  - finnhub (pip install finnhub)
  - requests (existing)
  - spacy (for NER/tagging)
  - textblob (for sentiment)
  - beautifulsoup4 (for layoffs.fyi scraper)

Database: Use existing DB (PostgreSQL recommended)
  - Add tables: news, news_events, correlations
```

**Option B: Node.js/TypeScript (If Backend is Node)**
```
Framework: 
  - If using Express/NestJS: Add routes + middleware
  - If using Bull/BullMQ: Queue for async processing
  - If using Cron: Schedule tasks

Libraries:
  - axios (HTTP requests)
  - cheerio (web scraping layoffs.fyi)
  - sentiment (sentiment analysis)
  - compromise (lightweight NLP)
  - node-cron (scheduling)

Database: Use existing DB (same)
```

---

## Week 1-2: MVP Implementation Roadmap

### Day 1-2: Project Setup
```
[ ] Create feature branch: feature/company-news
[ ] Add API keys to .env
[ ] Create database schema (see below)
[ ] Add dependencies to package.json/requirements.txt
[ ] Create directory structure:
    src/
    ├─ news/
    │  ├─ fetchers/       (API integrations)
    │  ├─ processors/     (normalization)
    │  ├─ storage/        (DB operations)
    │  ├─ models.py       (schema definitions)
    │  └─ service.py      (orchestration)
    └─ tests/
       └─ test_news.py
```

### Day 3-4: GNews Integration
```
[ ] Implement GNews API wrapper
    - Query building (company names)
    - Rate limit handling
    - Retry logic
    - Error handling

[ ] Test with 5-10 companies
    - Verify API responses
    - Check article count/day
    - Measure latency

[ ] Store raw articles to DB
```

### Day 5-6: Finnhub Integration
```
[ ] Create company ticker mapping
    - Build lookup table (company_name → ticker)
    - Test for your tracked companies
    - Handle missing tickers (fall back to GNews)

[ ] Implement Finnhub API wrapper
    - Real-time news pulling
    - 1-year historical fetch (optional)
    - Error handling for missing tickers

[ ] Deduplication logic
    - Hash articles across sources
    - Prevent duplicates in DB
```

### Day 7: Normalization & Storage
```
[ ] Build normalization pipeline
    - Company name resolution (fuzzy matching)
    - Category classification (rules-based)
    - Sentiment analysis (local library)
    - Timestamp standardization

[ ] Create normalized_news table
    - Schema matches PRD spec
    - Indexes on (company_id, published_at)

[ ] Build batch processor
    - Read raw articles
    - Normalize each
    - Store to normalized_news
    - Log errors
```

### Day 8-10: Testing & Optimization
```
[ ] Unit tests
    - API fetchers
    - Normalization logic
    - Company matching
    - Sentiment detection

[ ] Integration tests
    - End-to-end pipeline (fetch → normalize → store)
    - Error scenarios (API down, invalid data)
    - Rate limit handling

[ ] Performance test
    - 100+ articles processing
    - Query latency
    - Storage efficiency

[ ] Manual QA
    - Review 20 articles for accuracy
    - Check categorization
    - Verify sentiment scores
```

---

## Database Schema (SQL)

```sql
-- Companies table (extend existing)
ALTER TABLE companies ADD COLUMN news_status VARCHAR(20) DEFAULT 'active';

-- Raw news (as-received from APIs)
CREATE TABLE raw_news (
    id UUID PRIMARY KEY,
    source_id VARCHAR(50),  -- 'gnews', 'finnhub', 'newsdata'
    source_article_id VARCHAR(500) UNIQUE,
    article_url VARCHAR(2000),
    title VARCHAR(500),
    description TEXT,
    published_at TIMESTAMP,
    ingested_at TIMESTAMP DEFAULT NOW(),
    source_domain VARCHAR(200),
    author VARCHAR(200),
    image_url VARCHAR(500),
    raw_json JSONB,  -- Store full API response
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_source_date (source_id, published_at),
    INDEX idx_published (published_at DESC)
);

-- Normalized news (after processing)
CREATE TABLE normalized_news (
    id UUID PRIMARY KEY,
    raw_news_id UUID REFERENCES raw_news(id),
    company_id UUID REFERENCES companies(id),
    company_name VARCHAR(200),
    news_category VARCHAR(50),  -- 'funding', 'layoff', 'feature_launch', etc
    sentiment VARCHAR(20),  -- 'positive', 'negative', 'neutral'
    sentiment_score FLOAT,  -- -1 to +1
    confidence_score FLOAT,  -- 0 to 1 (company matching accuracy)
    title VARCHAR(500),
    summary TEXT,
    full_content TEXT,
    published_at TIMESTAMP,
    source_url VARCHAR(2000),
    source_domain VARCHAR(200),
    keywords VARCHAR[],  -- Array of tags
    metadata JSONB,  -- layoff_count, funding_amount, affected_depts, etc
    processed_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_company_date (company_id, published_at DESC),
    INDEX idx_category (news_category),
    INDEX idx_sentiment (sentiment),
    UNIQUE(raw_news_id)
);

-- News correlations (link to job snapshots)
CREATE TABLE news_correlations (
    id UUID PRIMARY KEY,
    snapshot_id UUID REFERENCES job_snapshots(id),
    company_id UUID REFERENCES companies(id),
    news_ids UUID[],  -- Array of normalized_news IDs
    days_window INT DEFAULT 30,  -- Look back window
    correlation_score FLOAT,  -- 0 to 1
    event_count INT,
    positive_events INT,
    negative_events INT,
    inferred_impact VARCHAR(100),  -- 'likely_hiring_increase', etc
    annotations TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(snapshot_id, company_id)
);

-- Analytics summary (daily aggregates)
CREATE TABLE news_analytics (
    id UUID PRIMARY KEY,
    company_id UUID REFERENCES companies(id),
    date DATE,
    articles_count INT,
    categories JSONB,  -- {funding: 1, layoff: 2, ...}
    sentiment_average FLOAT,
    positive_count INT,
    negative_count INT,
    neutral_count INT,
    job_changes JSONB,  -- Linked job diff summary
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(company_id, date)
);
```

---

## Code Examples

### Python: GNews Fetcher
```python
# src/news/fetchers/gnews_fetcher.py
import requests
from typing import List, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class GNewsFetcher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://gnews.io/api/v1/search"
        self.max_articles_per_request = 10
    
    def fetch_company_news(self, company_name: str, days_back: int = 7) -> List[Dict]:
        """Fetch news for a company"""
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')
        
        # Build query
        keywords = [company_name, 'funding OR layoff OR launch OR announcement']
        query = f'"{company_name}" ({keywords[1]})'
        
        params = {
            'q': query,
            'token': self.api_key,
            'max': self.max_articles_per_request,
            'sortby': 'publishedAt',
            'from': from_date,
            'to': to_date
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for article in data.get('articles', []):
                articles.append({
                    'source_id': 'gnews',
                    'source_article_id': article['url'],
                    'title': article['title'],
                    'description': article['description'],
                    'article_url': article['url'],
                    'published_at': article['publishedAt'],
                    'source_domain': article['source']['name'],
                    'image_url': article['image'],
                    'raw_json': article
                })
            
            logger.info(f"Fetched {len(articles)} articles for {company_name}")
            return articles
            
        except requests.RequestException as e:
            logger.error(f"Error fetching news for {company_name}: {str(e)}")
            return []

# src/news/service.py (Orchestration)
from gnews_fetcher import GNewsFetcher
from processors import NormalizeNewsProcessor
from storage import NewsStorage

class NewsService:
    def __init__(self, db, gnews_key: str, finnhub_key: str):
        self.db = db
        self.gnews_fetcher = GNewsFetcher(gnews_key)
        self.processor = NormalizeNewsProcessor(db)
        self.storage = NewsStorage(db)
    
    async def fetch_and_process_daily(self):
        """Run daily news fetch and processing"""
        companies = self.db.query("SELECT id, name FROM companies WHERE news_status = 'active'")
        
        all_articles = []
        for company in companies:
            # Fetch from all sources
            gnews_articles = self.gnews_fetcher.fetch_company_news(company['name'])
            all_articles.extend(gnews_articles)
        
        # Store raw articles
        self.storage.store_raw_articles(all_articles)
        
        # Normalize
        normalized = self.processor.process_batch(all_articles)
        
        # Store normalized
        self.storage.store_normalized_articles(normalized)
        
        # Correlate with job snapshots
        await self.correlate_with_jobs()
        
        return len(all_articles)
    
    async def correlate_with_jobs(self):
        """Link news to job snapshots"""
        # Query recent snapshots
        snapshots = self.db.query("""
            SELECT DISTINCT ON (company_id) * FROM job_snapshots 
            ORDER BY company_id, date DESC LIMIT 100
        """)
        
        for snapshot in snapshots:
            # Get news from past 30 days
            news = self.db.query("""
                SELECT * FROM normalized_news 
                WHERE company_id = %s 
                AND published_at > NOW() - INTERVAL '30 days'
                ORDER BY published_at DESC
            """, snapshot['company_id'])
            
            if news:
                correlation_score = self.calculate_correlation(snapshot, news)
                self.db.execute("""
                    INSERT INTO news_correlations 
                    (snapshot_id, company_id, news_ids, correlation_score, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """, snapshot['id'], snapshot['company_id'], 
                    [n['id'] for n in news], correlation_score)

# Usage in FastAPI
from fastapi import FastAPI, BackgroundTasks
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI()
news_service = NewsService(db, gnews_key=GNEWS_KEY, finnhub_key=FINNHUB_KEY)

scheduler = BackgroundScheduler()
scheduler.add_job(news_service.fetch_and_process_daily, 'cron', hour='8,16')
scheduler.start()

@app.get("/news/{company_id}")
async def get_company_news(company_id: str):
    """Get news for a company"""
    news = db.query("""
        SELECT * FROM normalized_news 
        WHERE company_id = %s 
        ORDER BY published_at DESC LIMIT 50
    """, company_id)
    return {'news': news, 'count': len(news)}
```

### Node.js: Finnhub Fetcher
```typescript
// src/news/fetchers/finnhub.fetcher.ts
import axios from 'axios';

interface Article {
  sourceId: string;
  title: string;
  description: string;
  url: string;
  publishedAt: string;
  source: string;
}

export class FinnhubFetcher {
  private baseUrl = 'https://finnhub.io/api/v1';
  
  constructor(private apiKey: string) {}
  
  async fetchCompanyNews(ticker: string, daysBack: number = 7): Promise<Article[]> {
    const fromDate = new Date();
    fromDate.setDate(fromDate.getDate() - daysBack);
    
    try {
      const response = await axios.get(`${this.baseUrl}/company-news`, {
        params: {
          symbol: ticker,
          from: fromDate.toISOString().split('T')[0],
          to: new Date().toISOString().split('T')[0],
          token: this.apiKey
        }
      });
      
      return response.data.map((article: any) => ({
        sourceId: 'finnhub',
        title: article.headline,
        description: article.summary,
        url: article.url,
        publishedAt: new Date(article.datetime * 1000).toISOString(),
        source: article.source,
        image: article.image
      }));
    } catch (error) {
      console.error(`Error fetching Finnhub news for ${ticker}:`, error);
      return [];
    }
  }
}
```

---

## Deployment Checklist

- [ ] Database migrations applied
- [ ] API keys securely stored in .env
- [ ] Rate limiting implemented (queue system)
- [ ] Monitoring/alerting for API failures
- [ ] Logging configured
- [ ] Tests passing (unit + integration)
- [ ] Code review completed
- [ ] Documentation updated
- [ ] Staging environment tested
- [ ] Performance baseline measured
- [ ] Rollback plan documented
- [ ] Team trained on new feature
- [ ] Analytics instrumentation added

---

## Monitoring & Alerts

```python
# Monitor these metrics:
metrics = {
    'articles_fetched_per_day': 200,  # Target
    'processing_latency_sec': 120,    # Max acceptable
    'normalization_success_rate': 0.95,  # >95%
    'company_match_accuracy': 0.85,   # >85%
    'api_error_rate': 0.01,           # <1%
    'dedup_rate': 0.1                 # ~10% duplicates expected
}

# Alert if:
- Articles fetched < 50 (API down?)
- Processing latency > 300s (bottleneck?)
- Company match accuracy < 0.75 (tuning needed?)
- API error rate > 0.05 (investigation needed)
```

---

## Next Steps

1. **Pick your primary API**: GNews or Finnhub (recommend both)
2. **Decide on stack**: Python or Node.js?
3. **Create feature branch** and project structure
4. **Week 1**: Implement GNews + Finnhub fetchers
5. **Week 2**: Build normalization + storage
6. **Week 3**: Add correlation logic + basic dashboard
7. **Week 4+**: Scale + optimize

---

## Questions?

- **Rate limits hitting you?** Use caching (Redis) + queue system (Celery/Bull)
- **Company matching failing?** Build manual whitelist for important companies
- **Need full-text articles?** Consider NewsAPI.ai in Phase 2
- **Layoffs tracking priority?** Build layoffs.fyi scraper immediately (Day 1)
- **Want ML sentiment?** Use Hugging Face transformers (more accurate than TextBlob)

**Start small, iterate fast, prove value before scaling.**
