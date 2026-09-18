import logging
from fuzzywuzzy import process
from backend.models import ExtractedBillData, GFRComplianceReport, BillLineItem
from backend.database import get_vendor_historical_velocity, check_vendor_registration

logger = logging.getLogger("Rule_Engine")

# Master standard price ontology (Estimated standard regional rates per unit in ₹)
REGIONAL_PRICE_BENCHMARKS = {
    "Brick": 9.0,        # Standard: ₹8 - ₹10 per piece
    "Cement": 380.0,     # Standard: ₹350 - ₹420 per 50kg bag
    "Sand": 45.0,        # Standard: ₹40 - ₹55 per cu.ft
    "Steel": 65.0,       # Standard: ₹60 - ₹75 per kg
    "Gravel": 35.0,      # Standard: ₹30 - ₹45 per cu.ft
    "Tiles": 40.0,       # Standard: ₹35 - ₹60 per sq.ft
    "Paint": 280.0,      # Standard: ₹250 - ₹350 per liter
    "Pipes": 120.0,      # Standard: ₹100 - ₹160 per meter
    "Labor": 500.0       # Standard daily wage rate
}

def standardize_inventory_and_audit_prices(line_items: list[BillLineItem]) -> tuple[list[BillLineItem], list[str]]:
    """
    1. Maps vernacular/local item names to standardized ontology using FuzzyWuzzy.
    2. Flags severe price gouging against regional rate benchmarks.
    """
    pricing_flags = []
    ontology_keys = list(REGIONAL_PRICE_BENCHMARKS.keys())

    for item in line_items:
        best_match, score = process.extractOne(item.item_description, ontology_keys)
        
        if score >= 65:
            item.standardized_item = best_match
            benchmark_price = REGIONAL_PRICE_BENCHMARKS[best_match]
            
            # Flag if claimed price is more than 80% higher than benchmark
            if item.unit_price > benchmark_price * 1.8:
                pricing_flags.append(
                    f"Price Gouging Alert: '{item.item_description}' billed at ₹{item.unit_price:.2f}/unit (Benchmark: ₹{benchmark_price:.2f})"
                )
        else:
            item.standardized_item = "Unclassified Material"
            
    return line_items, pricing_flags


def evaluate_gfr_154_compliance(extracted_data: ExtractedBillData) -> GFRComplianceReport:
    """
    Advanced Multi-Parameter Anomaly Engine:
    - GFR 154 Statutory Threshold & Near-Threshold Evasion Checks
    - 30-Day Rolling Smurfing/Velocity Verification
    - Ghost / Unregistered Vendor Cross-Referencing
    - Item Unit-Price Variance Audit
    - OCR Confidence / Tampering Check
    """
    logger.info(f"Auditing transaction for Vendor: {extracted_data.vendor_name}")

    flags = []
    risk_score = 10  # Baseline low risk

    # 1. Standardize items and audit unit prices
    extracted_data.line_items, price_flags = standardize_inventory_and_audit_prices(extracted_data.line_items)
    flags.extend(price_flags)
    if price_flags:
        risk_score += len(price_flags) * 15

    # 2. GFR Rule 154 Direct Procurement Limits
    total = extracted_data.total_amount
    if total >= 50000.0:
        flags.append(f"Hard Violation: Invoice amount ₹{total:,.2f} breaches the ₹50,000 statutory GFR 154 limit.")
        risk_score += 50
    elif 45000.0 <= total <= 49999.99:
        flags.append(f"Evasion Alert: Amount ₹{total:,.2f} is clustered near the ₹50,000 threshold (Possible intentional limit evasion).")
        risk_score += 30

    # 3. 30-Day Velocity / Smurfing Audit across District Ledger
    velocity_30d = get_vendor_historical_velocity(extracted_data.vendor_name, extracted_data.bill_date)
    if velocity_30d + total > 50000.0:
        flags.append(f"Smurfing Alert: Vendor 30-day cumulative disbursements reach ₹{(velocity_30d + total):,.2f}, bypassing quotation rules.")
        risk_score += 35

    # 4. Ghost Vendor Cross-Reference
    is_registered = check_vendor_registration(extracted_data.vendor_name)
    if not is_registered:
        flags.append(f"Unverified Vendor: '{extracted_data.vendor_name}' does not appear in historical e-Sakshi disbursements.")
        risk_score += 20

    # 5. Low-Confidence / Tamper Heuristic
    if extracted_data.overall_confidence < 0.70:
        flags.append("Document Integrity Alert: Low OCR text confidence indicates potential manual overwriting or illegible receipt.")
        risk_score += 15

    # Cap risk score between 0 and 100
    final_risk_score = min(max(risk_score, 0), 100)

    # Classify Risk Tier
    if final_risk_score >= 70:
        risk_level = "High"
    elif final_risk_score >= 35:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return GFRComplianceReport(
        risk_score=final_risk_score,
        risk_level=risk_level,
        flags=flags,
        vendor_30d_velocity=velocity_30d,
        is_registered_vendor=is_registered
    )