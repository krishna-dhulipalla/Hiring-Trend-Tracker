# Hard negative keywords - instantly reject if these appear as whole words
HARD_NEGATIVES = {
    # Level/early-career noise
    "intern", "internship", "co-op", "campus", "apprentice", "fellowship", "graduate", "grad",
    
    # Non-engineering functions
    "recruiter", "recruiting", "talent", "hr", "sales", "marketing", "growth", 
    "customer", "support", "operations", "finance", "accounting", "legal",
    "business", "coordinator", "assistant", "manager", "head", "chief", "director", "vp", "principal"
}

# Abbreviation / expansion map
ABBREVIATIONS = {
    "swe": "software engineer",
    "sde": "software engineer",
    "mle": "machine learning engineer",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "ds": "data scientist",
    "sre": "site reliability engineer",
    "qa": "quality assurance",
    "sdet": "software development engineer in test",
    "cv": "computer vision",
    "rl": "reinforcement learning",
    "llm": "llm",
    "mlops": "ml ops",
    "r&d": "research"
}

# Special tokens to protect from fuzzy matching (optional, for future use)
SPECIAL_TOKENS = {
    "learning", "engineer", "scientist", "platform", "backend", "frontend", "fullstack", "data"
}

# Role Families
# Each family has:
# - core: strong keywords that give high score
# - roles: role descriptors (engineer, scientist, etc.)
# - synonyms: specific phrases that map to this family
ROLE_FAMILIES = {
    "ml_ai": {
        "core": [
            "machine learning", "artificial intelligence", "deep learning", "computer vision", "nlp", 
            "generative ai", "llm", "model", "foundation model", "gen ai", "genai", "multimodal", 
            "rl", "reinforcement learning", "cv"
        ],
        "roles": ["engineer", "scientist", "researcher", "applied scientist"],
        "strong_phrases": [
            "machine learning engineer", "data scientist", "applied scientist", "ai engineer", 
            "research engineer", "research scientist", "ml scientist", "applied ml scientist", 
            "ml ops engineer", "ml platform engineer", "gen ai engineer", "llm engineer", 
            "founding engineer"
        ]
    },
    "data": {
        "core": ["data", "analytics", "pipeline", "etl"],
        "roles": ["engineer", "platform", "infrastructure"],
        "strong_phrases": ["data engineer", "analytics engineer", "data platform engineer"]
    },
    "swe_backend": {
        "core": ["software", "backend", "frontend", "fullstack", "web", "distributed systems", "api"],
        "roles": ["engineer", "developer"],
        "strong_phrases": ["software engineer", "backend engineer", "platform engineer", "full stack engineer"]
    },
    "infra_devops": {
        "core": ["infrastructure", "devops", "site reliability", "cloud", "platform", "reliability"],
        "roles": ["engineer"],
        "strong_phrases": ["site reliability engineer", "devops engineer", "infrastructure engineer", "platform engineer"]
    }
}
