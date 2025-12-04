import re
import difflib
from src.config import HARD_NEGATIVES, ABBREVIATIONS, ROLE_FAMILIES, SPECIAL_TOKENS

def parse_location(location_name):
    """
    Parses a location string into a dictionary with country, state, city, remote status.
    Conservative rules:
    - Detects 'Remote' variants.
    - Detects 'United States', 'USA', 'US'.
    - Detects state abbreviations (CA, NY, TX, etc.).
    """
    if not location_name:
        return {"raw": None, "is_remote": False, "is_us": False}

    loc_lower = location_name.lower()
    
    # Remote detection
    is_remote = "remote" in loc_lower
    
    # US detection
    is_us = False
    if any(x in loc_lower for x in ["united states", "usa", "us"]) or \
       re.search(r'\b(us)\b', loc_lower):
        is_us = True
    
    # State detection (abbreviations and full names)
    us_states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", 
                 "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", 
                 "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", 
                 "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", 
                 "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
                 "DC"]
                 
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
    
    found_state = None
    for state in us_states:
        # Check for ", CA" or " CA " or start/end of string
        if re.search(r'\b' + state + r'\b', location_name):
            found_state = state
            is_us = True
            break
            
    if not is_us:
        for state in full_state_names:
            if state in loc_lower:
                is_us = True
                break
            
    return {
        "raw": location_name,
        "is_remote": is_remote,
        "is_us": is_us,
        "state": found_state
    }

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
