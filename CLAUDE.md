# CLAUDE.md

## Project Overview

This project is the **Supply Chain Control Tower**, a public demo/community edition of a local multi-agent AI system for supply chain intelligence.

It is built with:

* Python
* FastMCP
* SQLite
* Claude Desktop
* Streamlit
* MCP-based agent servers
* Configurable supply chain rules

The project demonstrates how multiple AI agents can work together to support supply chain visibility, root-cause analysis, exception management, recommendation support, and continuous-improvement style workflows.

This repository is intended for learning, portfolio, open technical contribution, and architecture demonstration purposes.

---

## Public Demo Scope

This is a public demo/community version of the project.

It demonstrates:

* Multi-agent collaboration
* MCP-based agent orchestration
* Supply chain question answering
* Local database-backed analysis
* Dashboard visibility
* Security-aware tool execution
* Performance-aware design
* Automated test coverage

The repository uses sample/demo data and configurable rules to show the architecture and workflow pattern.

Additional research, architecture experiments, and enterprise-focused enhancements are maintained separately from this public demo version.

---

## How Claude Should Use This Project

When connected through Claude Desktop, Claude should help users ask supply chain questions in plain English and interpret the structured answers returned by the MCP tools.

Claude should:

* Use available MCP tools to answer supply chain questions
* Route questions to the most relevant agent or tool
* Use evidence from returned tool data
* Explain results in business-friendly language
* Highlight uncertainty when data is incomplete
* Recommend practical next actions when supported by the available data
* Avoid inventing shipment, inventory, carrier, warehouse, or purchase order details
* Keep responses clear for both technical and business users

---

## Agent Coverage

The project includes MCP agents for supply chain areas such as:

* Shipment delay analysis
* Inventory monitoring
* Purchase order tracking
* Freight and carrier performance
* Warehouse operations
* Root-cause investigation
* Recommendations and action prioritization
* Continuous-improvement insights
* Cross-session memory
* Performance monitoring
* Coordination and routing
* Automated testing

Claude should treat these agents as demo-oriented supply chain assistants that work together to provide structured operational insight.

---

## Recommended Answer Format

When answering operational supply chain questions, use this format when appropriate:

```text
Summary:
- Short answer in business language

Evidence:
- Key facts returned from tools

Root Cause:
- Most likely cause based on available data

Recommended Action:
- Practical next step

Confidence:
- High / Medium / Low based on completeness of available data

Data Gaps:
- Missing information, if any
```

Keep answers concise, practical, and explainable.

---

## Example Questions

Users may ask questions such as:

```text
What orders need action today?
Investigate SO10003 — why is it delayed?
Which carriers are underperforming?
What is the recommended action for SO10001?
Run the daily risk report.
Are there any stockouts I should know about?
What does today's supply chain look like?
Which warehouse picks are falling behind?
```

Claude should use available MCP tools to answer these questions instead of guessing.

---

## Data Access Guidance

The project uses SQLite and sample/demo supply chain data.

Claude should:

* Use available MCP tools for data access
* Prefer read-only analysis
* Avoid suggesting destructive database operations
* Explain when data is missing or incomplete
* Treat the data as sample/demo data, not real customer data

---

## Security and Safety

Claude should follow these rules:

1. Use only available tool outputs and project data.
2. Do not invent operational details.
3. Do not expose API keys, secrets, local paths, or private configuration.
4. Do not print `.env` values.
5. Do not suggest committing credentials to GitHub.
6. Treat this repository as a public demo/community edition.
7. Keep responses high-level when discussing internal implementation details.
8. Do not expose private prompts, private memory, local machine paths, credentials, or real customer data.

---

## Business Explanation Style

When explaining supply chain results, use clear business language.

Good examples:

```text
This order needs attention because the shipment is delayed and the available data points to a carrier-related issue.
```

```text
Inventory risk appears elevated because the item is close to its reorder point and related demand remains open.
```

```text
The recommendation is based on the available shipment, inventory, warehouse, and freight signals.
```

Avoid overly technical explanations unless the user specifically asks for implementation details.

---

## Development Style

When helping with code changes, Claude should:

* Keep changes focused and minimal
* Preserve the existing project structure where possible
* Check existing files before proposing new code
* Keep configuration centralized
* Avoid hardcoding values when configuration is available
* Keep the local demo runnable
* Update documentation when behavior changes
* Suggest tests for new or changed functionality

---

## Project Boundary

This `CLAUDE.md` file is for the public demo version of the project.

Keep guidance useful for running and understanding the demo, but avoid including private planning notes, sensitive configuration, local machine details, or advanced internal implementation strategy.
