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
