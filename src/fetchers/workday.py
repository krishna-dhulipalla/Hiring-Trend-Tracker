import requests
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from src.utils import parse_location, parse_posted_at

class WorkdayAgent:
    def __init__(self):
        self.companies = self._load_companies()
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _load_companies(self) -> List[Dict[str, str]]:
        config_path = os.path.join(os.path.dirname(__file__), "..", "workday_companies.json")
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config file not found at {config_path}")
            return []

    def normalize_job(self, raw_job: Dict[str, Any], company_config: Dict[str, str]) -> Dict[str, Any]:
        """
        Normalizes a Workday job posting into the unified schema.
        """
        job_info = raw_job.get("jobPostingInfo", {})
        
        # If company_config is missing or None (safety check)
        if not company_config:
            # Try to return partial
            return {
                "source_ats": "workday",
                "title": raw_job.get("title", "Unknown"),
                "raw": raw_job
            }

        host = company_config["host"]
        tenant = company_config["tenant"]
        site_slug = company_config["site_slug"]

        # Handle flat structure vs nested
        if not job_info:
            title = raw_job.get("title")
            external_path = raw_job.get("externalPath", "")
            job_url = f"https://{host}/en-US/{tenant}/{site_slug}{external_path}"
            location_raw = raw_job.get("locationsText", "")
            posted_at_raw = raw_job.get("postedOn")
            
            # Req ID
            req_id = None
            if "bulletFields" in raw_job and raw_job["bulletFields"]:
                req_id = raw_job["bulletFields"][0]
            
            all_locations_str = [location_raw]
        else:
            # Standard structure
            title = job_info.get("title")
            external_path = raw_job.get("externalPath", "")
            job_url = f"https://{host}/en-US/{tenant}/{site_slug}{external_path}"
            location_raw = job_info.get("location", "")
            
            # Additional locations are usually strings in 'additionalLocations'
            additional_locations = job_info.get("additionalLocations", [])
            all_locations_str = [location_raw] + additional_locations
            
            req_id = job_info.get("jobReqId")
            posted_at_raw = job_info.get("postedDate")

        # Parse ALL locations
        # Schema requires `locations` to be a list of objects.
        # We also need a `location_display`.
        
        parsed_locations = []
        for loc in all_locations_str:
            if loc:
                parsed_locations.append(parse_location(loc))

        # Parse Date
        posted_at = parse_posted_at(posted_at_raw)

        return {
            "source_ats": "workday",
            "company_slug": company_config["company_slug"],
            "job_key": external_path, # unique enough per tenant
            "req_id": req_id,
            "title": title,
            "url": job_url,
            "locations": parsed_locations,
            "location_display": location_raw, # Primary location
            "posted_at": posted_at,
            "first_seen_at": datetime.utcnow().isoformat() + "Z",
            "last_seen_at": datetime.utcnow().isoformat() + "Z",
            "status": "open"
        }

    def fetch_company_jobs(self, company: Dict[str, str]) -> List[Dict]:
        """
        Fetches jobs for a single company. Returns raw_jobs.
        """
        host = company["host"]
        tenant = company["tenant"]
        site_slug = company["site_slug"]
        base_endpoint = f"/wday/cxs/{tenant}/{site_slug}/jobs"
        url = f"https://{host}{base_endpoint}"
        
        all_raw_jobs = []
        offset = 0
        limit = 20
        total_jobs = 0 # To track total
        
        print(f"[{company['company_slug']}] Starting job fetch...")

        while True:
            payload = {
                "limit": limit,
                "offset": offset,
                "searchText": "",
                "appliedFacets": {}
            }

            try:
                response = requests.post(url, json=payload, headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    total_jobs = data.get("total", 0)
                    job_postings = data.get("jobPostings", [])
                    
                    # Inject company config into each job for later normalization
                    for job in job_postings:
                        job["_company_config"] = company

                    all_raw_jobs.extend(job_postings)
                    
                    if offset % 100 == 0:
                        print(f"[{company['company_slug']}] Fetched {len(all_raw_jobs)}/{total_jobs}")

                    if offset + limit >= total_jobs:
                        break
                    
                    offset += limit
                    
                elif response.status_code == 429 or response.status_code == 503:
                    time.sleep(5)
                    continue
                else:
                    print(f"[{company['company_slug']}] Error: {response.status_code}")
                    break

            except Exception as e:
                print(f"[{company['company_slug']}] Exception: {e}")
                break
        
        return all_raw_jobs

# Module-level interface
_agent = WorkdayAgent()

def fetch_jobs(company_slug: str) -> List[Dict[str, Any]]:
    """
    Fetches jobs for a specific company slug using the WorkdayAgent.
    """
    company_config = next((c for c in _agent.companies if c["company_slug"] == company_slug), None)
    
    if not company_config:
        print(f"No Workday config for {company_slug}")
        return []
    
    # Returns raw jobs with injected config
    raw_jobs = _agent.fetch_company_jobs(company_config)
    return raw_jobs

def normalize_job(raw_job):
    """
    Wrapper for normalize_job to be called by main.py
    """
    config = raw_job.get("_company_config")
    
    # If config not found (shouldn't happen if fetched via fetch_jobs), 
    # we can try to recover or fail gracefully.
    
    return _agent.normalize_job(raw_job, config)
