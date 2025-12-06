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
    # categories -> location (string)
    loc_str = job.get("categories", {}).get("location")
    if not loc_str:
        loc_str = job.get("country")
        
    location_obj = parse_location(loc_str)
    
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
        "locations": [location_obj],
        "location_display": loc_str,
        "posted_at": posted_at,
        "first_seen_at": datetime.datetime.utcnow().isoformat() + "Z",
        "last_seen_at": datetime.datetime.utcnow().isoformat() + "Z",
        "status": "open"
    }
