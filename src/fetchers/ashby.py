import requests
import datetime
from src.utils import parse_location, parse_posted_at

def fetch_jobs(company_slug):
    """
    Fetches jobs from Ashby using the public API endpoint.
    """
    url = f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        raw_jobs = data.get('jobs', [])
        return raw_jobs
    except requests.RequestException as e:
        print(f"Error fetching Ashby jobs for {company_slug}: {e}")
        return []

def normalize_job(job):
    """
    Normalizes an Ashby job.
    """
    # Location handling
    # Ashby: address -> {postalAddress: {addressLocality: ..., addressRegion: ..., addressCountry: ...}}
    # Or location (string) sometimes?
    # Usually it has 'location' string or 'address' object.
    # We normalized earlier to just 'location' string in old code. 
    # Let's check typical response. Often has 'location' key directly.
    loc_str = job.get("location")
    secondary = job.get("secondaryLocations", [])
    
    all_locs = []
    if loc_str:
        all_locs.append(loc_str)
        
    for sec in secondary:
        # secondaryLocations is usually a list of objects with 'location'
        s_loc = sec.get("location")
        if s_loc and s_loc not in all_locs:
            all_locs.append(s_loc)
            
    parsed_locations = [parse_location(l) for l in all_locs]
    # If no locations, at least store the raw string if we failed to parse anything useful?
    # No, existing logic just passes empty list if empty.
    
    location_obj = parsed_locations[0] if parsed_locations else parse_location(None)
    # But we want to return the LIST of parsed locations.
    # The previous code returned "locations": [location_obj]
    # We will return "locations": parsed_locations
    
    # Date
    # publishedAt or createdAt
    posted_at_raw = job.get("publishedAt") or job.get("createdAt")
    posted_at = parse_posted_at(posted_at_raw)

    return {
        "source_ats": "ashby",
        "company_slug": "",
        "job_key": str(job.get("id")),
        "req_id": str(job.get("id")),
        "title": job.get("title"),
        "url": job.get("jobUrl"),
        "locations": parsed_locations,
        "location_display": loc_str,
        "posted_at": posted_at,
        "first_seen_at": datetime.datetime.utcnow().isoformat() + "Z",
        "last_seen_at": datetime.datetime.utcnow().isoformat() + "Z",
        "status": "open"
    }
