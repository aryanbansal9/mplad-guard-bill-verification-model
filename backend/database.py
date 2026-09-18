# Mock database for hackathon POC
# In a production environment, this queries the District e-Sakshi DB.

VENDOR_HISTORY_DB = {
    "shri ram building materials": 5, # Highly used (Suspicious)
    "gupta cement store": 1,
    "sharma bricks": 3,
    "m/s agarwal traders": 0,
    "eent udyog": 4
}

def get_vendor_frequency(vendor_name: str) -> int:
    """Returns the number of prior transactions for a given vendor in the district."""
    # Convert to lowercase to ensure matching works regardless of LLM capitalization
    return VENDOR_HISTORY_DB.get(vendor_name.lower(), 0)