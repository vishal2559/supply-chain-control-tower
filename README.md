# 🏭 Supply Chain Control Tower

> A local, zero-cost, multi-agent AI system for supply chain intelligence —
> built with Python, FastMCP, SQLite, and Claude Desktop.

![Version](https://img.shields.io/badge/version-v3.0-blue)
![Python](https://img.shields.io/badge/python-3.10-green)
![License](https://img.shields.io/badge/license-MIT-brightgreen)
![Agents](https://img.shields.io/badge/agents-12-orange)
![Tools](https://img.shields.io/badge/tools-57-purple)
![Status](https://img.shields.io/badge/status-active-success)

---

## What Is This?

The Supply Chain Control Tower is a **multi-agent AI system** that monitors
and analyses supply chain operations in real time. It uses 12 specialised AI
agents — each an MCP (Model Context Protocol) server — connected simultaneously
to Claude Desktop.

Ask Claude a question in plain English. The right agents activate automatically,
query the SQLite database, apply business rules, and return structured answers.

**This project demonstrates:**
- Multi-agent architecture using the MCP protocol
- Zero-cost local AI deployment (no cloud required, no per-query fees)
- Quantitative self-learning continuous improvement loop
- Enterprise-grade security, caching, performance monitoring, and testing
- OpenRouter fallback for uninterrupted operation

> **First open-source implementation of quantitative self-learning rules
> in a multi-agent MCP architecture for supply chain operations.**

---

## Live Demo — What You Can Ask Claude
```
"What orders need action today?"
"Investigate SO10003 — why is it delayed?"
"Which carriers are underperforming?"
"What is the recommended action for SO10001?"
"Run the daily risk report."
"Are there any stockouts I should know about?"
"What does today's supply chain look like?"
"Which warehouse picks are falling behind?"
```

Claude reasons across all 12 agents simultaneously to answer these questions.

---

## Architecture

Claude Desktop
│
▼
┌─────────────────────────────────────────────────────────┐
│                  Coordinator Agent                       │
│         Routes questions to the right agents            │
└──────┬──────────────────────────────────────────────────┘
│
├──► Shipping Delay Agent    (9 tools)
├──► Inventory Agent         (6 tools)
├──► Purchase Order Agent    (5 tools)
├──► Freight Agent           (5 tools)
├──► Warehouse Agent         (5 tools)
├──► Investigation Agent     (4 tools)
├──► Recommendation Agent    (4 tools)
├──► CI Agent                (8 tools)
├──► Memory Agent            (3 tools)
├──► Performance Agent       (10 tools)
├──► Coordinator Agent       (6 tools)
└──► Test Agent              (5 tools)
│
▼
SQLite Database
(supply_chain.db)

**Total: 12 agents — 57 tools**

---

## The 12 Agents

| Agent | Tools | Purpose |
|-------|-------|---------|
| Shipping Delay | 9 | Tracks order delays, reason codes, management summaries |
| Inventory | 6 | Monitors stock levels, backorders, reorder points |
| Purchase Order | 5 | Tracks PO status, late orders, supplier performance |
| Freight | 5 | Carrier performance, freight holds, missed pickups |
| Warehouse | 5 | Pick status, warehouse operations, staffing issues |
| Investigation | 4 | Root cause analysis across all domains |
| Recommendation | 4 | Prioritised action plans with team assignment |
| CI (Continuous Improvement) | 8 | Self-learning improvement loop with 8 quantitative rules |
| Memory | 3 | Cross-session memory and project state |
| Performance | 10 | Token tracking, cache stats, slow query detection |
| Coordinator | 6 | Routes questions, health checks, daily briefings |
| Test | 5 | Automated test suite — 53 scenarios across all agents |

---

## Key Features

### Multi-Agent Reasoning
Claude activates multiple agents simultaneously to answer complex questions.
A single query like "investigate SO10003" triggers the Investigation Agent,
which pulls data from Shipping, Inventory, Freight, and Warehouse agents
to build a complete root cause analysis.

### Self-Learning CI Agent
The Continuous Improvement Agent detects patterns, generates recommendations,
tracks approvals/rejections, and adjusts its own confidence scores using
8 quantitative learning rules — no manual tuning required.

### Enterprise Security
- Read-only SQLite enforcement — agents can never modify data
- SQL whitelist — only SELECT queries allowed
- Input validation and prompt injection protection on all 57 tools
- Audit log of every tool call

### Performance Layer
- In-memory caching with configurable TTL (default 5 minutes)
- Token usage tracking per tool call
- Slow query detection with configurable threshold
- Anomaly detection for token spikes and unusual patterns

### OpenRouter Fallback
When Claude Desktop hits its usage limit, a terminal fallback chat
automatically tries 4 free LLMs in sequence before switching to a
paid model — keeping the system operational at zero additional cost.

### Central Configuration
All settings live in `config/settings.yaml` — one file controls every
agent's behaviour. No hardcoded values anywhere in the codebase.

### Automated Testing
53 test scenarios across all 12 agents run in one command.
Results saved as JSON and human-readable log.

---

## Business Logic

Delay Status:    ON_TIME | DELAYED (1–5 days) | NEED_ACTION (5+ days)
Reason Codes:    FREIGHT_HOLD | BACKORDER | INVENTORY_SHORTAGE |
TRUCK_NOT_AVAILABLE | CARRIER_DELAY |
WAREHOUSE_PICK_DELAY | UNKNOWN_NEEDS_REVIEW
Inventory:       HEALTHY | LOW | CRITICAL | OUT_OF_STOCK | ON_BACKORDER
Carrier Tiers:   STRONG (≥85) | AVERAGE (≥70) | WEAK (≥55) | CRITICAL (<55)
Pick Health:     ON_TRACK | AT_RISK | DELAYED
Priority Score:  0–100 (low / medium / high / critical)

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10 |
| AI Protocol | MCP (Model Context Protocol) via FastMCP |
| LLM Client | Claude Desktop |
| LLM Fallback | OpenRouter (free tier + paid fallback chain) |
| Database | SQLite |
| Dashboard | Streamlit + Plotly |
| Configuration | PyYAML |
| OS | Windows (tested) |

---

## Project Structure

supply_chain_mcp_project
│
├── config
│   ├── settings.yaml           ← single source of truth for all settings
│   └── settings_loader.py      ← reads settings.yaml for all agents
│
├── data
│   └── supply_chain.db         ← SQLite database (all live data)
│
├── docs
│   ├── INSTALLATION_GUIDE.md
│   └── UPGRADE_INSTRUCTIONS.md
│
├── logs\                        ← auto-created on first run
│   ├── audit.log
│   ├── anomaly.log
│   ├── token_usage.json
│   ├── perf_log.json
│   ├── balance_log.json
│   └── test_results.json
│
├── mcp_server\                  ← all 12 MCP agent servers
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
├── scripts
│   ├── check_balance.py         ← OpenRouter balance monitor
│   ├── fallback_chat.py         ← terminal chat fallback
│   ├── build_indexes.py
│   └── csv_to_sqlite.py
│
├── src\supply_chain\            ← shared business logic modules
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
├── tests
│   ├── test_scenarios.py        ← 53 test scenarios
│   └── test_runner.py
│
├── dashboard
│   └── app.py                   ← Streamlit dashboard
│
├── .env                         ← API keys (never committed to GitHub)
├── .gitignore
├── CLAUDE.md                    ← project instructions for Claude
└── requirements.txt

---

## Quick Start

### Prerequisites
- Python 3.10
- Claude Desktop (Windows)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/vishal2559/supply-chain-control-tower.git
cd supply-chain-control-tower

# Install dependencies
pip install -r requirements.txt

# Set up the database
python scripts/csv_to_sqlite.py
python scripts/build_indexes.py

# Configure Claude Desktop
# See docs/INSTALLATION_GUIDE.md for the full claude_desktop_config.json setup
```

### OpenRouter Fallback Setup (optional)

```bash
# Create .env file at project root
echo OPENROUTER_API_KEY=your-key-here > .env

# Check your balance
python scripts/check_balance.py

# Start fallback chat
python scripts/fallback_chat.py
```

---
## Slash Commands (Claude Desktop)

```
/sc-briefing      — daily summary across all agents
/sc-investigate   — root cause analysis for a specific order
/sc-escalate      — orders needing immediate action
/sc-scan          — run CI improvement scan
/sc-weekly        — weekly performance report
```

---

## Version History

| Version | What Was Added |
|---------|---------------|
| v1.0 | Shipping Delay + Inventory agents (CSV data) |
| v1.5 | PO + Freight + Warehouse agents |
| v2.0 | Investigation + Recommendation + CI agents |
| v2.5 | SQLite upgrade + Streamlit dashboard |
| v3.0 | Enterprise standardisation: settings.yaml, security layer, caching, performance monitoring, coordinator, test agent, OpenRouter fallback |

---

## Roadmap

- **Phase 2** — Docker containerisation (docker-compose, PostgreSQL, FastAPI)
- **Phase 3** — Cloud deployment (AWS/GCP, Kubernetes, Redis, CI/CD)
- **Phase 4** — SaaS product (multi-tenancy, Stripe billing, ERP connectors)

---

## Author

**Vishal** — AI Engineer  
GitHub: [github.com/vishal2559](https://github.com/vishal2559)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built as a learning project that grew into a production-grade architecture.
Every line of code explained from first principles.*
