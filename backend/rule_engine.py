import logging

logger = logging.getLogger("RuleEngine")

class GFRComplianceEngine:
    def __init__(self):
        # In a full deployment, this connects to your local mplads_guardian.db
        pass

    def analyze_bill(self, extracted_data: dict) -> dict:
        logger.info("Initializing GFR Statutory Audit against VLM data...")
        
        flags = []
        risk_score = 0
        
        # 1. Forensic Visual Checks (Powered by Qwen2-VL Edge Vision)
        if not extracted_data.get("has_official_stamp"):
            flags.append("CRITICAL: Missing official government round seal/stamp.")
            risk_score += 40
            
        if not extracted_data.get("has_signature"):
            flags.append("CRITICAL: Missing authorized physical signature.")
            risk_score += 40
            
        # 2. Financial Sanction Cross-Reference
        expenditure = extracted_data.get("expenditure")
        estimate = extracted_data.get("amount_of_estimate")
        
        if expenditure and estimate:
            try:
                # Clean strings if necessary and convert to floats
                exp_val = float(str(expenditure).replace(',', ''))
                est_val = float(str(estimate).replace(',', ''))
                
                if exp_val > est_val:
                    overrun = exp_val - est_val
                    flags.append(f"VIOLATION: Actual expenditure exceeds sanctioned estimate by ₹{overrun:,.2f}.")
                    risk_score += 100
            except ValueError:
                flags.append("WARNING: Could not mathematically parse financial values for comparison.")
                risk_score += 20

        # Calculate final compliance status based on GFR 2017 rules
        status = "APPROVED"
        if risk_score > 0 and risk_score < 50:
            status = "FLAGGED FOR MANUAL REVIEW"
        elif risk_score >= 50:
            status = "REJECTED - STATUTORY VIOLATION"

        return {
            "compliance_status": status,
            "total_risk_score": min(risk_score, 100),
            "audit_flags": flags if flags else ["Document passes all visual and financial statutory checks."]
        }

rule_engine = GFRComplianceEngine()