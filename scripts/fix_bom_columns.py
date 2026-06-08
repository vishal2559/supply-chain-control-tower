# scripts/fix_bom_columns.py
# Supply Chain Control Tower — BOM Character Fix
# =============================================================================
#
# PURPOSE:
#   Fixes a hidden character issue in the shipments table.
#
# WHAT IS A BOM?
#   BOM stands for "Byte Order Mark". It is an invisible Unicode character
#   \ufeff that some programs (like Excel) add to the very start of a CSV file.
#   When the CSV is loaded into SQLite, this character becomes part of the
#   first column name: "\ufeffsales_order_no" instead of "sales_order_no".
#
# WHY THIS IS A PROBLEM:
#   Your Python tools do: row.get("sales_order_no")
#   The database stores:  "\ufeffsales_order_no"
#   These don't match → every order lookup silently returns empty/not found.
#
# WHAT THIS SCRIPT DOES:
#   1. Detects any BOM-prefixed columns in the shipments table
#   2. Rebuilds the table with clean column names
#   3. Copies all data across — no data is lost
#   4. Drops the old table and renames the clean one
#
# HOW TO RUN (one time only):
#   python scripts/fix_bom_columns.py
#
# =============================================================================

import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings_loader import get_database_path

DB_PATH = get_database_path()

# Tables to check for BOM characters
# We check all 5 operational tables — BOM only affects the first column
# of each CSV, which is always the first column of the table.
TABLES_TO_CHECK = [
    "shipments",
    "inventory",
    "purchase_orders",
    "freight",
    "warehouse_picks",
]


def has_bom(text: str) -> bool:
    """Returns True if the string starts with the BOM character \ufeff"""
    return text.startswith('\ufeff')


def clean_column_name(name: str) -> str:
    """Removes BOM character from the start of a column name if present."""
    return name.lstrip('\ufeff')


def fix_table_bom(conn: sqlite3.Connection, table_name: str) -> bool:
    """
    Checks one table for BOM-prefixed column names.
    If found, rebuilds the table with clean names.

    Returns True if a fix was applied, False if table was already clean.
    """
    # Get current column info: (cid, name, type, notnull, default, pk)
    cols = conn.execute(f"PRAGMA table_info([{table_name}])").fetchall()

    # Check if any column has a BOM prefix
    bom_cols = [(c[1], clean_column_name(c[1])) for c in cols if has_bom(c[1])]

    if not bom_cols:
        print(f"  {table_name:<20} Clean — no BOM characters found")
        return False

    # Report what we found
    for dirty, clean in bom_cols:
        print(f"  {table_name:<20} BOM found: {repr(dirty)} → will rename to '{clean}'")

    # Build the clean column list for CREATE TABLE
    # We keep all column types as TEXT (matching original schema)
    clean_col_defs = ", ".join(
        f"[{clean_column_name(c[1])}] {c[2]}" for c in cols
    )

    # Build SELECT with clean aliases for copying data
    # For BOM columns: SELECT [﻿sales_order_no] AS [sales_order_no]
    # For clean columns: SELECT [order_status]
    select_parts = []
    for c in cols:
        col_name = c[1]
        clean_name = clean_column_name(col_name)
        if col_name != clean_name:
            # BOM column — alias it to the clean name
            select_parts.append(f"[{col_name}] AS [{clean_name}]")
        else:
            select_parts.append(f"[{col_name}]")
    select_cols = ", ".join(select_parts)

    temp_table = f"{table_name}_clean_temp"

    try:
        # Step 1: Create a new clean table
        conn.execute(f"CREATE TABLE [{temp_table}] ({clean_col_defs})")

        # Step 2: Copy all data from old table to new table with clean names
        conn.execute(
            f"INSERT INTO [{temp_table}] SELECT {select_cols} FROM [{table_name}]"
        )

        # Step 3: Count rows to verify no data was lost
        old_count = conn.execute(f"SELECT COUNT(*) FROM [{table_name}]").fetchone()[0]
        new_count = conn.execute(f"SELECT COUNT(*) FROM [{temp_table}]").fetchone()[0]

        if old_count != new_count:
            # Safety check — if row counts differ, abort and don't commit
            conn.execute(f"DROP TABLE [{temp_table}]")
            print(f"  ERROR: Row count mismatch ({old_count} → {new_count}). Aborting.")
            return False

        # Step 4: Drop old table and rename clean table to original name
        conn.execute(f"DROP TABLE [{table_name}]")
        conn.execute(f"ALTER TABLE [{temp_table}] RENAME TO [{table_name}]")
        conn.commit()

        print(f"  {table_name:<20} Fixed — {new_count} rows preserved, column names cleaned")
        return True

    except sqlite3.Error as e:
        # If anything goes wrong, try to clean up the temp table
        try:
            conn.execute(f"DROP TABLE IF EXISTS [{temp_table}]")
            conn.commit()
        except Exception:
            pass
        print(f"  ERROR fixing {table_name}: {e}")
        return False


def fix_all_tables():
    """
    Checks all 5 operational tables for BOM characters and fixes any found.
    """
    print("=" * 60)
    print("Supply Chain Control Tower — BOM Column Fix")
    print("=" * 60)
    print(f"\nDatabase: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print(f"\nERROR: Database not found at: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    # Get tables that actually exist
    existing = [
        r[0] for r in
        conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    ]

    print("\nChecking columns for BOM characters...\n")

    fixed_count = 0
    for table in TABLES_TO_CHECK:
        if table not in existing:
            print(f"  {table:<20} Skipped — table not found")
            continue
        was_fixed = fix_table_bom(conn, table)
        if was_fixed:
            fixed_count += 1

    conn.close()

    print(f"\n{'=' * 60}")
    if fixed_count > 0:
        print(f"Fixed {fixed_count} table(s).")
        print("\nIMPORTANT: Existing indexes on fixed tables were dropped")
        print("when the table was rebuilt. Run this next:")
        print("  python scripts/build_indexes.py")
    else:
        print("All tables already clean — no fixes needed.")
    print("=" * 60)


if __name__ == "__main__":
    fix_all_tables()
