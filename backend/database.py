import sqlite3
import pandas as pd
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("Database")

# Dynamically resolve paths so it works regardless of where you run the server
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "mplads_guardian.db")

def init_db():
    """Reads the e-Sakshi CSVs and builds a relational SQLite database for real-time querying."""
    logger.info("Initializing SQLite Database from e-Sakshi CSVs...")
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Load core CSVs
        expenditure_path = os.path.join(DATA_DIR, "expenditure.csv")
        sanctioned_path = os.path.join(DATA_DIR, "works_sanctioned.csv")
        
        if os.path.exists(expenditure_path):
            df_exp = pd.read_csv(expenditure_path)
            # Ensure dates are properly parsed for SQL querying
            df_exp['Expenditure Date'] = pd.to_datetime(df_exp['Expenditure Date'], format='%d-%b-%Y', errors='coerce')
            df_exp.to_sql("expenditure", conn, if_exists="replace", index=False)
            
        if os.path.exists(sanctioned_path):
            df_sanc = pd.read_csv(sanctioned_path)
            df_sanc.to_sql("works_sanctioned", conn, if_exists="replace", index=False)
            
        logger.info("Database successfully built and populated.")
    except Exception as e:
        logger.error(f"Failed to load CSVs into database: {e}")
    finally:
        conn.close()

def get_vendor_historical_velocity(vendor_name: str, bill_date_str: str) -> float:
    """Calculates the total amount paid to a vendor across all projects within 30 days prior to the bill date (Smurfing Check)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        bill_date = datetime.strptime(bill_date_str, "%Y-%m-%d")
        thirty_days_ago = bill_date - timedelta(days=30)
        
        # We use LIKE for fuzzy SQL matching to catch slight misspellings
        query = """
            SELECT SUM("Fund Disbursed Amount ( ₹ )") 
            FROM expenditure 
            WHERE "Vendor Name" LIKE ? 
            AND "Expenditure Date" BETWEEN ? AND ?
        """
        cursor.execute(query, (f"%{vendor_name}%", thirty_days_ago.strftime("%Y-%m-%d %H:%M:%S"), bill_date.strftime("%Y-%m-%d %H:%M:%S")))
        result = cursor.fetchone()[0]
        
        return float(result) if result else 0.0
    except Exception as e:
        logger.error(f"Velocity check failed: {e}")
        return 0.0
    finally:
        conn.close()

def check_vendor_registration(vendor_name: str) -> bool:
    """Checks if the vendor has ever been officially used in the district ledger (Ghost Vendor Check)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = 'SELECT COUNT(*) FROM expenditure WHERE LOWER("Vendor Name") LIKE LOWER(?)'
    cursor.execute(query, (f"%{vendor_name}%",))
    count = cursor.fetchone()[0]
    conn.close()
    
    return count > 0

# Initialize the database the first time this module is imported
if not os.path.exists(DB_PATH):
    init_db()