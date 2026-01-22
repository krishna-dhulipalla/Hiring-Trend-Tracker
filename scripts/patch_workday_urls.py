import os
import json
import re

DIFFS_DIR = os.path.abspath("data/diffs/workday")

def patch_url(url):
    # Fix: https://host/en-US/tenant/site/job/... -> https://host/en-US/site/job/...
    # Matches /en-US/segment1/segment2/job/ and removes segment1
    pattern = r"(/en-US)/([^/]+)/([^/]+)(/job/)"
    if re.search(pattern, url):
        return re.sub(pattern, r"\1/\3\4", url)
    return url

count = 0
for root, dirs, files in os.walk(DIFFS_DIR):
    for file in files:
        if file.endswith(".json"):
            path = os.path.join(root, file)
            changed = False
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Check top-level added/removed
                for key in ["added", "removed"]:
                    if key in data:
                        for job in data[key]:
                            if "url" in job:
                                new_url = patch_url(job["url"])
                                if new_url != job["url"]:
                                    job["url"] = new_url
                                    changed = True
                
                # Check nested details
                if "details" in data:
                    for key in ["added", "removed"]:
                        if key in data["details"]:
                            for job in data["details"][key]:
                                if "url" in job:
                                    new_url = patch_url(job["url"])
                                    if new_url != job["url"]:
                                        job["url"] = new_url
                                        changed = True
                                        
                if changed:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                    count += 1
            except Exception as e:
                print(f"Error patching {path}: {e}")

print(f"Patched {count} files.")
