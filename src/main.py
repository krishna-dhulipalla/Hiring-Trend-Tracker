from src.fetchers import greenhouse, lever, ashby, smartrecruiters, workday
from src.utils import parse_location, title_matches
import sys
import os

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Configuration of companies and their ATS
COMPANIES = [
    {"slug": "figma", "ats": "greenhouse"},
    {"slug": "gusto", "ats": "greenhouse"},
    {"slug": "linear", "ats": "ashby"},
    {"slug": "ramp", "ats": "ashby"},
    {"slug": "netflix", "ats": "lever"},
    {"slug": "square", "ats": "smartrecruiters"},
    # {"slug": "nvidia", "ats": "workday"}, # Workday is complex, skipping for now
]


def get_fetcher(ats_name):
    if ats_name == "greenhouse":
        return greenhouse
    elif ats_name == "lever":
        return lever
    elif ats_name == "ashby":
        return ashby
    elif ats_name == "smartrecruiters":
        return smartrecruiters
    elif ats_name == "workday":
        return workday
    else:
        return None


def main():
    print(f"{'COMPANY':<15} | {'ATS':<10} | {'REQ_ID':<10} | {'TITLE':<50} | {'LOCATION':<30} | {'URL'}")
    print("-" * 180)

    seen_ids = set()

    for company_info in COMPANIES:
        company_slug = company_info["slug"]
        ats_name = company_info["ats"]

        fetcher = get_fetcher(ats_name)
        if not fetcher:
            print(f"Unknown ATS '{ats_name}' for {company_slug}")
            continue

        print(f"Fetching {company_slug} ({ats_name})...")
        jobs = fetcher.fetch_jobs(company_slug)
        total_fetched = len(jobs)

        filtered_jobs = []
        for job in jobs:
            # Filter by title
            if not title_matches(job['title']):
                continue

            # Parse location
            loc_data = parse_location(job['location'])

            # Filter by location (US only)
            if not loc_data['is_us']:
                continue

            # Deduplication
            job_unique_id = f"{company_slug}_{job['req_id']}"
            if job_unique_id in seen_ids:
                continue
            seen_ids.add(job_unique_id)

            filtered_jobs.append(job)

        print(f"{company_slug} ({ats_name}) summary: fetched {total_fetched}, after filters {len(filtered_jobs)}")
        for job in filtered_jobs:
            try:
                print(
                    f"{company_slug:<15} | {ats_name:<10} | {job['req_id']:<10} | {job['title'][:50]:<50} | {job['location'][:30]:<30} | {job['url']}")
            except Exception:
                pass


if __name__ == "__main__":
    main()
