import re
import difflib
from datetime import datetime, timedelta
import dateutil.parser
from src.config import HARD_NEGATIVES, ABBREVIATIONS, ROLE_FAMILIES, SPECIAL_TOKENS

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
            "is_remote": False
        }

    loc_lower = location_name.lower()
    
    # Remote detection
    is_remote = "remote" in loc_lower
    
    # US Detection - Strict Rules
    is_us = False
    
    # 1. Explicit US Country Name
    if any(x in loc_lower for x in ["united states", "usa", "u.s."]):
        is_us = True
        
    # 2. ISO Prefix US-
    if "us-" in loc_lower: # e.g. "US-CA-San Francisco"
        is_us = True

    # 3. State Codes with delimiters (e.g. ", CA", " TX ")
    # NOT just "CA" which could be Canada or "Call"
    us_state_codes = [
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", 
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", 
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", 
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", 
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC"
    ]
    
    if not is_us:
        for code in us_state_codes:
            # Match ", CA", " CA ", ",CA" (end of string), " CA" (end of string)
            # Regex: (?:^|[,\s])CODE(?:[,\s]|$)
            # But "CA-" is explicit non-US usually if it's CA-ON (Canada-Ontario)
            # However some systems use US-CA.
            # Let's match ", CA" or " CA " specifically as typically seen in "City, ST"
            if re.search(r'[\s,]{}\b'.format(code), location_name): 
                 is_us = True
                 break

    # 4. Full State Names
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
    
    if not is_us:
        for state in full_state_names:
            if state in loc_lower:
                is_us = True
                break
    
    # Non-US Overrides / Explicit Non-US indicators
    # ISO prefixes like CA-, FR-, DE-, IN-, PL- (excluding US-)
    if re.search(r'\b[a-z]{2}-', loc_lower):
        if not loc_lower.startswith("us-"):
             # It might be CA-ON (Canada), but check if it's just a weird format
             # Assume NON-US if we see XX- formatted prefix that isn't US-
             # Actually, "CA-" could be California if "US-CA-..." but typically "CA-ON" is Canada
             # Let's check strict non-US keywords
             pass

    non_us_keywords = [
        "canada", "france", "germany", "india", "poland", "uk", "united kingdom", 
        "london", "toronto", "vancouver", "montreal", "berlin", "munich", 
        "paris", "bangalore", "pune", "hyderabad", "delhi", "mumbai"
    ]
    
    for kw in non_us_keywords:
        if kw in loc_lower:
            is_us = False
            break
            
    # ISO Prefix strict check for non-US
    # e.g. "CA-ON" -> Canada
    if re.match(r'^(ca|in|fr|de|pl|gb|uk)-', loc_lower):
        is_us = False

    return {
        "raw": location_name,
        "city": None, # Parsing city/state specifically is hard without a db, leaving None for now or could approximate
        "state": None,
        "country_code": "US" if is_us else None,
        "is_us": is_us,
        "is_remote": is_remote
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
        # 1. Handle "X days ago" or "Posted X days ago"
        lower_date = date_string.lower()
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
