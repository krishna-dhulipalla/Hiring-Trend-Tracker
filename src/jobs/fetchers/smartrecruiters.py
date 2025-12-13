import requests
import datetime
from src.utils import parse_location, parse_posted_at

def fetch_jobs(company_slug):
    """
    Fetches jobs from SmartRecruiters API.
    """
    url = f"https://api.smartrecruiters.com/v1/companies/{company_slug}/postings"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        raw_jobs = data.get('content', [])
        return raw_jobs
    except requests.RequestException as e:
        print(f"Error fetching SmartRecruiters jobs for {company_slug}: {e}")
        return []

def normalize_job(job):
    """
    Normalizes a SmartRecruiters job.
    """
    # Location
    # 'location': {'city': '...', 'region': '...', 'country': '...', 'remote': ...}
    loc_data = job.get("location", {})
    city = loc_data.get("city")
    region = loc_data.get("region")
    country = loc_data.get("country")
    is_remote_flag = loc_data.get("remote", False)
    
    parts = [x for x in [city, region, country] if x]
    loc_str = ", ".join(parts)
    
    # If their API says explicitly it's remote, ensure we capture that even if text doesn't say "Remote"
    if is_remote_flag:
        # Append "Remote" to string so parser picks it up? 
        # Or manually set flag.
        # Let's just append "Remote" to the string we parse if it's not there.
        if "remote" not in loc_str.lower():
            loc_str = f"Remote - {loc_str}"
    
    parsed_locations = [parse_location(loc_str)]
    
    # Date
    # releasedDate or createdOn
    posted_at_raw = job.get("releasedDate") or job.get("createdOn")
    posted_at = parse_posted_at(posted_at_raw)

    return {
        "source_ats": "smartrecruiters",
        "company_slug": "",
        "job_key": str(job.get("id")),
        "req_id": str(job.get("refNumber") or job.get("id")),
        "title": job.get("name"),
        "url": f"https://jobs.smartrecruiters.com/{job.get('company', {}).get('identifier')}/{job.get('id')}", 
        # SmartRecruiters doesn't always give direct URL in list, constructing it
        # Actually usually it's not in the list response. 
        # But we can try to guess or use the CLI link if available.
        # Let's check raw data structure if needed. For now constructing standard link.
        "locations": parsed_locations,
        "location_display": loc_str,
        "posted_at": posted_at,
        "first_seen_at": datetime.datetime.utcnow().isoformat() + "Z",
        "last_seen_at": datetime.datetime.utcnow().isoformat() + "Z",
        "status": "open"
    }
