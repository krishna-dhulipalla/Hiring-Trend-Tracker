import re
import difflib
from datetime import datetime, timedelta, timezone
import dateutil.parser
from src.config import HARD_NEGATIVES, ABBREVIATIONS, ROLE_FAMILIES, SPECIAL_TOKENS


# ---------------------------------------------------------------------------
# Constants for Location Parsing
# ---------------------------------------------------------------------------

US_CITIES_WEAK = {
    "san jose", "seattle", "austin", "new york", "boston", "dallas", 
    "san francisco", "los angeles", "chicago", "atlanta", "denver",
    "palo alto", "mountain view", "sunnyvale", "redmond", "menlo park"
}

NON_US_REGIONS = {
    "europe", "emea", "apac", "latam", "canada", "india", "singapore", 
    "spain", "poland", "germany", "france", "australia", "uk", "united kingdom",
    "london", "toronto", "vancouver", "montreal", "berlin", "munich", 
    "paris", "bangalore", "bengaluru", "pune", "hyderabad", "delhi", "mumbai",
    "china", "japan", "tokyo", "beijing", "shanghai", "ireland", "dublin",
    "netherlands", "amsterdam", "sweden", "stockholm", "switzerland", "zurich"
}

# ---------------------------------------------------------------------------
# Location Parsing Logic
# ---------------------------------------------------------------------------

def parse_location(location_name):
    """
    Parses a location string into a structured dictionary.
    Strict US detection rules applied.
    """
    if not location_name:
        return {
            "raw": None, 
            "city": None, 
            "state": None, 
            "country_code": None, 
            "is_us": False, 
            "is_remote": False,
            "has_non_us_marker": False
        }

    loc_lower = location_name.lower().strip()
    
    # 1. Check for Non-US Markers immediately
    has_non_us_marker = False
    for marker in NON_US_REGIONS:
        # Check for whole words or word boundaries to avoid partial matches like "spain" in "splaining"
        if re.search(r'\b' + re.escape(marker) + r'\b', loc_lower):
            has_non_us_marker = True
            break
            
    # Also check ISO prefixes (CA-, IN-, FR-, etc.) excluding US-
    if re.search(r'\b(ca|in|fr|de|pl|gb|uk|au|br|cn|jp)-', loc_lower):
        has_non_us_marker = True

    # 2. Remote detection
    is_remote = "remote" in loc_lower
    
    # 3. US Detection - Strict Rules
    is_us = False
    
    # Rule A: Explicit US Country Name
    if any(x in loc_lower for x in ["united states", "usa", "u.s."]) or re.search(r'\b(us)\b', loc_lower):
        is_us = True
        
    # Rule B: US- Prefix
    if "us-" in loc_lower: 
        is_us = True

    # Rule C: State Codes
    if not is_us:
        # Standard US State codes
        us_state_codes = [
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", 
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", 
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", 
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", 
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
            "DC"
        ]
        for code in us_state_codes:
            # Match ", CA", " CA ", ",CA"
            if re.search(r'[\s,]{}\b'.format(code), location_name): 
                 is_us = True
                 break

    # Rule D: Full State Names
    if not is_us:
        full_state_names = [
            "alabama", "alaska", "arizona", "arkansas", "california", "colorado", 
            "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho", 
            "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", 
            "maine", "maryland", "massachusetts", "michigan", "minnesota", 
            "mississippi", "missouri", "montana", "nebraska", "nevada", 
            "new hampshire", "new jersey", "new mexico", "new york", 
            "north carolina", "north dakota", "ohio", "oklahoma", "oregon", 
            "pennsylvania", "rhode island", "south carolina", "south dakota", 
            "tennessee", "texas", "utah", "vermont", "virginia", "washington", 
            "west virginia", "wisconsin", "wyoming", "district of columbia"
        ]
        for state in full_state_names:
            if state in loc_lower:
                is_us = True
                break
                
    # Rule E: Weak US Cities (only if no non-US marker)
    if not is_us and not has_non_us_marker:
        for city in US_CITIES_WEAK:
            if city in loc_lower:
                is_us = True
                break
    
    return {
        "raw": location_name,
        "city": None,
        "state": None,
        "country_code": "US" if is_us else None,
        "is_us": is_us,
        "is_remote": is_remote,
        "has_non_us_marker": has_non_us_marker
    }

def parse_posted_at(date_string):
    """
    Parses a date string into a UTC ISO 8601 string.
    Handles relative dates like "Posted 3 days ago".
    Returns None if parsing fails.
    """
    if not date_string:
        return None
        
    try:
        # 0. Handle epoch timestamps (int/float)
        if isinstance(date_string, (int, float)):
             # Assume seconds or milliseconds?
             # Workday usually gives milliseconds if it's huge, or string ISO.
             # If int, let's guess. If > 30000000000 (year 2920), likely millis.
             # Common cut off: 10 digits = seconds. 13 digits = millis.
             # 1733678788 (seconds) ~ 2024.
             ts = float(date_string)
             if ts > 100000000000: # Milliseconds
                 ts = ts / 1000.0
             dt = datetime.fromtimestamp(ts, tz=timezone.utc)
             return dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

        # 1. Handle "X days ago" or "Posted X days ago"
        lower_date = str(date_string).lower()
        if "ago" in lower_date:
            # Extract number
            match = re.search(r'(\d+)\+?\s*days?', lower_date)
            if match:
                days_ago = int(match.group(1))
                dt = datetime.utcnow() - timedelta(days=days_ago)
                return dt.isoformat()
            
            if "today" in lower_date:
                return datetime.utcnow().isoformat()
            
            if "yesterday" in lower_date:
                return (datetime.utcnow() - timedelta(days=1)).isoformat()
            
            # "30+ days ago" usually handled by regex above, but check just in case
            if "30+" in lower_date:
                 dt = datetime.utcnow() - timedelta(days=30)
                 return dt.isoformat()

        # 2. Handle "Today", "Yesterday" without "ago"
        if lower_date == "posted today" or lower_date == "today":
             return datetime.utcnow().isoformat()
        if lower_date == "posted yesterday" or lower_date == "yesterday":
             return (datetime.utcnow() - timedelta(days=1)).isoformat()

        # 3. Absolute Date Parsing
        # Use dateutil for robust parsing
        dt = dateutil.parser.parse(date_string)
        
        # Convert to UTC
        # If naive, assume midnight local -> UTC (which determines date)
        # But safest is just assume it's roughly correct.
        if dt.tzinfo is None:
            # Assume UTC for simplicity or local time?
            # Requirement: "Date-only (no time) -> treat as local midnight -> then UTC."
            # We'll just format as ISO which implies local if no Z, but let's append Z if we want UTC
             return dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        else:
            # Convert to UTC
            dt_utc = dt.astimezone(datetime.timezone.utc)
            return dt_utc.isoformat().replace("+00:00", "Z")

    except Exception:
        return None



def is_us_eligible(job):
    """
    Returns True if the job is considered US-eligible.
    Criteria: 
    1. Any location has is_us == True.
    2. OR (is_remote == True AND no non-US region word in that location text).
    """
    locations = job.get("locations", [])
    if not locations:
        return False
        
    for loc in locations:
        # 1. Explicit US
        if loc.get("is_us"):
            return True
            
        # 2. Remote + No Non-US marker
        if loc.get("is_remote") and not loc.get("has_non_us_marker"):
            return True
            
    return False

def normalize_title(title):

    """
    Normalizes a job title:
    1. Lowercase
    2. Replace fancy dashes and extra punctuation
    3. Tokenize
    4. Expand abbreviations
    5. Fuzzy correct special tokens
    """
    if not title:
        return []

    # 1. Lowercase
    text = title.lower()

    # 2. Replace fancy dashes and cleanup
    text = text.replace('–', '-').replace('—', '-')
    text = re.sub(r'[^\w\s-]', ' ', text) # Keep words, spaces, hyphens
    
    # 3. Tokenize (split by whitespace and hyphens)
    tokens = re.split(r'[\s-]+', text)
    tokens = [t for t in tokens if t] # Remove empty tokens

    normalized_tokens = []
    for token in tokens:
        # 4. Expand abbreviations
        if token in ABBREVIATIONS:
            # If abbreviation expands to multiple words, add them all
            expanded = ABBREVIATIONS[token].split()
            normalized_tokens.extend(expanded)
            continue

        # 5. Fuzzy correction (optional, conservative)
        # Check if token is close to a special token
        # Only if token length > 3 to avoid short word noise
        if len(token) > 3:
            matches = difflib.get_close_matches(token, SPECIAL_TOKENS, n=1, cutoff=0.85)
            if matches:
                normalized_tokens.append(matches[0])
                continue
        
        normalized_tokens.append(token)

    return normalized_tokens

def is_hard_negative(tokens):
    """
    Returns True if any token is a hard negative.
    """
    for token in tokens:
        if token in HARD_NEGATIVES:
            return True
    return False

def calculate_title_score(tokens):
    """
    Calculates a score for the title based on role families.
    Returns (score, matched_family)
    """
    title_text = " ".join(tokens)
    max_score = 0
    best_family = None

    for family, rules in ROLE_FAMILIES.items():
        score = 0
        
        # Check strong phrases (+2)
        for phrase in rules["strong_phrases"]:
            if phrase in title_text:
                score += 2
                # If we match a strong phrase, we can probably stop or just take it
        
        # Check core keywords (+1 if present)
        # We want at least one core keyword to consider it relevant if no strong phrase
        has_core = False
        for core in rules["core"]:
            if core in title_text: # Simple substring check for multi-word cores
                has_core = True
                break
        
        if has_core:
            score += 1

        # Check roles (+1 if present AND has_core)
        # e.g. "engineer" is good, but only if we have "data" or "ml"
        has_role = False
        for role in rules["roles"]:
            if role in tokens:
                has_role = True
                break
        
        if has_core and has_role:
            score += 1
            
        if score > max_score:
            max_score = score
            best_family = family

    return max_score, best_family

def is_valid_job(title):
    """
    Main entry point for filtering.
    Returns True if the job title is valid/relevant.
    """
    if not title:
        return False

    tokens = normalize_title(title)
    
    # 1. Hard negative filter
    if is_hard_negative(tokens):
        return False

    # 2. Scoring
    score, family = calculate_title_score(tokens)
    
    # Threshold: score >= 2 means it matched a strong phrase OR (core + role)
    if score >= 2:
        return True
        
    return False
