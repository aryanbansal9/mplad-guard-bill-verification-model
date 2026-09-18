import logging
from fuzzywuzzy import process
from backend.models import ExtractedBillData, GFRComplianceReport, BillLineItem
from backend.database import get_vendor_frequency

logger = logging.getLogger("Rule_Engine")

# Master ontology for public works (Standardizing local terminology)
MASTER_ITEM_ONTOLOGY = [
    "Brick", "Cement", "Sand", "Steel", "Gravel", "Tiles", "Paint", "Pipes", "Labor", "Wood"
]

def standardize_inventory(line_items: list[BillLineItem]) -> list[BillLineItem]:
    """Maps local Hindi/English terms (e.g., 'Eent') to standard terms (e.g., 'Brick') using Fuzzy Matching."""
    for item in line_items:
        # Extract the best match from our master list
        best_match, score = process.extractOne(item.item_description, MASTER_ITEM_ONTOLOGY)
        
        if score >= 70:  # 70% similarity threshold
            item.standardized_item = best_match
        else:
            item.standardized_item = "Unclassified"
            
    return line_items

def evaluate_gfr_154_compliance(extracted_data: ExtractedBillData) -> GFRComplianceReport:
    """
    The core anomaly detection engine for GFR Rule 154.
    Rule 154 allows direct purchases up to ₹50,000 without quotations. 
    Corrupt actors often make handmade bills for ₹49,999 to bypass this.
    """
    logger.info(f"Evaluating GFR 154 compliance for vendor: {extracted_data.vendor_name}")
    
    is_compliant = True
    flags = []
    confidence = 0.95
    
    # 1. Statutory Threshold Check (The ₹50,000 limit)
    total = extracted_data.total_amount
    if total >= 50000:
        is_compliant = False
        flags.append(f"Hard Violation: Amount ₹{total} exceeds the ₹50,000 GFR 154 limit for direct purchases.")
    elif 45000 <= total <= 49999.99:
        # Suspiciously close to the limit (Classic evasion tactic)
        is_compliant = False
        flags.append(f"Evasion Alert: Amount ₹{total} is suspiciously close to the ₹50,000 limit.")
        confidence = 0.88 # Lower confidence because it's technically legal, but behaviorally suspicious
        
    # 2. Vendor Frequency Check (Smurfing / Bill Splitting detection)
    vendor_count = get_vendor_frequency(extracted_data.vendor_name)
    
    # If this is the vendor's first time, we add 1 to simulate this current bill
    if vendor_count == 0:
        vendor_count = 1
        
    if vendor_count >= 3:
        is_compliant = False
        flags.append(f"Frequency Alert: Vendor used {vendor_count} times in recent projects. Possible bill splitting.")
        confidence = 0.92

    # Compile the final flag reason
    flag_reason = " | ".join(flags) if flags else None

    return GFRComplianceReport(
        is_compliant=is_compliant,
        flag_reason=flag_reason,
        vendor_frequency_count=vendor_count,
        confidence_score=confidence
    )