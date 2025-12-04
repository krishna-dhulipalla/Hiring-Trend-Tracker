import sys
import os

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils import is_valid_job, normalize_title, calculate_title_score

test_cases = [
    # Should be ACCEPTED
    ("Senior Data Scientist – Agentic AI & Decision Intelligence", True),
    ("Staff Applied Scientist, ML – Recommendations", True),
    ("Software Engineer", True),
    ("Backend Engineer", True),
    ("Site Reliability Engineer", True),
    ("Machine Learning Engineer", True),
    ("AI Engineer", True),
    ("Data Platform Engineer", True),
    ("Senior MLE", True), # Abbreviation
    ("SWE", True), # Abbreviation
    ("Machine Leaning Engineer", True), # Typo
    
    # Should be REJECTED
    ("Sales Engineer", False), # 'Sales' is hard negative? Let's check config.
    ("Recruiter", False),
    ("HR Manager", False),
    ("Marketing Intern", False),
    ("Scientist, Biology", False), # Missing ML/AI context
    ("Executive Assistant", False),
    ("Director of Engineering", False), # 'Director' is hard negative
    ("VP of Product", False), # 'VP' is hard negative
    ("Customer Support", False),
]

print(f"{'TITLE':<60} | {'EXPECTED':<10} | {'ACTUAL':<10} | {'RESULT':<10}")
print("-" * 100)

failures = 0
for title, expected in test_cases:
    actual = is_valid_job(title)
    result = "PASS" if actual == expected else "FAIL"
    if result == "FAIL":
        failures += 1
        # Debug info
        tokens = normalize_title(title)
        score, family = calculate_title_score(tokens)
        print(f"DEBUG: Tokens: {tokens}, Score: {score}, Family: {family}")
        
    print(f"{title[:60]:<60} | {str(expected):<10} | {str(actual):<10} | {result:<10}")

if failures == 0:
    print("\nAll tests passed!")
else:
    print(f"\n{failures} tests failed.")
