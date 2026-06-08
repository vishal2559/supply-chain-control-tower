from pathlib import Path
import sqlite3

DB_PATH = Path("data/supply_chain.db")

if not DB_PATH.exists():
    print(f"Database file not found: {DB_PATH}")
    print("Run the database setup scripts before using CI features.")
else:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name LIKE 'ci_%'
                ORDER BY name
            """)

            tables = cursor.fetchall()

            if tables:
                print("CI tables found:")
                for table in tables:
                    print(f"  OK - {table[0]}")
            else:
                print("No CI tables found. Run the setup scripts before using CI features.")

    except sqlite3.Error as error:
        print(f"Database check failed: {error}")
