# /sc-inventory
# Supply Chain Control Tower — Inventory Status Command
# ======================================================

## What This Command Does

Returns a full inventory health summary across all items and warehouses.
Identifies stockouts, critical items, backorders, and items approaching
reorder point.

## When To Use

- When someone asks about stock levels
- Before raising purchase orders
- When investigating whether inventory is causing shipment delays

## Output Format

**Inventory Health Summary — [date]**

**Overall Status:** HEALTHY / AT RISK / CRITICAL

**Counts by Status**
- Healthy / Low / Critical / Out of stock / On backorder

**Items Requiring Attention**
- Item number, description, warehouse, current stock, status, recommended action

**Backorder Impact**
- Orders affected by inventory shortages

**Summary**
- Plain-English paragraph describing current inventory health
