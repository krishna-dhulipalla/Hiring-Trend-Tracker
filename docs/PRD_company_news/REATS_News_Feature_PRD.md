# PRD: Company News & Hiring Correlation Feature for REATS

## Executive Summary
Add company news/funding intelligence layer to REATS to enable correlation analysis between corporate announcements and hiring velocity. This unlocks insights like:
- Feature launches → job openings increase
- Layoff announcements → hiring freezes/reductions
- Funding rounds → hiring acceleration
- Restructuring → role mix changes
- Expansion announcements → location diversity changes

---

## Goals & Success Metrics

### Primary Goals
1. **Ingest** company news from multiple free sources daily
2. **Normalize** news into structured format with company identity, sentiment, category, date
3. **Correlate** news events with job snapshots for trend analysis
4. **Visualize** news-hiring relationships in analytics dashboard
5. **Export** correlated data for external analysis

### Success Metrics
- Daily news ingestion for 50+ tracked companies
- <2 hour latency between news publication and ingestion
- >85% accuracy in company name entity matching
- Correlation analysis showing 70%+ alignment with job trends
- <10s query time for multi-company news + hiring analysis

---

## Feature Specifications

### 1. News Ingestion Layer

#### 1.1 Data Sources (Prioritized)
```
Priority 1 (Free, High-Quality):
├─ GNews API
│  ├─ 60,000+ sources
│  ├─ 5 years historical data
│  ├─ 100 requests/day free tier
│  └─ Query: "company_name funding OR layoff OR launch OR partnership"
│
├─ Finnhub Company News API (NA Companies)
│  ├─ Real-time + 1 year historical
│  ├─ Free tier available
│  └─ Strong for US tech companies
│
└─ NewsData.io
   ├─ 85,820+ sources
   ├─ 7+ years archive
   ├─ Free tier with rate limits
   └─ Good for historical backfill

Priority 2 (Specialized, Free):
├─ layoffs.fyi (Tech layoffs only)
│  └─ Community-curated, highly accurate
│
├─ The News API
│  ├─ Free tier, 40,000+ sources
│  └─ 1M+ articles/week
│
└─ Intellizence API (Layoff-specific)
   └─ Specializes in job cut announcements & WARN filings

Priority 3 (Optional Commercial):
├─ NewsAPI.ai (if budget allows)
├─ Perigon API
└─ Webz.io
```

#### 1.2 Data Schema
```json
{
  "news_id": "uuid",
  "source_id": "string (gnews, finnhub, newsdata)",
  "article_url": "string",
  "title": "string",
  "summary": "string (first 500 chars)",
  "full_content": "string (if available)",
  "published_at": "ISO8601 timestamp",
  "ingested_at": "ISO8601 timestamp",
  "company_name": "string",
  "company_id": "reference to companies table",
  "news_category": "enum (funding, layoff, feature_launch, partnership, acquisition, expansion, restructuring, other)",
  "sentiment": "enum (positive, negative, neutral)",
  "confidence_score": "0.0-1.0 (company matching accuracy)",
  "mentioned_keywords": ["array of tags: AI, remote_first, hiring_freeze, etc"],
  "source_domain": "string",
  "author": "string",
  "metadata": {
    "is_verified": "boolean",
    "layoff_count": "number (if applicable)",
    "funding_amount": "string (if applicable)",
    "affected_departments": ["array"]
  }
}
```

#### 1.3 Ingestion Schedule
- **Frequency**: Twice daily (8am, 4pm UTC/CST offset)
- **Lookback**: Last 7 days to catch missed articles
- **Deduplication**: Hash on (source_id, article_url) to avoid duplicates
- **Error handling**: Retry on API timeout, log failures, alert on persistent errors

---

### 2. News Normalization & Matching

#### 2.1 Company Name Resolution
```
Challenge: "Amazon", "AMZN", "Amazon.com", "Amazon Web Services" 
           should all match company_id

Solution:
├─ Maintain canonical company names table
├─ Use fuzzy matching (Levenshtein ratio > 0.85)
├─ Extract company names from article using NER (spaCy/NLTK)
├─ Cross-reference against known ATS domains
└─ Manual override for low-confidence matches
```

#### 2.2 Category Classification
```
Rules-based + ML-backed:
├─ Funding: "Series [A-Z]", "raised", "funding round", "investment"
├─ Layoff: "layoff", "job cut", "reducing headcount", "restructure"
├─ Feature Launch: "launches", "announces", "introduces", "new product"
├─ Partnership: "partner", "collaboration", "integrates with"
├─ Acquisition: "acquires", "acquired by", "merger"
├─ Expansion: "expands to", "opens office", "enters market"
└─ Restructuring: "reorganization", "cost cutting", "efficiency"
```

#### 2.3 Sentiment Detection
```
Library: TextBlob or Hugging Face transformers
├─ Positive: funding, launches, partnerships, expansions
├─ Negative: layoffs, losing customers, competitors, setbacks
└─ Neutral: hiring announcements, org changes (context-dependent)
```

---

### 3. Correlation Engine

#### 3.1 Snapshot Augmentation
```
Extend current job diff snapshot with news context:

{
  "snapshot_id": "uuid",
  "company_id": "string",
  "date": "ISO8601",
  "filtered_snapshot": {...},  // existing
  "diff": {...},               // existing
  "news_events": [
    {
      "news_id": "uuid",
      "category": "funding",
      "sentiment": "positive",
      "days_before_diff": -3,  // 3 days before this snapshot
      "inferred_impact": "likely_hiring_increase"
    }
  ],
  "news_correlation_score": 0.75,
  "annotations": ["Series B funding", "AI team expansion"]
}
```

#### 3.2 Correlation Metrics
```
For each company snapshot, calculate:

1. News → Hiring Lag Analysis
   ├─ If news_date < snapshot_date, days_lag = snapshot_date - news_date
   ├─ Typical lag for hiring response: 3-14 days
   └─ Visualize: heatmap of (news_category, days_lag, job_changes)

2. Event Impact Score (0.0 - 1.0)
   Formula: 
   ├─ sentiment_weight (0.3): +1 for positive, -1 for negative
   ├─ recency_weight (0.2): decay over 30 days
   ├─ confidence_weight (0.3): matching accuracy
   ├─ category_weight (0.2): category-specific impact
   └─ Combined: normalized 0-1 scale

3. Correlated Job Changes
   For each diff in snapshot:
   ├─ added_jobs: correlation with recent positive news?
   ├─ removed_jobs: correlation with recent negative news?
   ├─ role_mix_change: which news events triggered?
   └─ location_changes: expansion/contraction events?
```

#### 3.3 Anomaly Detection
```
Flag mismatches between news & hiring:
├─ Positive news but 0 new jobs (delayed response or noise?)
├─ Layoff announcement but hiring acceleration (redeployment?)
├─ Funding but hiring freeze (cash for operations, not growth?)
└─ Alert on low correlation_score (< 0.3)
```

---

### 4. Analytics & Visualization

#### 4.1 Dashboard Components
```
1. News Feed per Company
   ├─ Timeline of news events
   ├─ Category badges (funding, layoff, launch, etc)
   ├─ Sentiment indicators
   └─ Link to source article

2. Hiring Timeline Overlay
   ├─ Job count trend line
   ├─ News events as markers
   ├─ Colored by sentiment (green=positive, red=negative)
   └─ Tooltip: "3 days after Series B, +15 jobs posted"

3. Correlation Matrix
   ├─ Rows: companies
   ├─ Columns: time periods (weekly)
   ├─ Cells: score indicating strength of news-hiring alignment
   └─ Filter by news category, sentiment

4. Company Comparison
   ├─ Side-by-side news + hiring for 2-3 companies
   ├─ Identify divergent patterns
   └─ Export for report generation
```

#### 4.2 Export Formats
```
├─ CSV: company, date, news_count, job_changes, sentiment, correlation_score
├─ JSON: full correlated snapshots with news metadata
└─ PDF Report: curated narrative with visualizations
```

---

### 5. Data Pipeline Architecture

#### 5.1 Daily ETL Flow
```
1. News Fetch (10 min)
   ├─ Query each API with company names
   ├─ Dedup on source_id + URL
   └─ Store raw_news table

2. Normalization (5 min)
   ├─ NER company extraction
   ├─ Fuzzy matching to company_id
   ├─ Category classification
   ├─ Sentiment analysis
   └─ Store normalized_news table

3. Existing Job Snapshot (already running)
   ├─ Fetch ATS jobs
   ├─ Normalize + filter
   └─ Generate diff

4. Correlation (2 min)
   ├─ For each company snapshot
   ├─ Query normalized_news from past 30 days
   ├─ Calculate correlation metrics
   ├─ Augment snapshot with news_events
   └─ Store correlated_snapshot table

5. Alerts & Notifications (1 min)
   ├─ Check for low correlation_score
   ├─ Flag anomalies
   ├─ Send digest to dashboard/Slack
```

#### 5.2 Data Retention
```
├─ Raw news: 1 year (for backfill & audit)
├─ Normalized news: 2 years
├─ Correlated snapshots: 3 years
├─ Job snapshots: existing policy
└─ Aggregated metrics: perpetual (for trends)
```

---

### 6. Implementation Roadmap

| Phase | Weeks | Deliverables | Owner |
|-------|-------|--------------|-------|
| **Phase 1: Foundation** | 1-2 | API setup, schema, ingestion | Backend |
| | | News collection for 5 pilot companies | Backend |
| **Phase 2: Integration** | 3-4 | Company matching logic | Backend |
| | | Normalization & categorization | Backend/ML |
| | | Job snapshot augmentation | Backend |
| **Phase 3: Analytics** | 5-6 | Correlation metrics | Backend/Analytics |
| | | Dashboard UI | Frontend |
| | | Export functionality | Backend |
| **Phase 4: Scale** | 7+ | Multi-company rollout | Backend |
| | | Performance optimization | DevOps |
| | | Historical backfill | Backend |

---

### 7. Risk & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| API rate limits (free tier) | High | Missed news | Implement caching, queue system, batch requests |
| Company name ambiguity | Medium | False matches | Fuzzy matching + manual review, whitelist |
| News latency (hours to days) | Medium | Stale correlations | Accept 2-7 day correlation lag |
| False positive correlations | High | Misleading insights | Statistical significance testing, anomaly flagging |
| Low free API coverage | Medium | Incomplete data | Combine multiple sources, layoffs.fyi for gaps |

---

### 8. Success Criteria (Post-Launch)

- ✅ Daily news ingestion for 50+ companies with <2 hour latency
- ✅ 85%+ company name matching accuracy
- ✅ Correlated snapshots generated for 100% of job snapshots
- ✅ Dashboard loads in <10s with 3+ months of historical data
- ✅ Users report actionable insights (3+ aha moments per week in logs)
- ✅ Correlation signal shows >70% alignment with manual spot-checks

---

## Acceptance Criteria

**MVP (Must Have)**
- [ ] News ingestion from GNews + Finnhub (2 sources)
- [ ] Company name matching for 50 tracked companies
- [ ] Normalized news schema in database
- [ ] Basic correlation score calculation
- [ ] News timeline on company dashboard
- [ ] Daily ingestion pipeline running stably

**Nice to Have (Phase 2)**
- [ ] Multi-source aggregation (NewsData.io, layoffs.fyi)
- [ ] Advanced sentiment analysis (Hugging Face)
- [ ] Correlation heatmaps
- [ ] PDF export reports
- [ ] Anomaly alerts
- [ ] Historical backfill (2+ years)

---

## Metrics to Track

1. **Ingestion Health**: articles/day, API errors, dedup rate
2. **Data Quality**: company match accuracy, category classification F1 score
3. **Performance**: pipeline latency, query response time
4. **Engagement**: dashboard views, correlation insights exported, users actioned on insights
5. **Correlation Strength**: R² between news events and hiring changes (by category)
