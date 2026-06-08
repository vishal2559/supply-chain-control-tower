# ================================================================
# SANITIZED SLASH COMMAND FILES
# Supply Chain Control Tower
# Paste each section into its corresponding file on GitHub
# ================================================================


# ── FILE 1: sc-briefing.md ──────────────────────────────────────


# /sc-briefing
# Supply Chain Control Tower — Morning Briefing Command
# ======================================================

## What This Command Does

Runs a full morning briefing across the supply chain system.
Combines shipment delay analysis with cross-domain health monitoring
to give a complete operational picture in one response.

## When To Use

- Every morning before your standup
- Any time you need a quick full-system status check
- When someone asks "what does today look like?"

## Output Format

### 🏭 Supply Chain Morning Briefing — [date]

**Overall Risk Level:** LOW / MEDIUM / HIGH / CRITICAL

**Shipment Summary**
- Total orders tracked
- On time / Delayed / Need action / Shipped counts

**Top Delay Reasons**
- Ranked list of root causes across all delayed orders

**Most Urgent Order**
- Order number, customer, days overdue, recommended action
- Or: No orders require immediate escalation today

**Cross-Domain Health**
- Inventory risk count
- Freight problem count
- Warehouse pick delays
- Multi-domain risk orders

**Briefing Summary**
- Plain-English paragraph summarising today's supply chain health


# ── FILE 2: sc-investigate.md ──────────────────────────────────


# /sc-investigate
# Supply Chain Control Tower — Order Investigation Command
# =========================================================

## What This Command Does

Runs a full root-cause investigation for a specific order.
Pulls data from all supply chain domains — shipments, inventory,
freight, and warehouse — to identify the most likely cause of delay
and recommend a next action.

## When To Use

- When an order is delayed and the reason is unclear
- Before escalating an order to management
- When a customer requests an update on a specific order

## How To Use

    /sc-investigate SO10003

Replace SO10003 with the actual order number.

## Output Format

**Order:** [order number] — [customer name]

**Status:** [current delay status]
**Days Overdue:** [number]
**Root Cause:** [most likely cause based on available data]

**Evidence**
- Shipment status
- Inventory availability
- Freight / carrier status
- Warehouse pick status

**Recommended Action**
- Practical next step for the responsible team

**Confidence:** High / Medium / Low
**Data Gaps:** Any missing information


# ── FILE 3: sc-escalate.md ─────────────────────────────────────


# /sc-escalate
# Supply Chain Control Tower — Escalation Command
# =================================================

## What This Command Does

Returns a prioritised list of orders that require immediate attention.
Focuses on orders that are significantly overdue or have unresolved
root causes requiring manager intervention.

## When To Use

- At the start of the day to identify priority orders
- Before a management meeting
- When someone asks "what needs attention right now?"

## Output Format

**Escalation List — [date]**

For each escalated order:
- Order number and customer
- Days overdue
- Root cause
- Recommended action
- Responsible team

**Summary**
- Total orders requiring escalation
- Most common root cause
- Recommended focus area for the team


# ── FILE 4: sc-scan.md ─────────────────────────────────────────


# /sc-scan
# Supply Chain Control Tower — Improvement Scan Command
# ======================================================

## What This Command Does

Runs the continuous-improvement scan across recent supply chain data.
Detects recurring patterns, generates improvement recommendations,
and surfaces the highest-priority actions for review.

## When To Use

- Once per day or once per shift
- After a period of repeated delays or issues
- When you want to identify systemic problems, not just individual orders

## Output Format

**CI Scan Results — [date]**

**Patterns Detected**
- List of recurring patterns found across orders

**Recommendations Generated**
- Prioritised list of improvement actions
- Each with: pattern, recommended action, confidence, responsible team

**Top Priority**
- Single highest-priority recommendation with rationale

**Summary**
- Plain-English paragraph describing what the scan found


# ── FILE 5: sc-weekly.md ───────────────────────────────────────


# /sc-weekly
# Supply Chain Control Tower — Weekly Performance Report Command
# ==============================================================

## What This Command Does

Generates a weekly performance summary across all supply chain domains.
Covers shipment performance, inventory health, carrier performance,
warehouse efficiency, and improvement progress.

## When To Use

- End of week review
- Management reporting
- Identifying trends over a longer time window than the daily briefing

## Output Format

**Weekly Supply Chain Report — [week ending date]**

**Shipment Performance**
- On-time rate, delay rate, need-action rate
- Week-over-week trend

**Top Delay Causes This Week**
- Ranked list with counts

**Inventory Health**
- Stockout count, critical items, backorder count

**Carrier Performance**
- Top and bottom performing carriers

**Warehouse Performance**
- Pick completion rate, delayed picks, staffing issues

**Improvement Actions This Week**
- Recommendations approved, implemented, deferred

**Summary**
- Plain-English paragraph with the week's key takeaways


# ── FILE 6: sc-inventory.md ────────────────────────────────────


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


# ── FILE 7: sc-carriers.md ─────────────────────────────────────


# /sc-carriers
# Supply Chain Control Tower — Carrier Performance Command
# =========================================================

## What This Command Does

Returns a carrier performance summary across all active freight movements.
Identifies underperforming carriers, missed pickups, and freight holds
that are impacting delivery performance.

## When To Use

- When carrier delays are a recurring issue
- Before renewing or reviewing carrier contracts
- When investigating freight-related root causes

## Output Format

**Carrier Performance Summary — [date]**

**Performance by Carrier**
- Carrier name, performance tier, active shipments, issues

**Underperforming Carriers**
- Carriers below acceptable performance threshold
- Issues detected and recommended action

**Freight Holds**
- Active holds, reasons, impacted orders

**Missed Pickups**
- Recent missed pickups and responsible carrier

**Summary**
- Plain-English paragraph with carrier performance overview


# ── FILE 8: sc-warehouse.md ────────────────────────────────────


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
