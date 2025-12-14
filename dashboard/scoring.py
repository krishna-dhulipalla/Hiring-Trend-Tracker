import datetime

# -----------------------------------------------------------------------------
# 2. Core concept: "My Fit" profile
# -----------------------------------------------------------------------------

USER_PROFILE = {
    "target_keywords": [
        "machine learning", "ml engineer", "ai engineer", "artificial intelligence",
        "deep learning", "nlp", "computer vision", "llm", "large language model",
        "generative ai", "rag", "retrieval augmented", "agentic", "agents",
        "platform", "infrastructure", "inclusive", "distributed systems", "backend",
        "software engineer", "data engineer"
    ],
    "avoid_keywords": [
        "manager", "director", "vp", "head of", "chief", "sales", "marketing", 
        "account", "executive", "recruiter", "hr", "legal", "finance", "principal", "staff"
    ],
    "seniority_preference": {
        # Preference: Mid/Junior > Senior > Staff
        "Mid": 10,
        "Junior": 10,
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

def calculate_company_opportunity_score(stats, news_counts, open_now_count=0):
    """
    Calculates a Company Opportunity Score (0-100) based on hiring momentum, news, and OPEN JOBS.
    
    Args:
        stats (dict): { "added_total", "net_change", "senior_plus_added_count" }
        news_counts (dict): { "funding", "ai_announcement", ... }
        open_now_count (int): Current filtered open jobs.
        
    Returns:
        dict: { "score": int, "label": str, "reason": str, "breakdown": list }
    """
    raw_score = 0
    breakdown = []
    
    # 1. Base: Open Jobs (Actionability)
    # 2 pts per open job, cap at 40pts
    open_pts = min(open_now_count * 2, 40)
    if open_pts > 0:
        raw_score += open_pts
        breakdown.append(f"Open Jobs ({open_now_count}): +{open_pts}")
    else:
        # If 0 open jobs, hard to be an opportunity
        breakdown.append("No open filtered jobs")
        
    # 2. Hiring Momentum (Last N days)
    added = stats.get("added_total", 0)
    senior = stats.get("senior_plus_added_count", 0)
    mid_unspecified = max(0, added - senior)
    
    # Mid-level hiring bonus
    mom_pts = (mid_unspecified * 1.5)
    if mom_pts > 0:
        breakdown.append(f"Recent Mid/Jr Adds: +{mom_pts:.0f}")
        raw_score += mom_pts
        
    # Senior Penalty in score (user prefers junior/mid)
    if senior > 0:
        # Slightly penalize if ratio is high? Or just don't reward.
        # Let's simple ignore reward.
        pass
        
    # 3. News Signal
    funding = news_counts.get("funding", 0)
    ai = news_counts.get("ai_announcement", 0)
    layoff = news_counts.get("layoff", 0)
    
    if funding > 0:
        raw_score += 20
        breakdown.append("Funding News: +20")
    if ai > 0:
        raw_score += 15
        breakdown.append("AI News: +15")
    if layoff > 0:
        raw_score -= 30
        breakdown.append("Layoffs: -30")
        
    # Normalize 0-100 (soft cap)
    final_score = max(0, min(100, int(raw_score)))
    
    # Labeling
    if final_score >= 60:
        label = "🔥 Hot"
    elif final_score >= 40:
        label = "🙂 Warming"
    elif final_score >= 20:
        label = "😐 Flat"
    else:
        label = "🧊 Cooling"
        
    return {
        "score": final_score,
        "label": label,
        "reason": breakdown[0] if breakdown else "Quiet",
        "breakdown": breakdown
    }

def calculate_role_match_score(job, days_ago_added=0):
    """
    Calculates a Role Match Score based on keywords, seniority, and location.
    Same inputs, just ensuring clean output.
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
            # reasons.append(f"Avoid: {kw}") 
            
    # 2. Seniority
    seniority = job.get("seniority", "Mid") 
    pref = USER_PROFILE["seniority_preference"].get(seniority, 0)
    score += pref
    if pref > 0: reasons.append(seniority)
    
    # 3. Location
    # We check the serialized location strings via loc_str
    # Assuming caller passes clean data or we check dict
    # Simple check:
    locs = job.get("locations", [])
    loc_text = str(locs).lower()
    
    for loc_pref in USER_PROFILE["location_preference"]:
        if loc_pref in loc_text:
            score += 5
            # reasons.append("Location Match")
            break
            
    if job.get("is_us_remote"):
        score += 3
        # reasons.append("Remote")
        
    # 4. Recency (Decay)
    if days_ago_added <= 2:
        score += 5
    elif days_ago_added > 14:
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
        "match_reasons": list(set(reasons)) 
    }

def classify_company_momentum(stats, open_now_count=0):
    """
    Simple momentum classifier for Company Detail page.
    """
    added = stats.get("added_total", 0)
    net = stats.get("net_change", 0)
    
    if open_now_count > 10 and net >= 0:
        return "🔥 Hot"
    if open_now_count > 0 and added > 0:
        return "🙂 Warming"
    if net < 0 and open_now_count < 5:
        return "🧊 Cooling"
    if open_now_count > 0:
        return "😐 Flat" # Has jobs but no motion
        
    return "🧊 Ice Cold"
