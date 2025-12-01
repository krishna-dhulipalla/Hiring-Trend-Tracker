import requests
import json
import re
from src.config import TARGET_TITLES, EXCLUDE_TITLES

def fetch_greenhouse_jobs(company_slug):
    """
    Fetches jobs from the Greenhouse Boards API for a given company.
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get('jobs', [])
    except requests.RequestException as e:
        print(f"Error fetching jobs for {company_slug}: {e}")
        return []

def normalize_job(company_slug, job):
    """
    Extracts relevant fields from a Greenhouse job object.
    """
    return {
        "company_slug": company_slug,
        "req_id": str(job.get("id")),
        "title": job.get("title"),
        "location": job.get("location", {}).get("name"),
        "url": job.get("absolute_url")
    }

def parse_location(location_name):
    """
    Parses a location string into a dictionary with country, state, city, remote status.
    Conservative rules:
    - Detects 'Remote' variants.
    - Detects 'United States', 'USA', 'US'.
    - Detects state abbreviations (CA, NY, TX, etc.).
    """
    if not location_name:
        return {"raw": None, "is_remote": False, "is_us": False}

    loc_lower = location_name.lower()
    
    # Remote detection
    is_remote = "remote" in loc_lower
    
    # US detection
    is_us = False
    if any(x in loc_lower for x in ["united states", "usa", "us"]) or \
       re.search(r'\b(us)\b', loc_lower):
        is_us = True
    
    # State detection (abbreviations and full names)
    us_states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", 
                 "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", 
                 "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", 
                 "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", 
                 "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
                 "DC"]
                 
    full_state_names = [
        "alabama", "alaska", "arizona", "arkansas", "california", "colorado", 
        "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho", 
        "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", 
        "maine", "maryland", "massachusetts", "michigan", "minnesota", 
        "mississippi", "missouri", "montana", "nebraska", "nevada", 
        "new hampshire", "new jersey", "new mexico", "new york", 
        "north carolina", "north dakota", "ohio", "oklahoma", "oregon", 
        "pennsylvania", "rhode island", "south carolina", "south dakota", 
        "tennessee", "texas", "utah", "vermont", "virginia", "washington", 
        "west virginia", "wisconsin", "wyoming", "district of columbia"
    ]
    
    found_state = None
    for state in us_states:
        # Check for ", CA" or " CA " or start/end of string
        if re.search(r'\b' + state + r'\b', location_name):
            found_state = state
            is_us = True
            break
            
    if not is_us:
        for state in full_state_names:
            if state in loc_lower:
                is_us = True
                break
            
    return {
        "raw": location_name,
        "is_remote": is_remote,
        "is_us": is_us,
        "state": found_state
    }

def title_matches(title):
    """
    Returns True if title matches TARGET_TITLES and does NOT match EXCLUDE_TITLES.
    Uses word boundaries for robust matching.
    """
    if not title:
        return False
        
    title_lower = title.lower()
    
    # Check exclusions first
    for exclude in EXCLUDE_TITLES:
        # \b pattern \b
        if re.search(r'\b' + re.escape(exclude) + r'\b', title_lower):
            return False
            
    # Check inclusions
    for target in TARGET_TITLES:
        if re.search(r'\b' + re.escape(target) + r'\b', title_lower):
            return True
            
    return False

def main():
    # Hardcoded list of companies using Greenhouse
    companies = ["figma", "gusto"]

    print(f"{'COMPANY':<15} | {'REQ_ID':<10} | {'TITLE':<50} | {'LOCATION':<30} | {'URL'}")
    print("-" * 160)

    seen_ids = set()

    for company in companies:
        jobs = fetch_greenhouse_jobs(company)
        for job in jobs:
            normalized = normalize_job(company, job)
            
            # Filter by title
            if not title_matches(normalized['title']):
                continue
                
            # Parse location
            loc_data = parse_location(normalized['location'])
            
            # Filter by location (US only)
            if not loc_data['is_us']:
                continue
            
            # Deduplication
            job_unique_id = f"{company}_{normalized['req_id']}"
            if job_unique_id in seen_ids:
                continue
            seen_ids.add(job_unique_id)

            try:
                print(f"{normalized['company_slug']:<15} | {normalized['req_id']:<10} | {normalized['title'][:50]:<50} | {normalized['location'][:30]:<30} | {normalized['url']}")
            except Exception:
                pass

if __name__ == "__main__":
    main()
