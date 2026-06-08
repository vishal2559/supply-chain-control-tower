from pathlib import Path
import sqlite3

# Path to the local demo SQLite database.
DB_PATH = Path("data/supply_chain.db")

# Check if the database file exists before connecting.
# This prevents SQLite from silently creating a new empty database.
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
