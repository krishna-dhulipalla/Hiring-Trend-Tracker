import requests
import datetime
from src.utils import parse_location, parse_posted_at

def fetch_jobs(company_slug):
    """
    Fetches jobs from the Lever API for a given company.
    """
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        raw_jobs = response.json()
        return raw_jobs
    except requests.RequestException as e:
        print(f"Error fetching Lever jobs for {company_slug}: {e}")
        return []

def normalize_job(job):
    """
    Normalizes a Lever job to the unified schema.
    """
    # Location handling
    # Categories -> location
    # Sometimes Lever jobs have 'workplaceType' (remote/onsite)
    
    loc_str = job.get("categories", {}).get("location")
    country = job.get("country")
    
    all_loc_strings = []
    if loc_str:
        all_loc_strings.append(loc_str)
    if country and country != loc_str:
        all_loc_strings.append(country)
        
    parsed_locations = [parse_location(l) for l in all_loc_strings]
    
    if str(job.get("workplaceType")).lower() == "remote":
        if not any(pl["is_remote"] for pl in parsed_locations):
            parsed_locations.append(parse_location("Remote"))
    
    # Date handling
    # createdAt is ms timestamp
    created_at_ms = job.get("createdAt")
    if created_at_ms:
        # Convert ms to ISO
        dt = datetime.datetime.utcfromtimestamp(created_at_ms / 1000.0)
        posted_at = dt.isoformat() + "Z"
    else:
        posted_at = None
        
    return {
        "source_ats": "lever",
        "company_slug": "", 
        "job_key": str(job.get("id")),
        "req_id": str(job.get("id")),
        "title": job.get("text"), # Lever uses 'text' for title
        "url": job.get("hostedUrl"),
        "locations": parsed_locations,
        "location_display": loc_str,
        "posted_at": posted_at,
        "first_seen_at": datetime.datetime.utcnow().isoformat() + "Z",
        "last_seen_at": datetime.datetime.utcnow().isoformat() + "Z",
        "status": "open"
    }
