# REATS Company News Feature: Executive Summary

**Project**: REATS (Reverse-Engineered ATS Job Tracker)  
**Feature**: Company News & Hiring Correlation Engine  
**Stage**: MVP Planning  
**Timeline**: 4 weeks to launch, 0 budget to start  
**Owner**: You

---

## What This Feature Solves

Currently, REATS tracks **job posting trends** (velocity, role mix, locations, seniority).

**Gap**: You don't know **why** hiring changes occur.

**Solution**: Automatically ingest company news (funding, layoffs, launches, partnerships, expansions) and correlate with job trends to answer:

- 🟢 **Feature launched** → jobs posted increase? (Expected lag: 3-7 days)
- 🔴 **Layoffs announced** → hiring freeze or reduction? (Immediate)
- 💰 **Series B funding** → team expansion in specific departments?
- 🏢 **Expansion to new market** → new location jobs posted?
- 🤝 **Acquisition** → job merges or role consolidation?

**Result**: From "Tesla posted +47 jobs" to "Tesla posted +47 jobs because they announced AI division expansion."

---

## Investment Summary

| Aspect | Cost | Effort | Timeline |
|--------|------|--------|----------|
| **APIs** | **$0** | Sign up (30 min) | Day 1 |
| **Development** | **$0** | 40-60 hours | Weeks 1-2 |
| **Database** | **Minimal** (~3-4 new tables) | Already have infrastructure | Day 1 |
| **Deployment** | **$0** | Existing CI/CD | Week 3 |
| **TOTAL** | **$0** 🎉 | ~50 hours | 4 weeks |

---

## Recommended Free APIs (No Credit Card)

### Primary: **GNews API** 
- 100 requests/day free (enough for 50-70 companies)
- 60,000+ sources globally
- Real-time + 5 years history
- Website: https://gnews.io

### Secondary: **Finnhub Company News**
- 60 requests/minute free (very generous)
- Best for US tech companies (ticker-based)
- 1 year history
- Website: https://finnhub.io

### Tertiary: **layoffs.fyi** (Scraper)
- Community-curated layoff tracker
- Highest accuracy for layoffs
- Build lightweight scraper (2 hours)
- Website: https://layoffs.fyi

**Total Free Coverage**: ~85-90% of your tracked companies with <2 hour latency.

---

## What You Get

### For REATS Users:
1. **Timeline View** - Company news overlaid on hiring trends
2. **Correlation Insights** - "3 days after Series B, +15 roles posted"
3. **Anomaly Alerts** - "Company laid off but hiring increased (restructuring detected)"
4. **Exportable Reports** - "Here's why Company X is hiring right now"

### For Your Analysis:
1. **Historical Database** - 2-3 years of news + job trends correlated
2. **Predictive Signals** - Learn which news types correlate with hiring patterns
3. **Competitive Intelligence** - Monitor competitor expansion/contraction
4. **Hiring Momentum** - Identify which teams grew in which companies

---

## Technical Architecture (High-Level)

```
Daily Flow (8am & 4pm):
  1. Query GNews API → 50-70 companies → ~100-200 articles
  2. Query Finnhub API → US-ticker companies → supplement with latest
  3. Run layoffs.fyi scraper → capture high-confidence layoffs
  ↓
  4. Store raw articles (dedup by URL hash)
  ↓
  5. Normalize articles:
     - Extract company name (fuzzy match to your companies table)
     - Classify category (funding, layoff, feature, partnership, etc)
     - Analyze sentiment (positive, negative, neutral)
     ↓
  6. Link to job snapshots (existing):
     - Find recent job snapshot for that company
     - Calculate correlation score (news → job change relationship)
     - Annotate snapshot with news context
     ↓
  7. Serve in dashboard:
     - Timeline: news events + job counts
     - Correlation matrix: companies × time × score
     - Export: CSV/JSON of correlated data

Storage: 3 new tables
  - raw_news (as-received from APIs)
  - normalized_news (processed + categorized)
  - news_correlations (linked to job snapshots)
```

---

## MVP Scope (Weeks 1-4)

### ✅ Must Have
- [ ] GNews + Finnhub integration (2 sources)
- [ ] Daily ingestion for 50 tracked companies
- [ ] Company name matching + categorization
- [ ] Normalized news storage
- [ ] Correlation score calculation
- [ ] News timeline on existing dashboard
- [ ] Error handling + monitoring

### 🟡 Nice to Have (Phase 2)
- [ ] Multi-source aggregation (NewsData.io, layoffs.fyi API when available)
- [ ] Advanced sentiment analysis (Hugging Face)
- [ ] Anomaly detection alerts
- [ ] PDF reports with visualizations
- [ ] Historical backfill (1-2 years)

### ❌ Out of Scope (Phase 3+)
- [ ] Custom ML models for correlation prediction
- [ ] Real-time alerts (starts with daily digest)
- [ ] Full-text search across 10+ years history
- [ ] Competitor feature analysis (separate project)

---

## Implementation Timeline

```
Week 1: Foundation
├─ Mon-Tue: API setup + DB schema
├─ Wed-Thu: GNews API integration + basic tests
├─ Fri: Finnhub integration + dedup logic
└─ Mon: First week of real data collection

Week 2: Processing + Storage
├─ Tue-Wed: Normalization engine (company matching, categorization)
├─ Thu: Sentiment analysis + storage
├─ Fri: Error handling + logging + monitoring
└─ Mon: Data quality review (manual spot-check 50 articles)

Week 3: Integration + Analytics
├─ Tue: Correlation calculation (news → job changes)
├─ Wed: Dashboard integration (news timeline view)
├─ Thu: Export functionality (CSV/JSON)
├─ Fri: Load testing + performance optimization
└─ Mon: User testing + refinement

Week 4: Refinement + Launch
├─ Tue-Wed: Bug fixes + edge case handling
├─ Thu: Documentation + runbooks
├─ Fri: Soft launch (internal testing)
└─ Mon: GA (general availability) + monitoring

Total Dev Time: ~40-60 hours (6-8 hours/day, realistic)
```

---

## Success Metrics

**Launch (Week 4)**:
- ✅ News ingestion for 50+ companies, <2h latency
- ✅ 85%+ company name matching accuracy
- ✅ 0 duplicate articles in DB
- ✅ Dashboard shows correlated news + jobs

**Post-Launch (Month 2)**:
- ✅ Users report 3+ "aha moments" per week from correlations
- ✅ Export reports used by 50%+ of users
- ✅ Correlation signal shows R² > 0.5 with job trends
- ✅ <5% false positive correlations (manual spot check)

**Scale (Month 3+)**:
- ✅ Add 2nd source (NewsData.io or layoffs.fyi API)
- ✅ Correlation accuracy reaches 80%+
- ✅ Users rely on feature for hiring predictions

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| API rate limits hit | Medium | Delayed news | Implement caching + queue system |
| Company name fuzzy matching fails | Medium | False correlations | Build manual whitelist for top 20 companies |
| Sentiment analysis inaccurate | Medium | Misleading insights | Use hybrid approach (rule-based + ML) |
| Correlation coincidental (false positive) | High | User mistrust | Flag low confidence, require multiple signals |
| Free APIs discontinued | Low | Backfill from paid | Already have Finnhub + NewsData backup |

**Mitigation Strategy**: Start conservative. Flag all uncertainties. Gather user feedback before scaling.

---

## How to Get Started

### Right Now (Today):
1. **Sign up for APIs** (30 min):
   - GNews: https://gnews.io → "Get Free API Key"
   - Finnhub: https://finnhub.io → Sign up
   
2. **Build company ticker mapping** (2 hours):
   - Create CSV of your 50 tracked companies
   - Add ticker symbols (pull from Yahoo Finance or manually)
   - This is critical for Finnhub integration

3. **Create GitHub project** (15 min):
   - Branch `feature/company-news`
   - Create directory structure
   - Push empty commit

### This Week:
1. **Pick your stack** (Python/Node.js) based on your existing project
2. **Create database schema** (2 hours, SQL)
3. **Implement GNews fetcher** (4 hours)
4. **First data collection run** (1 hour setup, then automated)

### Next Week:
1. **Add Finnhub** (2 hours)
2. **Build normalization** (8 hours)
3. **Correlation logic** (6 hours)
4. **Dashboard integration** (4 hours)

---

## Key Decision: Which API First?

**Start with GNews** because:
- ✅ No ticker lookup needed (company name search)
- ✅ Broader coverage (international + small companies)
- ✅ Easier to test immediately
- ✅ Good free tier (100 req/day)

**Then add Finnhub** because:
- ✅ Supplements GNews for US tech (better sources)
- ✅ Structured sentiment/data
- ✅ Very generous free tier (60 req/min)
- ✅ Reduces false positives

**Later add layoffs.fyi scraper** because:
- ✅ Highest accuracy on layoff data
- ✅ Most directly linked to hiring changes
- ✅ Community-verified (low false positives)

---

## Budget Scenarios

**Scenario A: Stay Free Forever**
- Cost: $0/year
- Coverage: 80-85% (GNews + Finnhub)
- Latency: 2-3 hours
- Effort: 4-6 weeks dev + 2 hours/week maintenance

**Scenario B: Scale to 90%+ Coverage (Month 6+)**
- Add NewsAPI.ai ($99/month) for full-text
- Cost: ~$1,200/year
- Coverage: 95%+
- Latency: <30 min
- Effort: 1 week integration

**Scenario C: Enterprise-Grade (Year 2+)**
- Intellizence ($2,000+/year) for layoff specialization
- NewsAPI.ai for advanced NLP
- Custom scrapers for company press releases
- Cost: $3,000-5,000/year
- Coverage: 99%+
- Latency: Real-time
- Effort: 1 full-time engineer

**Recommendation**: Start with Scenario A, prove value, upgrade to B at scale.

---

## Files Delivered

1. **REATS_News_Feature_PRD.md** - Complete product specification
   - Goals, success metrics, feature specs, data schema, analytics, risks

2. **API_Sources_Comparison.md** - Detailed API analysis
   - Pros/cons of 8+ APIs, pricing, integration examples, recommendations

3. **Implementation_Plan.md** - Step-by-step roadmap
   - Week-by-week tasks, code examples (Python + Node.js), DB schema, deployment checklist

4. **This Summary** - High-level overview for decision-making

---

## Your Next Action

**Pick one:**

A) **Dive In Immediately** (Recommended for MVP)
   - Open all 3 documents
   - Start Week 1 tasks today
   - Have GNews running by Friday
   
B) **Discuss First** (If unsure)
   - Review the PRD
   - Validate architecture with team
   - Refine scope if needed
   - Then proceed with Week 1

C) **Validate Demand First** (If cautious)
   - Survey users: "Would news correlation help you?"
   - Run manual correlation for 5 companies
   - Prove value before building
   - Then proceed with implementation

**Recommendation**: Go with **A**. The investment is low ($0 + 50 hours), the payoff is high (correlation insights), and you learn fast. You can pivot or pause anytime.

---

## Questions to Ask Yourself

- ✅ Do my users care about **why** companies hire?
- ✅ Is the free API approach sufficient to start?
- ✅ Do I have 50 hours over the next 4 weeks?
- ✅ Can I afford 2-3 new tables in my DB?
- ✅ Do I want to own this feature or outsource?

**If all yes → Start Week 1 now.**  
**If any no → Reconsider scope or timeline.**

---

## Support & Resources

**During Implementation:**
- GNews docs: https://docs.gnews.io
- Finnhub docs: https://finnhub.io/docs
- layoffs.fyi data: https://layoffs.fyi (public HTML table)
- spaCy NER: https://spacy.io (free NLP library)
- TextBlob sentiment: https://textblob.readthedocs.io

**If Stuck:**
1. Check API documentation (most issues there)
2. Review code examples in Implementation_Plan.md
3. Test with curl before writing code
4. Start simple: fetch 10 articles, print them, then normalize

---

## Final Thoughts

This feature **transforms REATS** from a "what are they hiring" tool to a "why are they hiring and what does that tell us" tool.

The data is free, the infrastructure is simple, the payoff is substantial.

**Go build it.** 🚀

---

**Last Updated**: December 6, 2025  
**Status**: Ready to Implement  
**Confidence Level**: High (proven APIs, clear architecture, low risk)
