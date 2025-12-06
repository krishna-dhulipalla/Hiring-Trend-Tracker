from src.utils import parse_location, parse_posted_at
import json

tests_loc = [
    "CA-Ontario-Toronto",
    "Pune, IND",
    "London",
    "San Jose, CA",
    "Remote — US",
    "Austin TX",
    "Berlin, Germany",
    "United States"
]

print("--- Location Parsing Tests ---")
for t in tests_loc:
    print(f"'{t}' -> {json.dumps(parse_location(t))}")

tests_date = [
    "Posted 3 days ago",
    "Posted Today",
    "2023-10-25",
    "2023-10-25T12:00:00Z",
    "30+ days ago"
]

print("\n--- Date Parsing Tests ---")
for d in tests_date:
    print(f"'{d}' -> {parse_posted_at(d)}")
