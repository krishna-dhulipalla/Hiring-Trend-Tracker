
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.fetchers.custom import uber

def run():
    print("Running Uber Fetcher Test...")
    config = {
        "payload": {
            "page": 1,
            "size": 10,
            "filters": {
                "department": ["Engineering"] 
            }
        }
    }
    
    jobs = uber.fetch_jobs(config, max_pages=2)
    
    print(json.dumps(jobs, indent=2, default=str))
    print(f"Summary: {{ adapter: 'uber', items: {len(jobs)} }}")

if __name__ == "__main__":
    run()
