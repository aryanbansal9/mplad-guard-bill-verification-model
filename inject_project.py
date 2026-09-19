import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "mplads_guardian.db")

def inject_golden_record():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    project_name = "Construction of building for Kadamar-Idodu Tribal LPS in Kulathupuzhuppu"
    budget = 60000000  # 6 Crores (higher than the 5 Crore bill)
    
    try:
        # Check available columns
        cursor.execute("PRAGMA table_info(works_sanctioned)")
        cols = [row[1].lower() for row in cursor.fetchall()]
        
        work_col = next((c for c in cols if "work" in c or "name" in c), "name_of_work")
        amount_col = next((c for c in cols if "amount" in c or "sanction" in c), "sanctioned_amount")
        status_col = next((c for c in cols if "status" in c), "work_status")

        # ADDED DOUBLE QUOTES AROUND COLUMN NAMES TO FIX SYNTAX ERROR
        query = f"""
            INSERT INTO works_sanctioned ("{work_col}", "{amount_col}", "{status_col}") 
            VALUES (?, ?, 'IN_PROGRESS')
        """
        cursor.execute(query, (project_name, budget))
        conn.commit()
        print(f"✅ Successfully injected '{project_name}' into local SQLite database!")
        
    except Exception as e:
        print(f"❌ Database Injection Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inject_golden_record()