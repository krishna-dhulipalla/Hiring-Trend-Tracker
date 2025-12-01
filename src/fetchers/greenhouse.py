import requests

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
        
        normalized_jobs = []
        for job in raw_jobs:
            normalized_jobs.append({
                "company_slug": company_slug,
                "req_id": str(job.get("id")),
                "title": job.get("title"),
                "location": job.get("location", {}).get("name"),
                "url": job.get("absolute_url")
            })
        return normalized_jobs
    except requests.RequestException as e:
        print(f"Error fetching Greenhouse jobs for {company_slug}: {e}")
        return []
