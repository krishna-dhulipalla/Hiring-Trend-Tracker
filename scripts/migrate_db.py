import sqlite3
import os

DB_PATH = "news.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        print("Migrating database found at", DB_PATH)
        # Check if column exists
        c.execute("PRAGMA table_info(normalized_news)")
        columns = [info[1] for info in c.fetchall()]
        
        if "company_name" not in columns:
            print("Adding company_name column to normalized_news table...")
            c.execute("ALTER TABLE normalized_news ADD COLUMN company_name TEXT")
            conn.commit()
            print("Migration successful: company_name column added.")
        else:
            print("Migration skipped: company_name column already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
