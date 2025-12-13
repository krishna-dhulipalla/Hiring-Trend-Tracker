
import requests
import time
import random
from src.utils import parse_location, parse_posted_at

def fetch_jobs(config, max_pages=None):
    """
    Fetches jobs from Amazon Jobs.
    max_pages: Optional int limit.
    """
    base_params = config.get("params", {})
    if "result_limit" not in base_params:
        base_params["result_limit"] = 50
    if "offset" not in base_params:
        base_params["offset"] = 0
        
    offset = base_params["offset"]
    limit = base_params["result_limit"]
    
    all_jobs = []
    page_count = 0
    url = "https://www.amazon.jobs/en/search.json"
    
    while True:
        if max_pages and page_count >= max_pages:
            print(f"Reached max_pages {max_pages}. Stopping.")
            break
            
        page_count += 1
        print(f"Fetching Amazon offset {offset}...")
        
        current_params = base_params.copy()
        current_params["offset"] = offset
        
        try:
            resp = requests.get(url, params=current_params)
            if resp.status_code in [429, 500, 502, 503, 504]:
                print(f"Got {resp.status_code}, backing off...")
                time.sleep(random.uniform(5, 10))
                continue
                
            resp.raise_for_status()
            data = resp.json()
            
            jobs_list = data.get("jobs", [])
            hits = data.get("hits", 0)
            
            if not jobs_list:
                print("No jobs returned. Stopping.")
                break
                
            for item in jobs_list:
                job_id = str(item.get("id_icims") or item.get("id"))
                title = item.get("title")
                
                locs = []
                if "locations" in item and isinstance(item["locations"], list):
                     locs = item["locations"]
                elif "location" in item:
                     locs = [item["location"]]
                else:
                     city = item.get("city")
                     state = item.get("state")
                     country = item.get("country_code")
                     parts = [p for p in [city, state, country] if p]
                     if parts:
                         locs = [", ".join(parts)]
                
                parsed_locs = [parse_location(l) for l in locs]
                
                job_path = item.get("job_path")
                item_url = f"https://www.amazon.jobs{job_path}" if job_path else None
                posted_date = parse_posted_at(item.get("posted_date"))
                
                job = {
                    "job_id": job_id,
                    "title": title,
                    "company": "Amazon",
                    "locations": parsed_locs,
                    "url": item_url,
                    "employment_type": item.get("schedule_type_id"),
                    "posted_date": posted_date,
                    "remote_status": None,
                    "description_raw": item.get("description"),
                    "department": item.get("job_category"),
                    "team": item.get("team"),
                    "sub_teams": None,
                    "source": "amazon",
                    "fetched_at": None
                }
                all_jobs.append(job)
            
            offset += limit
            
            if offset >= hits:
                print(f"Offset {offset} >= hits {hits}. Stopping.")
                break
                
            if len(jobs_list) < limit:
                print(f"Returned {len(jobs_list)} items < limit {limit}. Stopping.")
                break
            
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"Error on Amazon offset {offset}: {e}")
            break
            
    return all_jobs
