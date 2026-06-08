# /sc-warehouse
# Supply Chain Control Tower — Warehouse Operations Command
# =========================================================

## What This Command Does

Returns a warehouse operations summary across all active pick tasks.
Identifies delayed picks, staffing issues, equipment problems, and
warehouse zones at risk of missing shipment windows.

## When To Use

- When warehouse delays are causing shipment issues
- During peak periods when pick capacity is under pressure
- When investigating warehouse-related root causes

## Output Format

**Warehouse Operations Summary — [date]**

**Overall Pick Health:** ON TRACK / AT RISK / DELAYED

**Pick Status by Warehouse**
- Warehouse name, total picks, completed, in progress, delayed

**At-Risk Picks**
- Pick ID, order, item, zone, delay reason, assigned picker

**Staffing and Equipment Issues**
- Active flags affecting pick performance

**Summary**
- Plain-English paragraph describing current warehouse health
