import requests

def fetch_jobs(company_slug):
    """
    Fetches jobs from the Lever API for a given company.
    Endpoint: https://api.lever.co/v0/postings/{company_slug}?mode=json
    """
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        raw_jobs = response.json()
        
        normalized_jobs = []
        for job in raw_jobs:
            # Lever location is often in 'categories' -> 'location' or 'text'
            # But the top level 'categories' object has 'location'
            location = job.get("categories", {}).get("location")
            if not location:
                # Fallback to 'country' if available or other fields
                location = job.get("country")
            
            normalized_jobs.append({
                "company_slug": company_slug,
                "req_id": str(job.get("id")),
                "title": job.get("text"), # Lever uses 'text' for title
                "location": location,
                "url": job.get("hostedUrl")
            })
        return normalized_jobs
    except requests.RequestException as e:
        print(f"Error fetching Lever jobs for {company_slug}: {e}")
        return []
