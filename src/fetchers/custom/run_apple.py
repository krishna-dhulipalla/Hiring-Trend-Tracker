
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.fetchers.custom import apple

def run():
    print("Running Apple Fetcher Test...")
    config = {
        "pageNumber": 1,
        "itemsPerPage": 10,
        "filters": {
            "keyword": "software"
        }
    }
    
    jobs = apple.fetch_jobs(config, max_pages=2)
    
    print(json.dumps(jobs, indent=2, default=str))
    print(f"Summary: {{ adapter: 'apple', items: {len(jobs)} }}")

if __name__ == "__main__":
    run()
