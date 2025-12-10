
import requests
import json
import time
import random
from src.utils import parse_location

def fetch_jobs(config, max_pages=None):
    """
    Fetches jobs from Meta Careers.
    max_pages: Optional int limit.
    """
    doc_id = config.get("doc_id", "CareersJobSearchResultsV3DataQuery")
    base_variables = config.get("variables", {})
    
    variables = base_variables.copy()
    if "search_input" not in variables:
        variables["search_input"] = {"q": None, "divisions": [], "offices": [], "results_per_page": 50}
        
    all_jobs = []
    has_next = True
    end_cursor = None
    page_count = 0
    
    url = "https://www.metacareers.com/graphql"
    
    while has_next:
        if max_pages and page_count >= max_pages:
            print(f"Reached max_pages {max_pages}. Stopping.")
            break
            
        page_count += 1
        print(f"Fetching Meta page {page_count}...")
        
        if end_cursor:
             variables["search_input"]["after"] = end_cursor
        
        payload = {
            "doc_id": doc_id,
            "variables": variables
        }
        
        try:
            resp = requests.post(url, data=payload)
            if resp.status_code >= 400:
                 resp = requests.post(url, json=payload)
                 
            if resp.status_code in [429, 500, 502, 503, 504]:
                print(f"Got {resp.status_code}, backing off...")
                time.sleep(random.uniform(5, 10))
                continue
                
            resp.raise_for_status()
            data = resp.json()
            
            root = data.get("data", {}).get("job_search_with_featured_jobs", {})
            job_conn = root.get("all_jobs", {})
            raw_items = job_conn.get("all_jobs", [])
            
            if not raw_items:
                print("No items returned. Stopping.")
                break
                
            for item in raw_items:
                job_id = item.get("id")
                title = item.get("title")
                
                loc_raw = item.get("locations", [])
                loc_strings = []
                for l in loc_raw:
                    if isinstance(l, str): loc_strings.append(l)
                    elif isinstance(l, dict): loc_strings.append(l.get('city') or l.get('name') or str(l))
                
                parsed_locs = [parse_location(l) for l in loc_strings]
                
                teams = item.get("teams", [])
                sub_teams = item.get("sub_teams", [])
                
                job = {
                    "job_id": job_id,
                    "title": title,
                    "company": "Meta",
                    "locations": parsed_locs,
                    "url": f"https://www.metacareers.com/jobs/{job_id}/", 
                    "employment_type": None,
                    "posted_date": None, 
                    "remote_status": None,
                    "description_raw": None,
                    "department": teams[0] if teams else None,
                    "team": teams,
                    "sub_teams": sub_teams,
                    "source": "meta",
                    "fetched_at": None 
                }
                all_jobs.append(job)
            
            page_info = job_conn.get("page_info", {})
            has_next_page = page_info.get("has_next_page", False)
            end_cursor = page_info.get("end_cursor")
            
            if not has_next_page:
                has_next = False
            elif not end_cursor:
                has_next = False
            
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"Error on Meta page {page_count}: {e}")
            break
            
    return all_jobs
