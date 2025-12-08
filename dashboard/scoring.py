import datetime

# -----------------------------------------------------------------------------
# 2. Core concept: "My Fit" profile
# -----------------------------------------------------------------------------

USER_PROFILE = {
    "target_keywords": [
        "machine learning", "ml engineer", "ai engineer", "artificial intelligence",
        "deep learning", "nlp", "computer vision", "llm", "large language model",
        "generative ai", "rag", "retrieval augmented", "agentic", "agents",
        "platform", "infrastructure", "inclusive", "distributed systems", "backend"
    ],
    "avoid_keywords": [
        "manager", "director", "vp", "head of", "chief", "sales", "marketing", 
        "account", "executive", "recruiter", "hr", "legal", "finance"
    ],
    "seniority_preference": {
        # Preference: Mid/Junior > Senior > Staff
        "Mid": 10,
        "Junior": 8,
        "Senior": -5,
        "Staff+": -10,  
        "Intern": 0
    },
    "location_preference": [
        "san francisco", "bay area", "palo alto", "mountain view", "sunnyvale",
        "menlo park", "redwood city", "new york", "nyc", "seattle", "austin", "remote"
    ]
}

# -----------------------------------------------------------------------------
# Scoring Logic
# -----------------------------------------------------------------------------

def calculate_company_opportunity_score(stats, news_counts):
    """
    Calculates a Company Opportunity Score (0-100+) based on hiring momentum and news.
    
    Args:
        stats (dict): {
            "added_total": int,
            "net_change": int,
            "senior_plus_added_count": int
        }
        news_counts (dict): {
            "funding": int,
            "product": int,
            "ai_announcement": int,
            "layoff": int,
            "earnings": int
        }
        
    Returns:
        dict: {
            "score": float,
            "label": str (Hot, Warming, Flat, Cooling),
            "reason": str
        }
    """
    score = 0
    reasons = []
    
    # 1. Hiring Momentum
    added = stats.get("added_total", 0)
    net = stats.get("net_change", 0)
    senior = stats.get("senior_plus_added_count", 0)
    mid_unspecified = max(0, added - senior)
    
    # Weight mid-level hiring more
    score += (mid_unspecified * 2) 
    score += (senior * 0.5)
    
    # Net change bonus/penalty
    if net > 0:
        score += (net * 1.5)
    elif net < 0:
        score -= (abs(net) * 2)
        
    if added > 0:
        reasons.append(f"+{added} roles")
        
    # 2. News Signal
    funding = news_counts.get("funding", 0)
    product = news_counts.get("product", 0)
    ai = news_counts.get("ai_announcement", 0)
    layoff = news_counts.get("layoff", 0)
    
    if funding > 0:
        score += (funding * 15)
        reasons.append("Funding news")
        
    if ai > 0:
        score += (ai * 10)
        reasons.append("AI news")
        
    if product > 0:
        score += (product * 5)
        
    if layoff > 0:
        score -= (layoff * 30) # Heavy penalty
        reasons.append("Layoffs")
        
    # 3. Labeling
    if score >= 40:
        label = "🔥 Hot"
    elif score >= 15:
        label = "🙂 Warming"
    elif score >= -5:
        label = "😐 Flat"
    else:
        label = "🧊 Cooling"
        
    return {
        "score": round(score, 1),
        "label": label,
        "reason": ", ".join(reasons) if reasons else "Quiet"
    }

def calculate_role_match_score(job, days_ago_added=0):
    """
    Calculates a Role Match Score based on keywords, seniority, and location.
    
    Args:
        job (dict): Job card data (title, locations, senioroty, discipline)
        days_ago_added (int): How many days ago the job was added (0 = today)
        
    Returns:
        dict: {
            "score": float,
            "label": str (Strong, Good, Okay, Weak),
            "match_reasons": list[str]
        }
    """
    score = 0
    reasons = []
    
    title = job.get("title", "").lower()
    
    # 1. Keywords
    for kw in USER_PROFILE["target_keywords"]:
        if kw in title:
            score += 15
            reasons.append(kw)
            
    for kw in USER_PROFILE["avoid_keywords"]:
        if kw in title:
            score -= 20
            # reasons.append(f"Avoid: {kw}") # Optional: show why avoided
            
    # 2. Seniority
    seniority = job.get("seniority", "Mid") # Default to Mid if unknown, which is good
    pref = USER_PROFILE["seniority_preference"].get(seniority, 0)
    score += pref
    
    # 3. Location
    # Heuristic: Check raw display or city fields
    locations = job.get("locations", [])
    loc_matched = False
    
    # Simple text check against location preferences
    # We check the serialized location strings or dicts
    loc_text = str(locations).lower()
    for loc_pref in USER_PROFILE["location_preference"]:
        if loc_pref in loc_text:
            score += 5
            loc_matched = True
            break
            
    if job.get("is_us_remote") and not loc_matched:
        score += 3 # Remote bonus if not already matched preferred geo
        
    # 4. Recency (Decay)
    # Freshness bonus: +5 for today/yesterday
    if days_ago_added <= 2:
        score += 5
    elif days_ago_added > 7:
        score -= 5
        
    # Labeling
    if score >= 25:
        label = "Strong"
    elif score >= 10:
        label = "Good"
    elif score >= 0:
        label = "Okay"
    else:
        label = "Weak"
        
    return {
        "score": score,
        "label": label,
        "match_reasons": list(set(reasons)) # dedup
    }

def classify_company_momentum(stats, prev_stats=None):
    """
    Simple momentum classifier for Company Detail page.
    """
    added = stats.get("added_total", 0)
    net = stats.get("net_change", 0)
    
    if added > 5 and net > 0:
        return "🔥 Hot"
    if added > 0 and net >= 0:
        return "🙂 Warming"
    if net < 0:
        return "🧊 Cooling"
    return "😐 Flat"
