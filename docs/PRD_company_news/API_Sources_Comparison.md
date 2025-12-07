# API Sources Comparison & Selection Guide for REATS News Feature

## Executive Summary
For REATS at your current stage (startup/indie), **prioritize free tiers** with good coverage. Start with **GNews API** (best free tier) + **Finnhub** (US tech focus) + **layoffs.fyi** (specialized accuracy). Avoid paid APIs until you hit scale.

---

## Tier 1: Recommended Free Sources (Start Here)

### 1. GNews API ⭐ PRIMARY CHOICE FOR MVP
**Website**: https://gnews.io  
**Status**: Active, reliable, popular

#### Pricing & Rate Limits
```
Free Tier:
├─ 100 requests/day
├─ 10 articles per request
├─ 5 years historical data (back to 2020)
├─ 60,000+ sources globally
├─ Response: ~200-500ms
└─ No credit card required

Upgrade Options (if needed):
├─ Pro: €49.99/month → 2,500 requests/day
├─ Business: €99.99/month → 5,000 requests/day
└─ Enterprise: custom
```

#### Strengths
- ✅ **Fastest free tier** (100 requests/day is generous for MVP)
- ✅ Excellent documentation & SDKs (Python, JS, Java)
- ✅ Full-text search across title + content
- ✅ Real-time updates (minutes latency)
- ✅ International coverage (60K+ sources)
- ✅ No authentication complexity
- ✅ Reliable 99%+ uptime

#### Weaknesses
- ❌ **No full article body** (title + snippet only, ~200 chars)
- ❌ Limited filtering (no sentiment API, no NER)
- ❌ No layoff-specific signals

#### Query Examples
```bash
# Funding announcements
https://gnews.io/api/search?q=Apple%20Series%20funding&token=YOUR_KEY

# Layoff news
https://gnews.io/api/search?q=Amazon%20layoff%20job%20cut&token=YOUR_KEY

# Feature launch
https://gnews.io/api/search?q=OpenAI%20announces%20OR%20launches&token=YOUR_KEY

# Multi-keyword with dates
q="company_name (funding OR layoff OR expansion)" 
from=2025-12-01
to=2025-12-07
sortby=publishedAt
```

#### SDK Integration
```python
from gnews import GNews

google_news = GNews(language='en', country='US', max_results=10)

# Search funding news
news_funding = google_news.get_news('Microsoft funding')

# Search + date filter
articles = google_news.get_news_by_topic('Apple')

# Custom search with date range
articles = google_news.get_news(
    'Tesla "job cut" OR "layoff"',
    from_='2025-12-01',
    to_='2025-12-07'
)

# Result structure
for article in articles:
    print({
        'title': article['title'],
        'description': article['description'],  # ~200 chars
        'url': article['url'],
        'image': article['image'],
        'published at': article['published at'],
        'source': article['source']
    })
```

#### Best For
✅ **MVP phase** (start here)  
✅ General news about company announcements  
✅ Budget-conscious projects  
✅ Real-time monitoring  

#### Not Ideal For
❌ Full article analysis (need full text)  
❌ Advanced NLP (no sentiment/NER from API)  
❌ Specialization in layoffs (too broad)  

#### Recommendation
**USE FOR MVP** (Week 1-4). Collect 100-200 articles/day easily. Process titles + descriptions with local NLP (spaCy, TextBlob).

---

### 2. Finnhub Company News API ⭐ SECONDARY CHOICE FOR TECH
**Website**: https://finnhub.io  
**Status**: Active, enterprise-grade

#### Pricing & Rate Limits
```
Free Tier:
├─ 60 requests/minute
├─ Real-time + 1 year historical
├─ North American companies ONLY
├─ Company identifiers via ticker (AAPL, MSFT, etc)
├─ ~50ms response time
└─ No credit card required

Premium (if needed):
├─ Pro: $10/month → 600 requests/minute
├─ Research: $99/month → enterprise limits
└─ Custom pricing for scale
```

#### Strengths
- ✅ **Real-time** company news specifically (not general news)
- ✅ **1 year historical** perfect for trend analysis
- ✅ Strong coverage of **US tech/finance companies** (your target)
- ✅ Company ID normalization (ticker-based, no fuzzy matching needed)
- ✅ Structured data: sentiment, sentiment score, category
- ✅ High reliability (enterprise customers)
- ✅ Generous free tier (60 req/min)

#### Weaknesses
- ❌ **North America only** (no international coverage)
- ❌ Requires company ticker symbol lookup
- ❌ ~100-150 sources (narrower than GNews)
- ❌ Limited historical depth (1 year vs 5 years)
- ❌ API endpoints can be slow (200-500ms)

#### Query Examples
```bash
# Get news for a company ticker
GET https://finnhub.io/api/v1/company-news?symbol=AAPL&from=2025-11-01&to=2025-12-06&token=YOUR_KEY

# Response includes:
{
  "id": 12345,
  "datetime": 1701907200,  # Unix timestamp
  "headline": "Apple Reports Strong Q4 iPhone Sales",
  "image": "https://...",
  "source": "CNBC",
  "summary": "Apple's latest earnings...",
  "url": "https://..."
}
```

#### SDK Integration
```python
import finnhub

client = finnhub.Client(api_key='YOUR_KEY')

# Get news for Apple
news = client.company_news('AAPL', _from='2025-11-01', to='2025-12-06')

for item in news:
    print({
        'headline': item['headline'],
        'summary': item['summary'],
        'source': item['source'],
        'datetime': item['datetime'],
        'url': item['url']
    })

# Also available: earnings calendar, insider transactions, company profile
profile = client.company_profile2(symbol='AAPL')
print(profile['name'])  # 'Apple Inc.'
```

#### Best For
✅ **US tech company focus** (NASDAQ, NYSE)  
✅ Real-time monitoring  
✅ Ticker-based correlation (easy to match to your data)  
✅ High data quality  
✅ Company metadata enrichment  

#### Not Ideal For
❌ International coverage  
❌ Broad news aggregation (too specialized)  
❌ Companies outside finance/tech  

#### Recommendation
**USE ALONGSIDE GNEWS** (Week 1-4). For every company in your tracking list, if it has a US ticker, use Finnhub as primary source. Fall back to GNews for non-US or private companies.

---

### 3. layoffs.fyi ⭐ SPECIALIZED (FREE, NO API... YET)
**Website**: https://layoffs.fyi  
**Status**: Live tracker, community-curated

#### Access Method
```
Current: Manual tracking + web scraping
├─ No official API yet
├─ But data is public HTML
├─ Can build simple scraper (BeautifulSoup)
└─ Or wait for API release (in development)

Future: API coming (sign up for waitlist)
```

#### Strengths
- ✅ **Highest accuracy on layoffs** (verified announcements only)
- ✅ Tracks actual headcount impact (not rumors)
- ✅ Categorized: who laid off, when, how many
- ✅ Covers ALL sectors (tech + non-tech)
- ✅ Live tracker (updated daily)
- ✅ WARN filings integrated (legal requirement in US)

#### Weaknesses
- ❌ **No API** (only web scraping for now)
- ❌ Layoffs-only (misses positive news)
- ❌ Maintenance burden (own scraper or wait for API)
- ❌ Community-curated (occasional delays in updates)

#### Integration Example (Web Scraper)
```python
import requests
from bs4 import BeautifulSoup
import pandas as pd

url = 'https://layoffs.fyi/'
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

# Parse table (structure may change - test regularly)
table = soup.find('table', {'class': 'layoffs-table'})
rows = table.find_all('tr')[1:]  # Skip header

layoffs = []
for row in rows:
    cols = row.find_all('td')
    if len(cols) >= 4:
        layoffs.append({
            'company': cols[0].text.strip(),
            'date': cols[1].text.strip(),
            'headcount': cols[2].text.strip(),
            'percentage': cols[3].text.strip(),
            'industry': cols[4].text.strip() if len(cols) > 4 else None
        })

df = pd.DataFrame(layoffs)
print(df.head())
```

#### Best For
✅ **Layoff-specific signals** (your use case!)  
✅ Verified, high-confidence data  
✅ Headcount impact quantification  
✅ Historical analysis  

#### Not Ideal For
❌ Funding, features, partnerships (layoffs-only)  
❌ If you need API reliability (scraping fragile)  

#### Recommendation
**BUILD LIGHT SCRAPER** (Week 3-4). Run 2x/day. Store results with high confidence. Or wait for official API (expected Q1 2025). **Critical for your correlation use case** — layoff data is most directly linked to hiring changes.

---

## Tier 2: Secondary Free Sources (If You Need Broader Coverage)

### 4. NewsData.io
**Website**: https://newsdata.io  
**Status**: Active

#### Pricing
```
Free Tier:
├─ 200 requests/day
├─ 7+ years historical archive
├─ 85,820 sources (broadest)
├─ Multi-language support
└─ JSON + CSV export

Paid: $29/month+
```

#### Pros & Cons
| Pro | Con |
|-----|-----|
| ✅ **Broadest source coverage** | ❌ No full article body |
| ✅ 7+ years history (great for backfill) | ❌ Slower API response |
| ✅ Free tier is generous (200 req/day) | ❌ Basic filtering only |
| ✅ Multi-language | ❌ No sentiment/NER |

#### Query Example
```python
import requests

url = "https://newsdata.io/api/1/news"
params = {
    'q': 'Tesla layoff',
    'apikey': 'YOUR_KEY',
    'language': 'en',
    'sortby': 'publishedAt'
}

response = requests.get(url, params=params).json()
for article in response['results']:
    print({
        'title': article['title'],
        'description': article['description'],
        'source_id': article['source_id'],
        'pubDate': article['pubDate'],
        'link': article['link']
    })
```

#### Best For
✅ Historical backfill (7 years!)  
✅ Broad source diversity  
✅ Secondary data validation  

#### Not Ideal For
❌ Real-time monitoring (slower)  
❌ Full-text analysis  

#### Recommendation
**USE FOR PHASE 2** (Week 5+). Historical backfill of 2-3 years for trend analysis. Not priority for MVP.

---

### 5. The News API
**Website**: https://thenewsapi.com  
**Status**: Active

#### Pricing
```
Free Tier: 100% free
├─ 200 requests/month (6-7/day)
├─ 40,000+ global sources
├─ Real-time + historical
└─ No rate limiting beyond quota
```

#### Pros & Cons
| Pro | Con |
|-----|-----|
| ✅ **Completely free** (no credit card) | ❌ Lowest rate limit (200/month) |
| ✅ Real-time updates | ❌ Small request quota |
| ✅ Good source coverage | ❌ Basic features |

#### Recommendation
**SKIP FOR MVP** (too rate-limited). Only use if GNews + Finnhub hit limits.

---

## Tier 3: Specialized / Paid Options (Consider Post-MVP)

### 6. Intellizence API (Layoff-Specific)
**Website**: https://intellizence.com  
**Status**: Active, commercial

#### Strengths
- ✅ **Specializes in layoff + hiring announcements**
- ✅ Automated monitoring of WARN filings (legal layoff notices)
- ✅ Structured data: company, date, count, affected departments
- ✅ High accuracy

#### Weaknesses
- ❌ Paid only ($$$)
- ❌ Overkill for MVP

#### Recommendation
**SKIP FOR MVP** (budget constraint). Revisit after proving concept with free sources.

---

### 7. NewsAPI.ai
**Website**: https://newsapi.ai  
**Status**: Premium/Enterprise

#### Strengths
- ✅ **Full article body included** (unlike GNews/Finnhub)
- ✅ NLP enrichment: sentiment, entities, topics
- ✅ Advanced filtering & Boolean queries
- ✅ Multi-language

#### Weaknesses
- ❌ Paid tier ($99+/month)
- ❌ Overkill for MVP phase

#### Recommendation
**CONSIDER FOR PHASE 3** (if you need full-text NLP analysis). For MVP, process GNews snippets with local NLP.

---

### 8. Webz.io, Perigon, etc.
**Status**: Premium APIs

#### Recommendation
**SKIP FOR NOW** (budget). Reassess at scale.

---

## Recommended Integration Strategy for REATS MVP

### **Phase 1 (Weeks 1-2): Foundation**

**Primary Sources**:
1. **GNews API** (100 requests/day, $0)
   - Query: `"[company_name]" (funding OR layoff OR launch OR expansion)`
   - Run 2x/day (morning, evening)
   - Cover 50-70 companies with ~1-2 queries/day each

2. **Finnhub Company News** (60 req/min, $0)
   - For every tracked company with US ticker
   - Pull news daily
   - Falls back to GNews for private companies

3. **layoffs.fyi Scraper** (lightweight, $0)
   - 2x/day runs
   - High confidence layoff alerts

**Expected Coverage**:
- ~100-200 articles/day
- ~85% of your target companies covered
- ~2-3 hour latency from publication

### **Phase 2 (Weeks 3-4): Optimization**

**Add**:
- NewsData.io for historical backfill (1-2 years)
- Caching layer to reuse queries
- Company name → query keyword mapping
- Duplicate detection across sources

### **Phase 3+ (Weeks 5+): Scale**

**Consider**:
- If budget available: NewsAPI.ai for full-text analysis
- Intellizence if layoff tracking becomes critical
- Custom RSS feed scraping for company blogs/press releases
- Your own web scraper for specific company career pages

---

## Cost Breakdown (12-Month Projection)

| Source | Setup | Year 1 | Notes |
|--------|-------|--------|-------|
| **GNews (Free)** | $0 | $0 | 100 req/day free forever |
| **Finnhub (Free)** | $0 | $0 | 60 req/min free forever |
| **layoffs.fyi (Scraper)** | 2 hrs dev | $0 | Maintenance risk, no API cost |
| **NewsData.io (Free)** | $0 | $0 | 200 req/day free |
| **The News API** | $0 | $0 | 200 req/month free (limited) |
| **TOTAL MVP COST** | **2 hrs** | **$0** | ✅ Zero budget |
| | | | |
| **NewsAPI.ai (if needed Phase 3)** | $0 | $1,188 | $99/month, full-text |
| **Intellizence (if needed)** | $0 | $2,000+ | Layoff specialization |
| **TOTAL WITH PAID** | **2 hrs** | **$3,188+** | Only if you scale significantly |

---

## Recommended Phased API Strategy

```
Week 1-2: MVP Minimum
├─ GNews API
├─ Finnhub Company News
├─ layoffs.fyi (scraper)
└─ Cost: $0, Coverage: 80%, Latency: 2-3 hrs

Week 3-4: Enhance Coverage
├─ Add NewsData.io (historical)
├─ Implement caching/dedup
└─ Cost: $0, Coverage: 90%, Latency: <2 hrs

Week 5+: Optimize & Scale
├─ Evaluate NewsAPI.ai if NLP-heavy
├─ Build company-specific scrapers
├─ Integrate WARN filings (free public data)
└─ Cost: $0-1200/mo, Coverage: 95%+, Latency: <1 hr
```

---

## Implementation Checklist

- [ ] Sign up for GNews API (instant, free)
- [ ] Sign up for Finnhub (instant, free)
- [ ] Build layoffs.fyi scraper (lightweight)
- [ ] Test queries on 10-20 pilot companies
- [ ] Measure coverage % per company
- [ ] Set up rate limit monitoring
- [ ] Build deduplication logic
- [ ] Integrate into existing pipeline
- [ ] Test error handling (API downtime)
- [ ] Document API credentials (rotate keys monthly)
- [ ] Monitor for API changes (test endpoints weekly)

---

## FAQ

**Q: Do I need a paid API?**  
A: No, not for MVP. Free APIs cover 80-90% of use cases. Revisit at scale.

**Q: Which API is fastest?**  
A: Finnhub (~50ms), then GNews (~200-500ms), then NewsData (~1-2s).

**Q: Which API has the most sources?**  
A: NewsData (85K+), then NewsAPI.org (150K+), then GNews (60K+).

**Q: What's the best for company-specific news?**  
A: Finnhub (if US ticker exists), else GNews + keyword search.

**Q: How do I handle rate limits?**  
A: Queue system with exponential backoff. Cache results for 12-24 hours.

**Q: Do I need NLP from the API?**  
A: No, use local libraries: spaCy (NER), TextBlob/VADER (sentiment), transformers (advanced).

**Q: How often should I fetch news?**  
A: 2x daily (morning, evening) is enough. Max 3x for critical monitoring.

**Q: What if an API goes down?**  
A: Implement fallback to secondary source + alert. Always have 2-3 sources for critical companies.

---

## Conclusion

**Start with GNews + Finnhub + layoffs.fyi scraper.**  
**$0 investment, 2-4 hours dev, covers 80%+ of your needs.**  
**Revisit paid APIs only after you validate the correlation insights are valuable.**
