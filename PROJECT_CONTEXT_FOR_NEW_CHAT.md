# Supply Chain Control Tower — Complete Project Context
# Paste this entire document at the start of any new Claude chat.
# Last updated: June 2026 — v3.0 release
# ================================================================

## WHO I AM AND WHAT I AM BUILDING

I am Vishal, building a local, zero-cost, multi-agent AI system called the
Supply Chain Control Tower. It is a learning project that has grown into a
production-grade architecture. I am a beginner coder.

Always explain every piece of code in full detail — what each line does,
why it was written that way, and the reasoning behind every design decision.
Never assume prior knowledge. End every response with a terminal test checklist.

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
Phase 10 — Enterprise Standardisation    ✅ COMPLETE
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

## TECH STACK

Language:      Python 3.10
Data:          SQLite — data/supply_chain.db
MCP SDK:       FastMCP
LLM Client:    Claude Desktop (Windows)
LLM Fallback:  OpenRouter (4 free models + 1 paid fallback)
Dashboard:     Streamlit + Plotly
Config:        PyYAML — config/settings.yaml
OS:            Windows
Editor:        VS Code
Coding level:  Beginner — always explain every line

---

## PROJECT FOLDER

C:\Users\preet\Documents\AI Work\supply_chain_mcp_project\

Note: Windows username is "preet" but all project files, docs,
and code use "Vishal" as the owner name. Never use "Preet".

---

## FOLDER STRUCTURE

supply_chain_mcp_project\
│
├── config\
│   ├── settings.yaml              ← single source of truth
│   └── settings_loader.py         ← get_setting() + get_database_path()
│
├── data\
│   └── supply_chain.db            ← SQLite database
│
├── docs\
│   ├── INSTALLATION_GUIDE.md
│   └── UPGRADE_INSTRUCTIONS.md
│
├── logs\
│   ├── audit.log
│   ├── anomaly.log
│   ├── token_usage.json
│   ├── perf_log.json
│   ├── balance_log.json
│   └── test_results.json
│
├── mcp_server\                    ← all 12 MCP agent servers
│   ├── shipping_mcp_server.py
│   ├── inventory_mcp_server.py
│   ├── po_mcp_server.py
│   ├── freight_mcp_server.py
│   ├── warehouse_mcp_server.py
│   ├── investigation_mcp_server.py
│   ├── recommendation_mcp_server.py
│   ├── ci_mcp_server.py
│   ├── memory_mcp_server.py
│   ├── performance_mcp_server.py
│   ├── coordinator_mcp_server.py
│   └── test_mcp_server.py
│
├── scripts\
│   ├── check_balance.py           ← OpenRouter balance monitor
│   ├── fallback_chat.py           ← terminal fallback chat
│   ├── build_indexes.py
│   └── csv_to_sqlite.py
│
├── src\supply_chain\              ← shared business logic
│   ├── rules.py
│   ├── inventory_rules.py
│   ├── freight_rules.py
│   ├── warehouse_rules.py
│   ├── investigation_rules.py
│   ├── recommendation_engine.py
│   ├── cache_manager.py
│   ├── token_tracker.py
│   ├── security_guard.py
│   ├── anomaly_detector.py
│   ├── notifier.py
│   ├── input_validation.py
│   └── prompt_injection_shield.py
│
├── tests\
│   ├── test_scenarios.py          ← 53 test scenarios
│   └── test_runner.py
│
├── dashboard\
│   └── app.py                     ← Streamlit dashboard
│
├── .env                           ← API keys (never on GitHub)
├── .gitignore
├── CLAUDE.md
├── README.md
└── requirements.txt

---

## THE 12 MCP AGENTS — 57 TOOLS TOTAL

shipping-delay-agent  (9 tools):
  get_delayed_shipments, get_delay_summary, get_shipment_by_order,
  get_need_action_shipments, get_shipments_by_reason_code,
  get_shipments_by_customer, get_shipments_by_delay_status,
  recommend_action_for_order, get_management_summary

inventory-agent (6 tools):
  get_inventory_summary, get_inventory_by_item, get_inventory_by_status,
  get_backordered_items, check_inventory_for_order, get_inventory_by_warehouse

po-agent (5 tools):
  check_po_for_order, get_late_purchase_orders, get_open_purchase_orders,
  get_po_by_item, get_supplier_summary

freight-agent (5 tools):
  get_freight_status_by_order, get_freight_holds, get_missed_pickups,
  get_carrier_performance_summary, get_active_freight

warehouse-agent (5 tools):
  get_pick_status_by_order, get_warehouse_summary, get_delayed_picks,
  get_picks_by_warehouse, get_staffing_and_equipment_issues

investigation-agent (4 tools):
  investigate_order, find_orders_at_risk, get_root_cause_summary,
  get_daily_risk_report

recommendation-agent (4 tools):
  get_action_plan, get_team_workload, get_escalation_list,
  get_recommendation_for_order

ci-agent (8 tools):
  run_improvement_scan, get_pending_recommendations,
  approve_recommendation, reject_recommendation,
  log_outcome, get_improvement_summary, get_lessons_learned,
  get_weekly_report

memory-agent (3 tools):
  get_memory_status, read_project_memory, update_project_memory

performance-agent (10 tools):
  get_performance_dashboard, get_slow_queries, get_cache_stats_tool,
  get_token_usage_summary, get_anomaly_log,
  [+ 5 additional monitoring tools]

coordinator-agent (6 tools):
  get_agent_roster, get_system_status, get_order_health,
  get_daily_brief, escalate_critical_orders, route_question

test-agent (5 tools):
  run_all_tests, run_agent_tests, get_last_test_report,
  get_failed_tests, reset_test_results

---

## CLAUDE DESKTOP CONFIG

Config path (PowerShell):
$env:LOCALAPPDATA\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json

Python executable:
C:\Users\preet\AppData\Local\Programs\Python\Python310\python.exe

PYTHONPATH must point to:
C:\Users\preet\Documents\AI Work\supply_chain_mcp_project\src

Always validate config before restarting:
python -c "import json; json.load(open(r'PATH_TO_CONFIG'))"

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
Order ID format: SO10001 (no dashes)

---

## OPENROUTER FALLBACK

API key:         .env → OPENROUTER_API_KEY
Settings:        config/settings.yaml → llm_providers.fallback
Free model chain (tried in order):
  1. google/gemma-4-31b-it:free
  2. meta-llama/llama-3.3-70b-instruct:free
  3. nousresearch/hermes-3-llama-3.1-405b:free
  4. qwen/qwen3-coder:free
Paid fallback:   mistralai/mistral-7b-instruct
Balance alert:   $5.00 → logs/balance_log.json

Commands:
  python scripts\check_balance.py    ← verify API key + check credits
  python scripts\fallback_chat.py    ← start fallback terminal chat

In fallback chat, start with:
  "I am continuing work on the Supply Chain Control Tower.
   Today I want to [describe what you need]."

---

## KEY LESSONS LEARNED

BOM character:     Windows CSVs carry invisible \ufeff on first column.
                   Always verify column names explicitly after loading.

JSON validation:   Validate claude_desktop_config.json before restarting.
                   One syntax error disconnects all 12 agents.

PowerShell:        Use $env:VARNAME not %VARNAME%.
                   Use Rename-Item not rename.

.env encoding:     Create with Python open(..., 'w', encoding='utf-8').
                   PowerShell Out-File adds BOM which breaks dotenv.

Module location:   All supply_chain modules only in src\supply_chain\.
                   Duplicates at project root cause silent wrong imports.

sys.path fix:      Every MCP server needs this before imports:
                   sys.path.insert(0, os.path.dirname(
                       os.path.dirname(os.path.abspath(__file__))))

Security pattern:  Input → sanitise_input() at top of every tool.
                   Output → shield_row() or shield_rows() on every return.

---

## CODING RULES

1. Read before writing — check existing files first
2. One file at a time — confirm working before next step
3. Never touch unrelated files
4. Flag uncertainty explicitly — never guess silently
5. All settings in settings.yaml — never hardcode values
6. Always encoding="utf-8" on file operations
7. Owner is always "Vishal" — never "Preet"

---

## SLASH COMMANDS

/sc-briefing      — daily summary across all agents
/sc-investigate   — root cause analysis for a specific order
/sc-escalate      — orders needing immediate action
/sc-scan          — run CI improvement scan
/sc-weekly        — weekly performance report

---

## GITHUB

Repository: https://github.com/vishal2559/supply-chain-control-tower
Current release: v3.0
License: MIT

---

## ROADMAP

Phase 2 — Docker containerisation (docker-compose, PostgreSQL, FastAPI)
Phase 3 — Cloud deployment (AWS/GCP, Kubernetes, Redis, CI/CD)
Phase 4 — SaaS product (multi-tenancy, Stripe billing, ERP connectors)