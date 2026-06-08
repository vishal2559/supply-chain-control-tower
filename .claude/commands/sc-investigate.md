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
