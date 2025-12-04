import requests
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from src.utils import parse_location, title_matches

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
        Normalizes a Workday job posting into the common schema.
        """
        job_info = raw_job.get("jobPostingInfo", {})
        host = company_config["host"]
        tenant = company_config["tenant"]
        site_slug = company_config["site_slug"]
        
        # Construct full URL
        external_path = raw_job.get("externalPath", "")
        job_url = f"https://{host}/en-US/{tenant}/{site_slug}{external_path}"

        # Locations
        location_raw = job_info.get("location", "")
        additional_locations = job_info.get("additionalLocations", [])
        all_locations = [location_raw] + additional_locations
        
        # Parse the primary location (or iterate if you want to support multiple)
        parsed_loc = parse_location(location_raw)

        return {
            "source_ats": "workday",
            "company_slug": company_config["company_slug"],
            "req_id": job_info.get("jobReqId"),
            "title": job_info.get("title"),
            "locations": all_locations,
            "url": job_url,
            "posted_at": job_info.get("postedDate"),
            "location_parsed": parsed_loc,
            "raw": raw_job
        }

    def fetch_company_jobs(self, company: Dict[str, str]) -> tuple[List[Dict], List[Dict]]:
        """
        Fetches jobs for a single company. Returns (raw_jobs, normalized_jobs).
        """
        host = company["host"]
        tenant = company["tenant"]
        site_slug = company["site_slug"]
        base_endpoint = f"/wday/cxs/{tenant}/{site_slug}/jobs"
        url = f"https://{host}{base_endpoint}"
        
        all_raw_jobs = []
        normalized_jobs = []
        offset = 0
        limit = 20
        total_jobs = 0
        
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
                    
                    all_raw_jobs.extend(job_postings)
                    
                    # Normalize and filter immediately
                    for job in job_postings:
                        normalized = self.normalize_job(job, company)
                        if title_matches(normalized["title"]):
                            normalized_jobs.append(normalized)

                    print(f"[{company['company_slug']}] Fetched {len(job_postings)} jobs (Offset: {offset}, Total: {total_jobs})")

                    if offset + limit >= total_jobs:
                        break
                    
                    offset += limit
                    
                elif response.status_code == 429 or response.status_code == 503:
                    print(f"[{company['company_slug']}] Rate limited or service unavailable (Status: {response.status_code}). Retrying in 5 seconds...")
                    time.sleep(5)
                    continue
                elif response.status_code == 403:
                    print(f"[{company['company_slug']}] Access forbidden (Status: 403). Skipping.")
                    break
                else:
                    print(f"[{company['company_slug']}] Error fetching jobs: {response.status_code} - {response.text}")
                    break

            except Exception as e:
                print(f"[{company['company_slug']}] Exception occurred: {e}")
                break
        
        return all_raw_jobs, normalized_jobs

    def run(self):
        """
        Main execution method to fetch jobs for all configured companies.
        """
        data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
        os.makedirs(data_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for company in self.companies:
            raw_jobs, normalized_jobs = self.fetch_company_jobs(company)
            
            print(f"[{company['company_slug']}] Finished. Raw: {len(raw_jobs)}, Normalized: {len(normalized_jobs)}")
            
            # Save snapshots
            slug = company["company_slug"]
            raw_path = os.path.join(data_dir, f"workday_{slug}_raw_{timestamp}.json")
            norm_path = os.path.join(data_dir, f"workday_{slug}_normalized_{timestamp}.json")
            
            with open(raw_path, "w") as f:
                json.dump(raw_jobs, f, indent=2)
                
            with open(norm_path, "w") as f:
                json.dump(normalized_jobs, f, indent=2)
                
            print(f"[{company['company_slug']}] Saved snapshots to {data_dir}")

# Module-level interface for main.py
_agent = WorkdayAgent()

def fetch_jobs(company_slug: str) -> List[Dict[str, Any]]:
    """
    Fetches jobs for a specific company slug using the WorkdayAgent.
    Compatible with the interface expected by main.py.
    """
    company_config = next((c for c in _agent.companies if c["company_slug"] == company_slug), None)
    if not company_config:
        print(f"No Workday config found for {company_slug}")
        return []
    
    _, normalized_jobs = _agent.fetch_company_jobs(company_config)
    
    # Ensure compatibility with main.py
    for job in normalized_jobs:
        if "location" not in job and "locations" in job and job["locations"]:
            job["location"] = job["locations"][0] # Use first location as primary
            
    return normalized_jobs

if __name__ == "__main__":
    _agent.run()
