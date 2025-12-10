
import requests
import time
import random
import re
from bs4 import BeautifulSoup
from src.utils import parse_location

def fetch_jobs(url, max_pages=None):
    """
    Fetches jobs from Google Careers.
    max_pages: Optional int limit for testing.
    """
    all_jobs = []
    page = 1
    
    if '?' not in url:
        url += '?'
    
    base_url = url
    
    while True:
        if max_pages and page > max_pages:
            print(f"Reached max_pages {max_pages}. Stopping.")
            break
            
        target_url = f"{base_url}&page={page}"
        print(f"Fetching Google page {page}...")
        
        try:
            resp = requests.get(target_url)
            if resp.status_code in [429, 500, 502, 503, 504]:
                print(f"Got {resp.status_code}, backing off...")
                time.sleep(random.uniform(5, 10))
                continue
            
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            cards = soup.select('ul.spHGqe > li.lLd3Je')
            
            if not cards:
                print(f"No cards found on page {page}. Stopping.")
                break
                
            print(f"Found {len(cards)} cards on page {page}.")
            
            page_jobs = []
            for card in cards:
                title_elem = card.select_one('h3.QJPWVe')
                title = title_elem.get_text(strip=True) if title_elem else None
                company = "Google"
                
                loc_elems = card.select('.r0wTof')
                raw_locs = [el.get_text(strip=True) for el in loc_elems]
                locations = [parse_location(l) for l in raw_locs]
                
                link_elem = card.select_one('a[href^="jobs/results/"]')
                item_url = None
                job_id = None
                
                if link_elem:
                    href = link_elem.get('href')
                    item_url = f"https://www.google.com/about/careers/applications/{href}"
                    match = re.search(r'jobs/results/(\d+)', href)
                    if match:
                        job_id = match.group(1)
                
                if not job_id:
                    if item_url:
                        job_id = str(abs(hash(item_url)))
                    else:
                        job_id = str(abs(hash(title + str(raw_locs))))

                job = {
                    "job_id": job_id,
                    "title": title,
                    "company": company,
                    "locations": locations,
                    "url": item_url,
                    "employment_type": None,
                    "posted_date": None, 
                    "remote_status": None,
                    "description_raw": None, 
                    "department": None,
                    "team": None,
                    "sub_teams": None,
                    "source": "google",
                    "fetched_at": None 
                }
                
                page_jobs.append(job)
            
            if not page_jobs:
                print("No jobs extracted from cards. Stopping.")
                break

            if all_jobs and page_jobs[0]['job_id'] == all_jobs[-len(page_jobs)]['job_id']:
                 print("Duplicate page detected (first item match). Stopping.")
                 break
                 
            all_jobs.extend(page_jobs)
            
            if len(cards) < 20:
                print(f"Page {page} has {len(cards)} items (< 20). Stopping.")
                break
                
            page += 1
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break
            
    return all_jobs
