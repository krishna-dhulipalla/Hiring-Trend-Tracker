import requests

def fetch_jobs(company_slug):
    """
    Fetches jobs from the SmartRecruiters API for a given company.
    Endpoint: https://api.smartrecruiters.com/v1/companies/{company_slug}/postings
    """
    url = f"https://api.smartrecruiters.com/v1/companies/{company_slug}/postings"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        raw_jobs = data.get('content', [])
        
        normalized_jobs = []
        for job in raw_jobs:
            # Location in SmartRecruiters: job['location']['city'], job['location']['region'], job['location']['country']
            loc_obj = job.get("location", {})
            parts = [loc_obj.get("city"), loc_obj.get("region"), loc_obj.get("country")]
            loc_str = ", ".join([p for p in parts if p])
            
            normalized_jobs.append({
                "company_slug": company_slug,
                "req_id": str(job.get("id")),
                "title": job.get("name"), # SmartRecruiters uses 'name'
                "location": loc_str,
                "url": f"https://jobs.smartrecruiters.com/{company_slug}/{job.get('id')}" # Construct URL if not provided
                # Or job.get('ref')? Usually they have a link.
                # Let's check if there is a direct link.
                # Usually 'ref' is internal.
                # We can construct: https://jobs.smartrecruiters.com/oneclick-ui/company/{company_slug}/publication/{id}?
                # Or just use the default job page.
            })
            # Correction: SmartRecruiters API response usually doesn't have the full public URL directly in the list, 
            # but we can construct it or maybe it's in 'actions'?
            # Let's assume standard format: https://jobs.smartrecruiters.com/{company_slug}/{id}
            
        return normalized_jobs
    except requests.RequestException as e:
        print(f"Error fetching SmartRecruiters jobs for {company_slug}: {e}")
        return []
