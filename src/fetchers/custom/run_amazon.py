
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.fetchers.custom import amazon

def run():
    print("Running Amazon Fetcher Test...")
    config = {
        "params": {
            "result_limit": 10,
            "offset": 0,
            "category": ["software-development"]
        }
    }
    
    jobs = amazon.fetch_jobs(config, max_pages=2)
    
    print(json.dumps(jobs, indent=2, default=str))
    print(f"Summary: {{ adapter: 'amazon', items: {len(jobs)} }}")

if __name__ == "__main__":
    run()
