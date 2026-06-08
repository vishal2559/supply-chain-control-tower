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
