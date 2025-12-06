import requests
import datetime
from src.utils import parse_location, parse_posted_at

def fetch_jobs(company_slug):
    """
    Fetches jobs from the Greenhouse Boards API for a given company.
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        raw_jobs = data.get('jobs', [])
        return raw_jobs
    except requests.RequestException as e:
        print(f"Error fetching Greenhouse jobs for {company_slug}: {e}")
        return []

def normalize_job(job):
    """
    Normalizes a Greenhouse job to the unified schema.
    """
    # Location handling
    # Greenhouse provides 'location': {'name': '...'}
    loc_str = job.get("location", {}).get("name")
    location_obj = parse_location(loc_str)
    
    # Date handling
    # created_at or updated_at
    posted_at_raw = job.get("updated_at") # Greenhouse public board often uses updated_at as the visible date
    # Ideally check both but usually updated_at is finer
    posted_at = parse_posted_at(posted_at_raw)
    
    return {
        "source_ats": "greenhouse",
        "company_slug": "", # Filled by main loop usually, or we can pass it in if needed. Main loop handles file path.
        "job_key": str(job.get("id")),
        "req_id": str(job.get("internal_job_id") or job.get("id")),
        "title": job.get("title"),
        "url": job.get("absolute_url"),
        "locations": [location_obj],
        "location_display": loc_str,
        "posted_at": posted_at,
        "first_seen_at": datetime.datetime.utcnow().isoformat() + "Z", # Current crawl time
        "last_seen_at": datetime.datetime.utcnow().isoformat() + "Z",
        "status": "open"
    }
