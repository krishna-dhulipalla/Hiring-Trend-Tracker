import re
from src.config import TARGET_TITLES, EXCLUDE_TITLES

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

def title_matches(title):
    """
    Returns True if title matches TARGET_TITLES and does NOT match EXCLUDE_TITLES.
    Uses word boundaries for robust matching.
    """
    if not title:
        return False
        
    title_lower = title.lower()
    
    # Check exclusions first
    for exclude in EXCLUDE_TITLES:
        # \b pattern \b
        if re.search(r'\b' + re.escape(exclude) + r'\b', title_lower):
            return False
            
    # Check inclusions
    for target in TARGET_TITLES:
        if re.search(r'\b' + re.escape(target) + r'\b', title_lower):
            return True
            
    return False
