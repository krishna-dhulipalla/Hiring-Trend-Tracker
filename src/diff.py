import json
import os
import glob
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Tuple

# We'll use the user's definitions for disciplines and seniority mapping
# Discipline keywords (simple heuristic base)
DISCIPLINES = {
    "ML": ["machine learning", " ml", "ai ", "artificial intelligence", "deep learning", "nlp", "computer vision", "llm"],
    "Data": ["data scientist", "data engineer", "data analyst", "analytics", "bi engineer"],
    "Platform": ["platform", "infrastructure", "devops", "sre", "reliability", "cloud"],
    "Infra": ["infrastructure", "systems", "distributed systems", "embedded"],
    # Fallback to "Other"
}

SENIORITY_LEVELS = [
    ("Intern", ["intern", "university", "grad", "student"]),
    ("Junior", ["junior", "entry", "associate", " jr"]),
    ("Staff+", ["staff", "principal", "distinguished", "fellow", "architect", "director", "vp", "head of", "lead"]),
    ("Senior", ["senior", " sr", "lead"]), # Check Senior after Staff+ to avoid "Senior Staff" colliding purely on Senior
    ("Mid", []), # Fallback
]

def _parse_seniority(title: str) -> str:
    title_lower = title.lower()
    for level, keywords in SENIORITY_LEVELS:
        for kw in keywords:
            if kw in title_lower:
                return level
    # If no match but not explicit mid, default to specific logic or just Mid?
    # User said: Intern / Junior / Mid / Senior / Staff+
    # If it doesn't match others, it's likely Mid (or just standard Engineer)
    return "Mid"

def _parse_discipline(title: str) -> str:
    title_lower = title.lower()
    for disc, keywords in DISCIPLINES.items():
        for kw in keywords:
            if kw in title_lower:
                return disc
    return "Other"

def _get_is_us_remote(job: Dict[str, Any]) -> bool:
    """
    Derived: remote & not clearly non-US.
    Suggestion: allow US-remote when any location is_remote and no location raw indicates non-US region.
    """
    locations = job.get("locations", [])
    if not locations:
        return False
        
    has_remote = False
    has_non_us = False
    
    for loc in locations:
        if isinstance(loc, dict):
            if loc.get("is_remote"):
                has_remote = True
            # Check if explicitly non-US (if is_us is explicit False, or country_code is not US)
            # Assuming 'is_us' flag is the source of truth for US-ness.
            # If is_us is False, does it mean non-US? 
            # Usually yes, but let's confirm usage. 
            # If we rely on is_us flag:
            if loc.get("is_us") is False: 
                # Careful: if it's missing it might be None/False.
                # If we have a country code and it's not US, it's non-US.
                cc = loc.get("country_code") or loc.get("country")
                if cc and str(cc).upper() not in ["US", "USA", "UNITED STATES"]:
                    has_non_us = True

    return has_remote and not has_non_us

def _get_is_us(job: Dict[str, Any]) -> bool:
    """True if any location is_us"""
    locations = job.get("locations", [])
    for loc in locations:
        if isinstance(loc, dict) and loc.get("is_us"):
            return True
    return False

def _create_job_card(job: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a raw/normalized job into the analytic 'Card' shape."""
    title = job.get("title", "Unknown")
    posted_at = job.get("posted_at")
    
    # Fix: read canonical key (job_key > id)
    # If not present, fallback to URL (brittle but allowed fallback)
    job_key = job.get("job_key") or job.get("id") or job.get("url")
    
    card = {
        "job_key": job_key,
        "req_id": job.get("req_id"), 
        "title": title,
        "url": job.get("url"),
        "locations": job.get("locations", []),
        "is_us": _get_is_us(job),
        "is_us_remote": _get_is_us_remote(job),
        "seniority": _parse_seniority(title),
        "discipline": _parse_discipline(title),
        "posted_at": posted_at,
        "first_seen_at": job.get("first_seen_at", posted_at),
        "last_seen_at": job.get("last_seen_at"), 
        "status": job.get("status", "open"),
    }
    
    # location_display fallback
    if "location_display" in job:
        card["location_display"] = job["location_display"]
    else:
        # Construct simple display using country_code
        loc_strs = []
        for l in card["locations"]:
            if isinstance(l, dict):
                parts = [p for p in [l.get("city"), l.get("state"), l.get("country_code")] if p]
                loc_strs.append(", ".join(parts))
        card["location_display"] = " | ".join(loc_strs)

    return card

def _normalize_title(t: str) -> str:
    return " ".join(t.lower().split())

def _compare_locations(locs1: List[Any], locs2: List[Any]) -> bool:
    """Return True if locations fit different semantic set."""
    
    def _loc_sig(l):
        # Create a signature for the location
        # Fix: use country_code
        if isinstance(l, str): return l.strip().lower()
        if isinstance(l, dict):
             return (
                 l.get("city", "").strip().lower(),
                 l.get("state", "").strip().lower(),
                 l.get("country_code", "").strip().lower(),
                 l.get("is_remote", False),
                 l.get("is_us", False)
             )
        return str(l)
        
    s1 = set(_loc_sig(l) for l in locs1)
    s2 = set(_loc_sig(l) for l in locs2)
    return s1 != s2

def _detect_changes(prev: Dict[str, Any], curr: Dict[str, Any]) -> Optional[Dict[str, Dict[str, Any]]]:
    """
    Compare two cards (from prev and curr) and return changes dict if meaningful change detected.
    Returns None if no meaningful changes.
    """
    changes = {}
    
    # 1. Title
    if _normalize_title(prev["title"]) != _normalize_title(curr["title"]):
        changes["title"] = {"before": prev["title"], "after": curr["title"]}
        
    # 2. Locations
    if _compare_locations(prev["locations"], curr["locations"]):
        changes["locations"] = {"before": prev["locations"], "after": curr["locations"]}
        
    # 3. is_us_remote / is_us
    if prev["is_us_remote"] != curr["is_us_remote"]:
        changes["is_us_remote"] = {"before": prev["is_us_remote"], "after": curr["is_us_remote"]}
        
    # 4. Status
    if prev["status"] != curr["status"]:
        changes["status"] = {"before": prev["status"], "after": curr["status"]}
        
    # 5. posted_at
    # Only treat posted_at as changed if: previous.posted_at is null and current.posted_at is non-null.
    p_date = prev.get("posted_at")
    c_date = curr.get("posted_at")
    
    if p_date is None and c_date is not None:
        changes["posted_at"] = {"before": None, "after": c_date}
        
    if not changes:
        return None
        
    return changes

def get_previous_snapshot_path(snapshot_dir: str, current_ts: str) -> Optional[str]:
    """Find the most recent snapshot in snapshot_dir before current_ts."""
    # Pattern: {timestamp}.json (standard ISO format or similar)
    pattern = os.path.join(snapshot_dir, "*.json")
    files = glob.glob(pattern)
    
    valid_files = []
    for f in files:
        fname = os.path.basename(f)
        # Assuming filename IS the timestamp.json
        ts_str = fname.replace(".json", "")
        
        # Skip if it is the current one (if it exists)
        if ts_str == current_ts:
            continue
            
        try:
            if ts_str < current_ts:
                valid_files.append((ts_str, f))
        except:
            continue
            
    if not valid_files:
        return None
        
    # Sort by TS descending
    valid_files.sort(key=lambda x: x[0], reverse=True)
    return valid_files[0][1]

def generate_diff(company_slug: str, current_ts: str, current_snapshot_data: List[Dict], snapshot_dir: str, diff_dir: str):
    """
    Main entry point to generate differences.
    """
    card_map_curr = {}
    for job in current_snapshot_data:
        card = _create_job_card(job)
        key = card["job_key"]
        if key:
            card_map_curr[key] = card

    # Find previous
    prev_path = get_previous_snapshot_path(snapshot_dir, current_ts)
    card_map_prev = {}
    prev_ts = None
    
    if prev_path and os.path.exists(prev_path):
        try:
            with open(prev_path, 'r', encoding='utf-8') as f:
                prev_data = json.load(f)
                # prev_data should be a list of jobs
                for job in prev_data:
                    card = _create_job_card(job)
                    key = card["job_key"]
                    if key:
                        card_map_prev[key] = card
            
            # Extract ts from filename
            fname = os.path.basename(prev_path)
            prev_ts = fname.replace(".json", "")
        except Exception as e:
            print(f"Error loading previous snapshot {prev_path}: {e}")

    # Compute Diff
    curr_keys = set(card_map_curr.keys())
    prev_keys = set(card_map_prev.keys())
    
    added_keys = curr_keys - prev_keys
    removed_keys = prev_keys - curr_keys
    common_keys = curr_keys & prev_keys
    
    added_cards = [card_map_curr[k] for k in added_keys]
    removed_cards = [card_map_prev[k] for k in removed_keys]
    
    changed_cards = []
    
    for k in common_keys:
        prev_card = card_map_prev[k]
        curr_card = card_map_curr[k]
        
        changes = _detect_changes(prev_card, curr_card)
        if changes:
            c_copy = curr_card.copy()
            c_copy["changes"] = changes
            changed_cards.append(c_copy)
            
    # Analytics
    summary = {
        "added": len(added_cards),
        "removed": len(removed_cards),
        "changed": len(changed_cards),
        "us_added": sum(1 for c in added_cards if c["is_us"]),
        "us_remote_added": sum(1 for c in added_cards if c["is_us_remote"]),
        "senior_plus_added": sum(1 for c in added_cards if c["seniority"] in ["Senior", "Staff+"]),
    }
    
    diff_output = {
        "company_slug": company_slug,
        "current_snapshot_ts": current_ts,
        "previous_snapshot_ts": prev_ts,
        "summary": summary,
        "added": added_cards,
        "removed": removed_cards,
        "changed": changed_cards
    }
    
    # Save
    os.makedirs(diff_dir, exist_ok=True)
    diff_filename = f"jobs_diff_{company_slug}_{current_ts}.json"
    diff_path = os.path.join(diff_dir, diff_filename)
    
    with open(diff_path, 'w', encoding='utf-8') as f:
        json.dump(diff_output, f, indent=2, ensure_ascii=False)
        
    print(f"Diff saved to {diff_path}")
    return diff_path
