from src.utils import parse_location, is_us_eligible

test_cases = [
    ("Remote - US", True),
    ("Austin, TX", True),
    ("New York, NY", True),
    ("London", False),
    ("Remote Spain", False),
    ("Remote Poland", False),
    ("Berlin, Germany", False),
    ("United States", True),
    ("Remote", False), 
    ("US-CA-San Francisco", True)
]

print("--- US Eligibility Tests ---")
passed = 0
for loc_str, expected in test_cases:
    parsed = parse_location(loc_str)
    mock_job = {"locations": [parsed]}
    result = is_us_eligible(mock_job)
    
    if result != expected:
        print(f"[FAIL] '{loc_str}' -> is_us={parsed['is_us']} -> eligible={result} (Expected: {expected})")
        print(f"       Parsed: {parsed}")
    else:
        passed += 1

print(f"\nPassed {passed}/{len(test_cases)} tests.")
