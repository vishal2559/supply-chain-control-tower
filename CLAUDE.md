# CLAUDE.md — Supply Chain Control Tower
# Project instructions for Claude Desktop
# This file is read automatically by Claude Code.
# For Claude Desktop: paste contents into Project Instructions.
# ================================================================

## WHO I AM

I am Vishal, an AI Engineer building the Supply Chain Control Tower —
a local, zero-cost, multi-agent AI system running on Windows via
Claude Desktop. I am a beginner coder. Always explain every line of
code in full detail — what it does, why it was written that way, and
the reasoning behind every design decision. Never assume prior knowledge.

---

## PROJECT LOCATION

C:\Users\preet\Documents\AI Work\supply_chain_mcp_project\

Note: Windows username is "preet" but all project files, documentation,
code comments, and settings use "Vishal" as the owner name. Never use
"Preet" in any project output.

---

## CURRENT STATUS — v3.0 COMPLETE

Phase 1  — Shipping Delay Agent          ✅ COMPLETE
Phase 2  — Inventory Agent               ✅ COMPLETE
Phase 3  — Purchase Order Agent          ✅ COMPLETE
Phase 4  — Freight + Warehouse Agents    ✅ COMPLETE
Phase 5  — Investigation Agent           ✅ COMPLETE
Phase 6  — Recommendation Agent          ✅ COMPLETE
Phase 7  — SQLite Database Upgrade       ✅ COMPLETE
Phase 8  — Streamlit Dashboard           ✅ COMPLETE
Phase 9  — CI Agent                      ✅ COMPLETE
Phase 10 — Enterprise Standardisation   ✅ COMPLETE
  Step A — settings.yaml + settings_loader.py
  Step B — build_indexes.py (24 indexes)
  Step C — fix_bom_columns.py
  Step D — cache_manager.py + token_tracker.py
  Step E — security_guard.py + anomaly_detector.py + notifier.py
  Step F — performance_mcp_server.py (10th agent)
  Step G — coordinator_mcp_server.py (11th agent)
  Step H — test_mcp_server.py (12th agent, 53 scenarios)
  Step I — OpenRouter fallback (check_balance.py + fallback_chat.py)

Next: Phase 2 — Docker containerisation

---

## THE 12 MCP AGENTS

Agent                    File                              Tools
─────────────────────────────────────────────────────────────────
shipping-delay-agent     mcp_server/shipping_mcp_server.py      9
inventory-agent          mcp_server/inventory_mcp_server.py     6
po-agent                 mcp_server/po_mcp_server.py            5
freight-agent            mcp_server/freight_mcp_server.py       5
warehouse-agent          mcp_server/warehouse_mcp_server.py     5
investigation-agent      mcp_server/investigation_mcp_server.py 4
recommendation-agent     mcp_server/recommendation_mcp_server.py 4
ci-agent                 mcp_server/ci_mcp_server.py            8
memory-agent             mcp_server/memory_mcp_server.py        3
performance-agent        mcp_server/performance_mcp_server.py  10
coordinator-agent        mcp_server/coordinator_mcp_server.py   6
test-agent               mcp_server/test_mcp_server.py          5

Total: 12 agents — 57 tools

---

## KEY FILE LOCATIONS

config/settings.yaml          — single source of truth for all settings
config/settings_loader.py     — reads settings.yaml (used by all agents)
data/supply_chain.db          — SQLite database (all live data)
logs/audit.log                — every tool call recorded here
logs/token_usage.json         — token usage per tool call
logs/perf_log.json            — performance timing per tool call
logs/anomaly.log              — anomaly events
logs/test_results.json        — latest test run results
logs/balance_log.json         — OpenRouter balance history
scripts/check_balance.py      — OpenRouter credit balance monitor
scripts/fallback_chat.py      — terminal chat when Claude Desktop limited
.env                          — API keys (NEVER commit to GitHub)
CLAUDE.md                     — this file
README.md                     — public documentation
tests/test_scenarios.py       — 53 test scenarios
tests/test_runner.py          — dynamic test runner

---

## SHARED MODULES (src/supply_chain/)

rules.py                  — delay status + reason code logic
inventory_rules.py        — inventory status logic
freight_rules.py          — freight status + carrier tier logic
warehouse_rules.py        — pick health logic
investigation_rules.py    — root cause analysis logic
recommendation_engine.py  — action plan + priority scoring
cache_manager.py          — in-memory caching with TTL
token_tracker.py          — token usage estimation
security_guard.py         — read-only enforcement + audit log
anomaly_detector.py       — pattern detection + alerting
notifier.py               — log + desktop + email notifications
input_validation.py       — sanitise_input for all tool inputs
prompt_injection_shield.py — shield_row / shield_rows on all outputs

---

## CODING RULES — ALWAYS FOLLOW THESE

1. READ BEFORE WRITING
   Always check what already exists before proposing new code.
   Never duplicate files or functions that already exist.

2. ONE STEP AT A TIME
   One file per response. Confirm it works before moving to the next.
   Never redesign multiple things at once.

3. NEVER TOUCH UNRELATED FILES
   If fixing inventory_mcp_server.py, do not touch any other file.
   Scope changes tightly.

4. FLAG UNCERTAINTY EXPLICITLY
   If unsure about a function name, file location, or behaviour —
   say so. Never guess silently.

5. EXPLAIN EVERY LINE
   Every code block must be preceded by a plain-English explanation
   of what each line does and why. Assume zero prior knowledge.

6. CONFIGURATION DISCIPLINE
   All settings in settings.yaml. Never hardcode paths, thresholds,
   or flags in .py files. Read via get_setting().

7. ENCODING ON WINDOWS
   All file operations require encoding="utf-8" explicitly.
   Omitting it causes UnicodeDecodeError on Windows.

8. SYS.PATH FIX IN EVERY MCP SERVER
   Every mcp_server file needs this at the top before any imports:
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

9. SECURITY PATTERN
   Every tool that accepts input → sanitise_input() at the top.
   Every tool that returns database text → shield_row() or shield_rows().

10. NAMING
    Owner is always "Vishal" in all files, settings, docs, and code.
    Order IDs use format SO10001 (no dashes).

---

## BUSINESS LOGIC QUICK REFERENCE

Delay status:    ON_TIME | DELAYED (1-5 days) | NEED_ACTION (5+ days)
                 SHIPPED | CANCELLED
Reason codes:    FREIGHT_HOLD | BACKORDER | INVENTORY_SHORTAGE |
                 TRUCK_NOT_AVAILABLE | CARRIER_DELAY |
                 WAREHOUSE_PICK_DELAY | UNKNOWN_NEEDS_REVIEW | NOT_APPLICABLE
Inventory:       HEALTHY | LOW | CRITICAL | OUT_OF_STOCK | ON_BACKORDER
PO status:       ON_TIME | LATE | PARTIAL | RECEIVED | CANCELLED
Freight status:  SCHEDULED | IN_TRANSIT | DELIVERED | ON_HOLD |
                 PICKUP_MISSED | CARRIER_DELAYED
Carrier tiers:   STRONG(≥85) | AVERAGE(≥70) | WEAK(≥55) | CRITICAL(<55)
Pick health:     ON_TRACK | AT_RISK | DELAYED
Priority score:  0-100 integer (low/medium/high/critical)

---

## SLASH COMMANDS

/sc-briefing      — daily summary across all agents
/sc-investigate   — root cause analysis for a specific order
/sc-escalate      — list orders needing immediate action
/sc-scan          — run CI improvement scan
/sc-weekly        — weekly performance report

---

## CLAUDE DESKTOP CONFIG

Config path (PowerShell):
$env:LOCALAPPDATA\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json

Python executable:
C:\Users\preet\AppData\Local\Programs\Python\Python310\python.exe

PYTHONPATH env block must point to:
C:\Users\preet\Documents\AI Work\supply_chain_mcp_project\src

---

## TECH STACK

Language:      Python 3.10
Data:          SQLite — data/supply_chain.db
MCP SDK:       FastMCP
LLM Client:    Claude Desktop
LLM Fallback:  OpenRouter (free model chain + paid fallback)
Dashboard:     Streamlit + Plotly
Config:        PyYAML
OS:            Windows
Editor:        VS Code

---

## COMMON PITFALLS — LEARNED THE HARD WAY

BOM character:     Windows CSV files carry invisible \ufeff on first column.
                   Always verify column names explicitly after loading.

JSON validation:   Always run python -c "import json; json.load(open(...))"
                   before restarting Claude Desktop. One syntax error
                   disconnects all 12 agents simultaneously.

PowerShell syntax: Use $env:VARNAME not %VARNAME%. Use Rename-Item not rename.

Module location:   All supply_chain modules live only in src\supply_chain\.
                   A stray duplicate at project root causes silent wrong imports.

.env encoding:     Create .env with Python open(..., 'w', encoding='utf-8').
                   PowerShell Out-File adds BOM which breaks dotenv silently.

Function names:    Always verify actual function names via dir() before
                   referencing them in other files.

---

## OPENROUTER FALLBACK

API key stored in: .env (OPENROUTER_API_KEY=sk-or-v1-...)
Settings in:       config/settings.yaml → llm_providers.fallback
Free model chain:
  1. google/gemma-4-31b-it:free       ← primary
  2. meta-llama/llama-3.3-70b-instruct:free
  3. nousresearch/hermes-3-llama-3.1-405b:free
  4. qwen/qwen3-coder:free
Paid fallback:     mistralai/mistral-7b-instruct
Balance alert:     $5.00 threshold → logs/balance_log.json

To use fallback:
  python scripts\check_balance.py     ← verify API key works
  python scripts\fallback_chat.py     ← start terminal chat

---

## ROADMAP

Phase 2 — Docker containerisation (docker-compose, PostgreSQL, FastAPI)
Phase 3 — Cloud deployment (AWS/GCP, Kubernetes, Redis, CI/CD)
Phase 4 — SaaS product (multi-tenancy, Stripe billing, ERP connectors)

---

## GITHUB

Repository: https://github.com/vishal2559/supply-chain-control-tower
Current release: v3.0
License: MIT