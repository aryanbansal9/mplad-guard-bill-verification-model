import sqlite3
import os
import re
import logging
from difflib import SequenceMatcher

logger = logging.getLogger("RuleEngine")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "mplads_guardian.db")

class GFRComplianceEngine:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _get_db_connection(self):
        if not os.path.exists(self.db_path):
            logger.warning(f"Database not found at {self.db_path}. Database checks will be bypassed.")
            return None
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _clean_number(self, value) -> float:
        if value is None:
            return 0.0
        cleaned = re.sub(r"[^\d.]", "", str(value))
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _fuzzy_similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

    def cross_verify_with_database(self, name_of_work: str, claimed_amount: float) -> dict:
        """Cross-checks document details against ingested e-Sakshi records."""
        conn = self._get_db_connection()
        if not conn:
            return {"db_verified": False, "flags": ["Database unavailable for cross-verification."], "risk": 10}

        flags = []
        risk = 0
        matched_record = None
        max_ratio = 0.0

        try:
            cursor = conn.cursor()
            # Fetch sanctioned works from e-Sakshi data
            cursor.execute("SELECT name_of_work, sanctioned_amount, work_status FROM works_sanctioned LIMIT 500")
            rows = cursor.fetchall()

            for row in rows:
                ratio = self._fuzzy_similarity(name_of_work, row["name_of_work"])
                if ratio > max_ratio:
                    max_ratio = ratio
                    matched_record = row

            if max_ratio < 0.65:
                flags.append(f"HIGH RISK: Work title does not match any officially sanctioned project in e-Sakshi (Match confidence: {max_ratio:.0%}).")
                risk += 60
            else:
                official_budget = self._clean_number(matched_record["sanctioned_amount"])
                if official_budget > 0 and claimed_amount > official_budget:
                    overrun = claimed_amount - official_budget
                    flags.append(f"CRITICAL: Claimed expenditure exceeds official government sanctioned budget by ₹{overrun:,.2f}.")
                    risk += 80

                if matched_record["work_status"] and matched_record["work_status"].lower() == "completed":
                    flags.append("POTENTIAL FRAUD: Work is already marked as completed and disbursed in e-Sakshi records (Duplicate claim).")
                    risk += 75

        except Exception as e:
            logger.error(f"Error querying SQLite database: {e}")
            flags.append(f"DB Query Warning: {str(e)}")
        finally:
            conn.close()

        return {
            "db_verified": max_ratio >= 0.65,
            "match_confidence": round(max_ratio, 2),
            "matched_work": matched_record["name_of_work"] if matched_record and max_ratio >= 0.65 else None,
            "flags": flags,
            "risk": risk
        }

    def analyze_bill(self, extracted_data: dict) -> dict:
        logger.info("Initializing comprehensive statutory and forensic audit...")
        
        flags = []
        risk_score = 0

        # 1. Forensic Visual Checks (Stamp & Signature)
        if not extracted_data.get("has_official_stamp"):
            flags.append("CRITICAL: Missing official government round seal/stamp.")
            risk_score += 40

        if not extracted_data.get("has_signature"):
            flags.append("CRITICAL: Missing authorized physical signature.")
            risk_score += 40

        # 2. Arithmetic Document Sanity Check
        exp_val = self._clean_number(extracted_data.get("expenditure"))
        est_val = self._clean_number(extracted_data.get("amount_of_estimate"))

        if exp_val > 0 and est_val > 0 and exp_val > est_val:
            overrun = exp_val - est_val
            flags.append(f"VIOLATION: Actual expenditure exceeds estimated amount by ₹{overrun:,.2f}.")
            risk_score += 50

        # --- NEW: GSTIN Cryptographic Format Check ---
        gstin = extracted_data.get("vendor_gstin")
        if gstin and str(gstin).lower() != "null":
            # Validates Indian GSTIN structure (2 digits, 5 letters, 4 digits, 1 letter, 1 alphanumeric, Z, 1 alphanumeric)
            gstin_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
            if not re.match(gstin_pattern, str(gstin).upper()):
                flags.append(f"CRITICAL FRAUD: Invalid GSTIN format detected ({gstin}). Potential shell company.")
                risk_score += 85

        # --- NEW: Tax Math Anomaly Detection ---
        base = self._clean_number(extracted_data.get("base_amount"))
        cgst = self._clean_number(extracted_data.get("cgst_amount"))
        sgst = self._clean_number(extracted_data.get("sgst_amount"))
        igst = self._clean_number(extracted_data.get("igst_amount"))
        total = self._clean_number(extracted_data.get("total_billed_amount"))

        if total > 0:
            calculated_tax = cgst + sgst + igst
            calculated_total = base + calculated_tax
            
            # Allow a small float tolerance of 2 rupees for rounding discrepancies
            if abs(total - calculated_total) > 2.0:
                flags.append(f"FINANCIAL ANOMALY: Tax math mismatch. Base ({base}) + Taxes ({calculated_tax}) does not equal Total Billed ({total}).")
                risk_score += 70

        # --- NEW: Digital / Physical Authentication ---
        if not extracted_data.get("has_physical_signature") and not extracted_data.get("has_digital_signature"):
            flags.append("VIOLATION: Document lacks both physical and digital authorization signatures.")
            risk_score += 50

        # 3. e-Sakshi Ground Truth Cross-Verification
        name_of_work = extracted_data.get("name_of_work", "")
        db_audit = self.cross_verify_with_database(name_of_work, exp_val)
        
        flags.extend(db_audit.get("flags", []))
        risk_score += db_audit.get("risk", 0)

        # 4. Final Risk Classification
        total_risk = min(risk_score, 100)
        if total_risk == 0:
            status = "APPROVED"
        elif total_risk < 50:
            status = "FLAGGED FOR MANUAL REVIEW"
        else:
            status = "REJECTED - STATUTORY VIOLATION"

        return {
            "compliance_status": status,
            "total_risk_score": total_risk,
            "e_sakshi_match": {
                "matched_project": db_audit.get("matched_work"),
                "confidence": db_audit.get("match_confidence")
            },
            "audit_flags": flags if flags else ["Document passes all visual, mathematical, and database checks."]
        }

rule_engine = GFRComplianceEngine()