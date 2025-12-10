
import requests
import time
import random
from src.utils import parse_location, parse_posted_at

def fetch_jobs(config, max_pages=None):
    """
    Fetches jobs from Apple Jobs API.
    max_pages: Optional int limit.
    """
    page = config.get("pageNumber", 1)
    items_per_page = config.get("itemsPerPage", 50)
    filters = config.get("filters", {})
    
    all_jobs = []
    
    session = requests.Session()
    
    print("Getting Apple CSRF token...")
    csrf_token = None
    try:
        resp = session.get("https://jobs.apple.com/en-us/search", headers={"User-Agent": "Mozilla/5.0"})
        csrf_token = resp.headers.get('X-Apple-CSRF-Token')
    except Exception as e:
        print(f"Error getting CSRF: {e}")
        
    search_url = "https://jobs.apple.com/api/v1/search"
    
    pages_fetched = 0
    
    while True:
        if max_pages and pages_fetched >= max_pages:
            print(f"Reached max_pages {max_pages}. Stopping.")
            break
            
        pages_fetched += 1
        print(f"Fetching Apple page {page}...")
        
        payload = {
            "query": "",
            "filters": filters,
            "page": page, 
            "itemsPerPage": items_per_page
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json"
        }
        if csrf_token:
            headers["X-Apple-CSRF-Token"] = csrf_token
            
        try:
            resp = session.post(search_url, json=payload, headers=headers)
            
            if resp.status_code == 403:
                print("Got 403 Forbidden. CSRF issue likely.")
                break
                
            if resp.status_code in [429, 500, 502, 503, 504]:
                print(f"Got {resp.status_code}, backing off...")
                time.sleep(random.uniform(5, 10))
                continue
                
            resp.raise_for_status()
            data = resp.json()
            
            results = data.get("searchResults", [])
            total_records = data.get("totalRecords", 0)
            
            if not results:
                print("No results returned. Stopping.")
                break
                
            for item in results:
                job_id = item.get("id") or item.get("positionId")
                title = item.get("postingTitle") or item.get("title")
                
                locs_raw = item.get("locations", [])
                loc_list = []
                for l in locs_raw:
                    city = l.get("city")
                    state = l.get("stateCode") or l.get("state")
                    country = l.get("countryName") or l.get("countryID")
                    parts = [p for p in [city, state, country] if p]
                    loc_list.append(", ".join(parts))
                    
                parsed_locs = [parse_location(l) for l in loc_list]
                
                item_url = f"https://jobs.apple.com/en-us/details/{job_id}"
                posted_date = parse_posted_at(item.get("postingDate"))
                
                job = {
                    "job_id": str(job_id),
                    "title": title,
                    "company": "Apple",
                    "locations": parsed_locs,
                    "url": item_url,
                    "employment_type": item.get("schedule"), 
                    "posted_date": posted_date,
                    "remote_status": None,
                    "description_raw": item.get("description"),
                    "department": item.get("team", {}).get("name") if isinstance(item.get("team"), dict) else item.get("team"),
                    "team": None,
                    "sub_teams": None,
                    "source": "apple",
                    "fetched_at": None
                }
                all_jobs.append(job)
            
            if (page * items_per_page) >= total_records:
                print(f"Page {page} * {items_per_page} >= {total_records}. Stopping.")
                break
                
            if len(results) < items_per_page:
                 break
                 
            page += 1
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"Error on Apple page {page}: {e}")
            break
            
    return all_jobs
