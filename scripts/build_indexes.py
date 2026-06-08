# scripts/build_indexes.py
# Supply Chain Control Tower — SQLite Index Builder
# =============================================================================
#
# PURPOSE:
#   Adds database indexes to supply_chain.db to make queries faster.
#   Run this script ONCE after setting up the database.
#   Safe to run again — uses IF NOT EXISTS so it never duplicates indexes.
#
# WHAT IS AN INDEX?
#   Without index: SQLite reads every row to find sales_order_no = SO10001
#   With index:    SQLite jumps directly to that row instantly
#
#   With 10,000 rows:
#     Without index: ~10,000 comparisons per lookup
#     With index:    ~13 comparisons (log2 of 10,000)
#
# HOW TO RUN:
#   python scripts/build_indexes.py
#
# =============================================================================

import sys
import os
import sqlite3
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings_loader import get_database_path, get_project_root

DB_PATH = get_database_path()

# ─── Index definitions ────────────────────────────────────────────────────────
#
# Format: (index_name, table_name, column_name)
# Column names verified against actual database using check_columns.py
#
# WHY EACH COLUMN IS INDEXED:
#   sales_order_no  → primary lookup key used by almost every tool
#   order_status    → used to filter DELAYED / NEED_ACTION / SHIPPED
#   scheduled_pick_date → used to calculate how many days overdue
#   customer_name   → used in investigation and search tools
#   item_no         → primary key for inventory lookups
#   warehouse_id    → used to filter inventory/picks by warehouse location
#   backorder_flag  → used by get_backordered_items (Y/N filter)
#   supplier_id     → used by supplier performance and PO tools
#   po_status       → used to filter open vs closed purchase orders
#   carrier_id      → used by carrier performance summary tools
#   freight_status  → used by freight delay and hold tools
#   freight_hold_flag → used by get_freight_holds (Y/N filter)
#   pick_status     → used by get_delayed_picks
#   staffing_flag   → used by get_staffing_and_equipment_issues

INDEXES = [
    # ── shipments ─────────────────────────────────────────────────────────────
    # Verified columns: sales_order_no, order_status, scheduled_pick_date,
    #                   customer_name, freight_hold_flag, pick_status
    ("idx_shipments_order_no",        "shipments",       "sales_order_no"),
    ("idx_shipments_order_status",    "shipments",       "order_status"),
    ("idx_shipments_pick_date",       "shipments",       "scheduled_pick_date"),
    ("idx_shipments_customer",        "shipments",       "customer_name"),
    ("idx_shipments_freight_hold",    "shipments",       "freight_hold_flag"),
    ("idx_shipments_pick_status",     "shipments",       "pick_status"),

    # ── inventory ─────────────────────────────────────────────────────────────
    # Verified columns: item_no, warehouse_id, backorder_flag, supplier_id
    ("idx_inventory_item_no",         "inventory",       "item_no"),
    ("idx_inventory_warehouse_id",    "inventory",       "warehouse_id"),
    ("idx_inventory_backorder_flag",  "inventory",       "backorder_flag"),
    ("idx_inventory_supplier_id",     "inventory",       "supplier_id"),

    # ── purchase_orders ───────────────────────────────────────────────────────
    # Verified columns: po_number, item_no, supplier_id, po_status, warehouse_id
    # NOTE: purchase_orders has no sales_order_no column — po_number is the key
    ("idx_po_number",                 "purchase_orders", "po_number"),
    ("idx_po_item_no",                "purchase_orders", "item_no"),
    ("idx_po_supplier_id",            "purchase_orders", "supplier_id"),
    ("idx_po_status",                 "purchase_orders", "po_status"),
    ("idx_po_warehouse_id",           "purchase_orders", "warehouse_id"),

    # ── freight ───────────────────────────────────────────────────────────────
    # Verified columns: sales_order_no, carrier_id, freight_status,
    #                   freight_hold_flag
    ("idx_freight_order_no",          "freight",         "sales_order_no"),
    ("idx_freight_carrier_id",        "freight",         "carrier_id"),
    ("idx_freight_status",            "freight",         "freight_status"),
    ("idx_freight_hold_flag",         "freight",         "freight_hold_flag"),

    # ── warehouse_picks ───────────────────────────────────────────────────────
    # Verified columns: sales_order_no, warehouse_id, pick_status,
    #                   staffing_flag, item_no
    ("idx_warehouse_order_no",        "warehouse_picks", "sales_order_no"),
    ("idx_warehouse_id",              "warehouse_picks", "warehouse_id"),
    ("idx_warehouse_pick_status",     "warehouse_picks", "pick_status"),
    ("idx_warehouse_staffing_flag",   "warehouse_picks", "staffing_flag"),
    ("idx_warehouse_item_no",         "warehouse_picks", "item_no"),
]


def get_existing_tables(conn):
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cursor.fetchall()]


def mark_indexes_built():
    """Updates indexes_built: false → true in settings.yaml"""
    settings_path = os.path.join(get_project_root(), "config", "settings.yaml")
    with open(settings_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "indexes_built: false" in content:
        content = content.replace("indexes_built: false", "indexes_built: true")
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("  settings.yaml updated: indexes_built → true")
    elif "indexes_built: true" in content:
        print("  settings.yaml already shows indexes_built: true")
    else:
        print("  WARNING: indexes_built flag not found in settings.yaml")
        print("           Please manually set: indexes_built: true")


def build_indexes():
    print("=" * 60)
    print("Supply Chain Control Tower — Index Builder")
    print("=" * 60)
    print(f"\nDatabase: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print(f"\nERROR: Database not found at: {DB_PATH}")
        print("Run: python scripts/csv_to_sqlite.py first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    existing_tables = get_existing_tables(conn)
    print(f"Tables found: {', '.join(sorted(existing_tables))}")
    print(f"\nCreating {len(INDEXES)} indexes...\n")

    created = []
    skipped = []
    errors  = []

    for index_name, table_name, column_name in INDEXES:

        # Skip if table doesn't exist
        if table_name not in existing_tables:
            skipped.append((index_name, table_name))
            print(f"  SKIP    {index_name:<48} (table '{table_name}' not found)")
            continue

        # Verify column exists in this table before indexing
        cols = conn.execute(f"PRAGMA table_info([{table_name}])").fetchall()
        col_names = [c[1] for c in cols]
        if column_name not in col_names:
            skipped.append((index_name, table_name))
            print(f"  SKIP    {index_name:<48} (column '{column_name}' not in {table_name})")
            continue

        sql = (
            f"CREATE INDEX IF NOT EXISTS {index_name} "
            f"ON [{table_name}] ([{column_name}])"
        )

        try:
            start = time.time()
            conn.execute(sql)
            conn.commit()
            ms = (time.time() - start) * 1000
            created.append(index_name)
            print(f"  OK      {index_name:<48} ({ms:.1f}ms)")
        except sqlite3.Error as e:
            errors.append((index_name, str(e)))
            print(f"  ERROR   {index_name:<48} → {e}")

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"  Created : {len(created)}")
    print(f"  Skipped : {len(skipped)}")
    print(f"  Errors  : {len(errors)}")

    if skipped:
        print("\n  Skipped (column or table mismatch):")
        for name, table in skipped:
            print(f"    - {name} on {table}")

    if errors:
        print("\n  Errors:")
        for name, err in errors:
            print(f"    - {name}: {err}")

    # Verify final count
    all_idx = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
    ).fetchall()
    print(f"\n  Total supply chain indexes in database: {len(all_idx)}")
    conn.close()

    # Update settings.yaml
    if len(errors) == 0:
        print("\nUpdating settings.yaml...")
        mark_indexes_built()
        print("\nDone. All indexes built successfully.")
    else:
        print(f"\nWARNING: {len(errors)} error(s). Fix and re-run.")

    print("=" * 60)


if __name__ == "__main__":
    build_indexes()