import requests

def fetch_jobs(company_slug):
    """
    Fetches jobs from the Ashby Public API for a given company.
    Endpoint: https://api.ashbyhq.com/posting-api/job-board/{company_slug}
    Note: Ashby public API structure can vary, but usually:
    POST https://api.ashbyhq.com/posting-api/job-board/{company_slug} (GraphQL or specialized)
    OR GET https://api.ashbyhq.com/posting-api/job-board/{company_slug}
    
    Actually, the user provided: /api/public/job-boards/{company}/jobs
    Let's try that one first.
    """
    # User suggested: /api/public/job-boards/{company}/jobs
    # But often it is https://jobs.ashbyhq.com/api/non-user-facing/custom/job-board/{company_slug}
    # Or https://api.ashbyhq.com/posting-api/job-board/{company_slug}
    
    # Let's try the one suggested by user or common one.
    # Common public one: https://api.ashbyhq.com/posting-api/job-board/{company_slug}
    # But let's try the user's suggestion if it looks like a known pattern.
    # "Endpoints look like: /api/public/job-boards/{company}/jobs"
    
    # Let's try constructing a few common URLs if one fails, or just stick to one.
    # I'll try the one that seems most standard for "scraping" or public access.
    # https://jobs.ashbyhq.com/api/non-user-facing/custom/job-board/{company_slug} is very common for frontend.
    
    # However, let's try the user's hint:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}"
    
    # Ashby often requires a POST with empty body to get jobs? Or just GET?
    # Let's try GET first.
    
    try:
        response = requests.get(url)
        # If 404 or error, maybe try the other one
        if not response.ok:
             url = f"https://jobs.ashbyhq.com/api/non-user-facing/custom/job-board/{company_slug}"
             response = requests.get(url)
             
        response.raise_for_status()
        data = response.json()
        
        # Structure might be data['jobs'] or just data
        raw_jobs = data.get('jobs', [])
        
        normalized_jobs = []
        for job in raw_jobs:
            # Ashby location structure
            # "address": { "postalAddress": { "addressCountry": "US", "addressRegion": "CA", "addressLocality": "San Francisco" } }
            # or "location": "San Francisco, CA"
            
            loc_str = job.get("location")
            if not loc_str and "address" in job:
                addr = job["address"].get("postalAddress", {})
                parts = [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry")]
                loc_str = ", ".join([p for p in parts if p])
            
            normalized_jobs.append({
                "company_slug": company_slug,
                "req_id": str(job.get("id")),
                "title": job.get("title"),
                "location": loc_str,
                "url": job.get("jobUrl")
            })
        return normalized_jobs
    except requests.RequestException as e:
        print(f"Error fetching Ashby jobs for {company_slug}: {e}")
        return []
