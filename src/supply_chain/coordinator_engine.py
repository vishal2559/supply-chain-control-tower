# src/supply_chain/coordinator_engine.py
#
# Coordinator Engine — the routing and synthesis brain of the Supply Chain Control Tower.
#
# This file is PURE PYTHON. It has no MCP tools and no FastMCP imports.
# The coordinator_mcp_server.py file will import functions from here and
# expose them as MCP tools to Claude Desktop.
#
# Why separate the engine from the MCP server?
#   - You can test every function from the terminal without Claude Desktop.
#   - The logic is clean and reusable — no MCP boilerplate mixed in.
#   - Same pattern used by investigation_rules.py and recommendation_engine.py.
#
# What this file does:
#   get_agent_roster()           — returns the full list of all 12 agents
#   get_system_status()          — health-checks all 10 live agents via import test
#   get_order_health(order_no)   — full cross-agent snapshot for one order
#   get_daily_brief()            — morning summary across all domains
#   escalate_critical_orders()   — all NEED_ACTION orders with full context
#   route_question(q, order_no)  — keyword router: maps plain-English to right tools
#
# Owner: Vishal
# Version: 3.0

import sys
import os
from datetime import date

# ── Make sure src/supply_chain is on the path ─────────────────────────────────
# When Claude Desktop launches this indirectly via coordinator_mcp_server.py,
# the working directory is unknown. This line makes imports reliable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Data loaders ──────────────────────────────────────────────────────────────
# We need to load the four main data tables to answer cross-agent questions.
from supply_chain.data_loader import load_shipments
from supply_chain.inventory_data_loader import load_inventory
from supply_chain.freight_data_loader import load_freight
from supply_chain.warehouse_data_loader import load_warehouse_picks

# ── Rules engines ─────────────────────────────────────────────────────────────
# These are the classification functions from each domain agent.
# We import them directly — no need to call each MCP server separately.
from supply_chain.rules import (
    assign_delay_status,
    assign_reason_code,
    calculate_delay_days,
)
from supply_chain.inventory_rules import assign_inventory_status
from supply_chain.freight_rules import (
    assign_freight_status,
    assign_carrier_tier,
    calculate_pickup_delay_days,
)
from supply_chain.warehouse_rules import assign_pick_health

# ── Investigation and Recommendation logic ─────────────────────────────────────
# Reuse Phase 5 and Phase 6 logic rather than duplicating it.
from supply_chain.investigation_rules import build_investigation_report
from supply_chain.recommendation_engine import (
    calculate_priority_score,
    needs_escalation,
    get_responsible_team,
    get_action_sentence,
)

TODAY = date.today()

# ── Data file paths ───────────────────────────────────────────────────────────
# All existing agents use the CSV files directly via their data loaders.
# We do the same here to stay consistent with every other server.
# We build paths dynamically from this file's location so they work
# regardless of what directory Claude Desktop launches from.
#
# This file lives at:  src/supply_chain/coordinator_engine.py
# _HERE  ->  src/supply_chain/
# _SRC   ->  src/
# _ROOT  ->  project root (supply_chain_mcp_project/)
# _DATA  ->  project root/data/

_HERE = os.path.dirname(os.path.abspath(__file__))   # src/supply_chain/
_SRC  = os.path.dirname(_HERE)                       # src/
_ROOT = os.path.dirname(_SRC)                        # project root
_DATA = os.path.join(_ROOT, "data")                  # data/ folder

SHIPMENTS_FILE = os.path.join(_DATA, "shipments_sample.csv")
INVENTORY_FILE = os.path.join(_DATA, "inventory_sample.csv")
FREIGHT_FILE   = os.path.join(_DATA, "freight_sample.csv")
WAREHOUSE_FILE = os.path.join(_DATA, "warehouse_sample.csv")


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: build lookup dict for fast join operations
# ─────────────────────────────────────────────────────────────────────────────
# Instead of looping through all rows for every order lookup, we build a
# dict once keyed by the join field (e.g. sales_order_no, item_no).
# This makes lookups O(1) instead of O(n).

def _index_by(rows: list, key: str) -> dict:
    """
    Builds a dict mapping key_value -> first matching row.

    Example: _index_by(freight_rows, "sales_order_no")
    Returns: {"SO10001": {...row...}, "SO10002": {...row...}, ...}
    """
    result = {}
    for row in rows:
        k = str(row.get(key, "")).strip()
        if k and k not in result:
            result[k] = row
    return result


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: gather all cross-agent signals for one shipment row
# ─────────────────────────────────────────────────────────────────────────────
# This is the same pattern used in investigation_mcp_server.py.
# We centralise it here so coordinator tools don't duplicate it.

def _gather_signals(ship_row: dict,
                    inventory_index: dict,
                    freight_index: dict,
                    warehouse_index: dict) -> dict:
    """
    Given one shipment row + three pre-built lookup dicts, returns a flat
    dict of all signals needed by investigation and recommendation engines.

    We call this once per order. The indexes are built once per tool call
    and passed in — so we only scan each table once per request.
    """
    sales_order_no = str(ship_row.get("sales_order_no", "")).strip()
    item_no        = str(ship_row.get("item_no", "")).strip()

    # Shipping domain
    delay_status    = assign_delay_status(ship_row, TODAY)
    delay_days      = calculate_delay_days(ship_row, TODAY)
    shipping_reason = assign_reason_code(ship_row, TODAY)

    # Inventory domain — look up by item_no
    inv_row          = inventory_index.get(item_no, {})
    inventory_status = assign_inventory_status(inv_row) if inv_row else "UNKNOWN"

    # Freight domain — look up by sales_order_no
    frt_row             = freight_index.get(sales_order_no, {})
    freight_status      = assign_freight_status(frt_row, TODAY) if frt_row else "UNKNOWN"
    freight_hold        = str(frt_row.get("freight_hold_flag", "NO")).strip().upper() == "YES"
    freight_hold_reason = frt_row.get("freight_hold_reason", "") if frt_row else ""
    carrier_name        = frt_row.get("carrier_name", "Unknown") if frt_row else "Unknown"
    carrier_tier        = assign_carrier_tier(
        frt_row.get("carrier_performance_score", "")
    ) if frt_row else "UNKNOWN"

    # Warehouse domain — look up by sales_order_no
    wh_row      = warehouse_index.get(sales_order_no, {})
    pick_health = assign_pick_health(wh_row, TODAY) if wh_row else "UNKNOWN"

    return {
        "sales_order_no":      sales_order_no,
        "customer_name":       ship_row.get("customer_name", ""),
        "scheduled_pick_date": ship_row.get("scheduled_pick_date", ""),
        "delay_days":          delay_days,
        "delay_status":        delay_status,
        "shipping_reason":     shipping_reason,
        "inventory_status":    inventory_status,
        "freight_status":      freight_status,
        "freight_hold":        freight_hold,
        "freight_hold_reason": freight_hold_reason,
        "pick_health":         pick_health,
        "carrier_tier":        carrier_tier,
        "carrier_name":        carrier_name,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 1: get_agent_roster
# ─────────────────────────────────────────────────────────────────────────────
# Returns a static list of all 12 agents.
# "Static" means we define it here, not from the database.
# The roster only changes when we add or remove an agent.

def get_agent_roster() -> dict:
    """
    Returns the full agent roster: all 12 agents, their tools, domain,
    file location, and whether they are currently live in Claude Desktop.

    Used by the /health command and the get_system_status tool.
    """
    agents = [
        {
            "agent_number": 1,
            "name": "shipping-delay-agent",
            "file": "mcp_server/shipping_mcp_server.py",
            "tools": 9,
            "domain": "Outbound shipment delay tracking",
            "status": "LIVE",
        },
        {
            "agent_number": 2,
            "name": "inventory-agent",
            "file": "mcp_server/inventory_mcp_server.py",
            "tools": 6,
            "domain": "Stock levels and backorder status",
            "status": "LIVE",
        },
        {
            "agent_number": 3,
            "name": "po-agent",
            "file": "mcp_server/po_mcp_server.py",
            "tools": 5,
            "domain": "Purchase orders and supplier tracking",
            "status": "LIVE",
        },
        {
            "agent_number": 4,
            "name": "freight-agent",
            "file": "mcp_server/freight_mcp_server.py",
            "tools": 5,
            "domain": "Carrier pickup and freight holds",
            "status": "LIVE",
        },
        {
            "agent_number": 5,
            "name": "warehouse-agent",
            "file": "mcp_server/warehouse_mcp_server.py",
            "tools": 5,
            "domain": "Warehouse pick operations",
            "status": "LIVE",
        },
        {
            "agent_number": 6,
            "name": "investigation-agent",
            "file": "mcp_server/investigation_mcp_server.py",
            "tools": 4,
            "domain": "Root cause analysis across all domains",
            "status": "LIVE",
        },
        {
            "agent_number": 7,
            "name": "recommendation-agent",
            "file": "mcp_server/recommendation_mcp_server.py",
            "tools": 4,
            "domain": "Prioritised action plans and escalation",
            "status": "LIVE",
        },
        {
            "agent_number": 8,
            "name": "ci-agent",
            "file": "mcp_server/ci_mcp_server.py",
            "tools": 8,
            "domain": "Continuous improvement and pattern learning",
            "status": "LIVE",
        },
        {
            "agent_number": 9,
            "name": "memory-agent",
            "file": "mcp_server/memory_mcp_server.py",
            "tools": 3,
            "domain": "Project memory and session context",
            "status": "LIVE",
        },
        {
            "agent_number": 10,
            "name": "performance-agent",
            "file": "mcp_server/performance_mcp_server.py",
            "tools": 5,
            "domain": "Token tracking, cache stats, query performance",
            "status": "LIVE",
        },
        {
            "agent_number": 11,
            "name": "coordinator-agent",
            "file": "mcp_server/coordinator_mcp_server.py",
            "tools": 6,
            "domain": "Routing, synthesis, system health — front door for all agents",
            "status": "LIVE",
        },
        {
            "agent_number": 12,
            "name": "test-agent",
            "file": "mcp_server/test_mcp_server.py",
            "tools": 5,
            "domain": "Automated test scenarios for all agents",
            "status": "PENDING",
        },
    ]

    live_count    = sum(1 for a in agents if a["status"] == "LIVE")
    pending_count = sum(1 for a in agents if a["status"] == "PENDING")
    total_tools   = sum(a["tools"] for a in agents)

    return {
        "total_agents":   len(agents),
        "live_agents":    live_count,
        "pending_agents": pending_count,
        "total_tools":    total_tools,
        "agents":         agents,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 2: get_system_status
# ─────────────────────────────────────────────────────────────────────────────
# Checks whether each live agent's core module can be imported successfully.
# If the import works → HEALTHY. If it raises any exception → DEGRADED.
#
# Why imports instead of network pings?
# MCP servers are local Python processes — there is no HTTP endpoint to ping.
# The best proxy for "is this agent working?" is "can its key module be imported?"
# If the module import fails, the MCP server itself would also fail to start.

def get_system_status() -> dict:
    """
    Health-checks all 10 live agents by attempting to import their core module.

    Returns:
    - overall_health: "HEALTHY" if all pass, "DEGRADED" if any fail
    - agents: list with name, health status, and error message if any
    - healthy_count and degraded_count
    """

    # Each tuple is (agent_name, module_to_import, function_to_check_for)
    # We test a specific function name to confirm the right module loaded,
    # not just any file with that name.
    checks = [
        ("shipping-delay-agent",    "supply_chain.rules",              "assign_delay_status"),
        ("inventory-agent",         "supply_chain.inventory_rules",    "assign_inventory_status"),
        ("po-agent",                "supply_chain.po_rules",           "assign_po_status"),
        ("freight-agent",           "supply_chain.freight_rules",      "assign_freight_status"),
        ("warehouse-agent",         "supply_chain.warehouse_rules",    "assign_pick_health"),
        ("investigation-agent",     "supply_chain.investigation_rules","build_investigation_report"),
        ("recommendation-agent",    "supply_chain.recommendation_engine","calculate_priority_score"),
        ("ci-agent",                "supply_chain.ci_signal_detector", "run_full_signal_scan"),
        ("memory-agent",            "supply_chain.cache_manager",      "get_cached"),
        ("performance-agent",       "supply_chain.cache_manager",      "get_cached"),
        ("coordinator-agent",       "supply_chain.coordinator_engine", "get_agent_roster"),
    ]

    results = []
    healthy_count  = 0
    degraded_count = 0

    for agent_name, module_name, function_name in checks:
        try:
            # __import__ dynamically imports the named module at runtime.
            # This is the same as writing "import supply_chain.rules" but
            # with the module name as a variable.
            mod = __import__(module_name, fromlist=[function_name])

            # Check the specific function exists in the module.
            # hasattr returns True if the object has an attribute with that name.
            if hasattr(mod, function_name):
                results.append({
                    "agent":  agent_name,
                    "health": "HEALTHY",
                    "module": module_name,
                    "note":   f"{function_name}() found",
                })
                healthy_count += 1
            else:
                results.append({
                    "agent":  agent_name,
                    "health": "DEGRADED",
                    "module": module_name,
                    "note":   f"Module loaded but {function_name}() not found",
                })
                degraded_count += 1

        except Exception as e:
            # Catches ImportError (module missing) or any other load error.
            results.append({
                "agent":  agent_name,
                "health": "DEGRADED",
                "module": module_name,
                "note":   str(e),
            })
            degraded_count += 1

    overall = "HEALTHY" if degraded_count == 0 else "DEGRADED"

    return {
        "date":            str(TODAY),
        "overall_health":  overall,
        "healthy_count":   healthy_count,
        "degraded_count":  degraded_count,
        "agents":          results,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 3: get_order_health
# ─────────────────────────────────────────────────────────────────────────────
# Assembles a complete picture of one order by querying all four data domains.
# This replaces the need to manually call shipping + freight + warehouse +
# investigation + recommendation for the same order.

def get_order_health(sales_order_no: str) -> dict:
    """
    Returns a full health snapshot for one order.

    Pulls from: shipments, inventory, freight, warehouse_picks.
    Runs: investigation rules + recommendation engine.

    Returns:
    - order identity (order no, customer, item)
    - delay status and days overdue
    - inventory status for the item
    - freight status and hold flag
    - warehouse pick health
    - investigation severity and root cause
    - recommended action and team assignment
    - whether this order needs manager escalation
    """
    sales_order_no = sales_order_no.strip()

    # Load all four tables
    ship_rows = load_shipments(SHIPMENTS_FILE)
    inv_rows  = load_inventory(INVENTORY_FILE)
    frt_rows  = load_freight(FREIGHT_FILE)
    wh_rows   = load_warehouse_picks(WAREHOUSE_FILE)

    # Build lookup indexes
    inventory_index = _index_by(inv_rows, "item_no")
    freight_index   = _index_by(frt_rows, "sales_order_no")
    warehouse_index = _index_by(wh_rows,  "sales_order_no")

    # Find the shipment row for this order
    ship_row = None
    for row in ship_rows:
        if str(row.get("sales_order_no", "")).strip() == sales_order_no:
            ship_row = row
            break

    if ship_row is None:
        return {
            "error": f"Order {sales_order_no} not found in shipments.",
            "hint":  "Order IDs use SO10001 format with no dashes.",
        }

    # Gather all cross-agent signals
    s = _gather_signals(ship_row, inventory_index, freight_index, warehouse_index)

    # Run investigation engine to get severity and root cause
    investigation = build_investigation_report(
        sales_order_no      = s["sales_order_no"],
        customer_name       = s["customer_name"],
        scheduled_pick_date = s["scheduled_pick_date"],
        delay_days          = s["delay_days"],
        delay_status        = s["delay_status"],
        shipping_reason     = s["shipping_reason"],
        inventory_status    = s["inventory_status"],
        freight_status      = s["freight_status"],
        freight_hold        = s["freight_hold"],
        freight_hold_reason = s["freight_hold_reason"],
        pick_health         = s["pick_health"],
        carrier_tier        = s["carrier_tier"],
        carrier_name        = s["carrier_name"],
    )

    # Run recommendation engine to get priority score and action
    priority_score = calculate_priority_score(
        delay_days       = s["delay_days"],
        severity         = investigation.get("severity", "LOW"),
        freight_hold     = s["freight_hold"],
        inventory_status = s["inventory_status"],
    )
    root_cause     = investigation.get("root_cause", "UNKNOWN_NEEDS_REVIEW")
    team           = get_responsible_team(root_cause)
    action         = get_action_sentence(root_cause)
    needs_escalate = needs_escalation(
        priority_score = priority_score,
        delay_status   = s["delay_status"],
        freight_hold   = s["freight_hold"],
    )

    return {
        "sales_order_no":      s["sales_order_no"],
        "customer_name":       s["customer_name"],
        "item_no":             ship_row.get("item_no", ""),
        "scheduled_pick_date": s["scheduled_pick_date"],
        # Delay
        "delay_status":        s["delay_status"],
        "delay_days":          s["delay_days"],
        # Domain health
        "inventory_status":    s["inventory_status"],
        "freight_status":      s["freight_status"],
        "freight_hold":        s["freight_hold"],
        "freight_hold_reason": s["freight_hold_reason"],
        "pick_health":         s["pick_health"],
        "carrier_name":        s["carrier_name"],
        "carrier_tier":        s["carrier_tier"],
        # Investigation
        "severity":            investigation.get("severity", "LOW"),
        "root_cause":          root_cause,
        "contributing_factors":investigation.get("contributing_factors", []),
        "first_action":        investigation.get("first_action", ""),
        # Recommendation
        "priority_score":      priority_score,
        "assigned_team":       team,        "recommended_action":  action,
        "needs_escalation":    needs_escalate,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 4: get_daily_brief
# ─────────────────────────────────────────────────────────────────────────────
# Morning summary across all four domains.
# Reuses the same counting and briefing logic from investigation_mcp_server.py
# but packaged as a standalone function so coordinator can call it directly.

def get_daily_brief() -> dict:
    """
    Generates the morning briefing across all four operational domains.

    Returns:
    - Today's date
    - Shipment health counts (on time, delayed, need action, shipped, cancelled)
    - Inventory health counts (healthy, low, critical, out of stock, on backorder)
    - Freight health counts (scheduled, in transit, on hold, missed pickup)
    - Warehouse pick health counts (on track, at risk, delayed)
    - Number of orders with multi-domain problems
    - Top root cause system-wide
    - Plain-English briefing paragraph
    """
    ship_rows = load_shipments(SHIPMENTS_FILE)
    inv_rows  = load_inventory(INVENTORY_FILE)
    frt_rows  = load_freight(FREIGHT_FILE)
    wh_rows   = load_warehouse_picks(WAREHOUSE_FILE)

    inventory_index = _index_by(inv_rows, "item_no")
    freight_index   = _index_by(frt_rows, "sales_order_no")
    warehouse_index = _index_by(wh_rows,  "sales_order_no")

    # ── Count shipment statuses ───────────────────────────────────────────────
    ship_counts = {
        "total": len(ship_rows),
        "ON_TIME": 0, "DELAYED": 0, "NEED_ACTION": 0,
        "SHIPPED": 0, "CANCELLED": 0,
    }
    for row in ship_rows:
        status = assign_delay_status(row, TODAY)
        ship_counts[status] = ship_counts.get(status, 0) + 1

    # ── Count inventory statuses ──────────────────────────────────────────────
    inv_counts = {
        "total": len(inv_rows),
        "HEALTHY": 0, "LOW": 0, "CRITICAL": 0,
        "OUT_OF_STOCK": 0, "ON_BACKORDER": 0,
    }
    for row in inv_rows:
        status = assign_inventory_status(row)
        inv_counts[status] = inv_counts.get(status, 0) + 1

    # ── Count freight statuses ────────────────────────────────────────────────
    frt_counts = {
        "total": len(frt_rows),
        "SCHEDULED": 0, "IN_TRANSIT": 0, "DELIVERED": 0,
        "ON_HOLD": 0, "PICKUP_MISSED": 0, "CARRIER_DELAYED": 0,
    }
    for row in frt_rows:
        status = assign_freight_status(row, TODAY)
        frt_counts[status] = frt_counts.get(status, 0) + 1

    # ── Count warehouse pick health ───────────────────────────────────────────
    wh_counts = {
        "total": len(wh_rows),
        "ON_TRACK": 0, "AT_RISK": 0, "DELAYED": 0, "UNKNOWN": 0,
    }
    for row in wh_rows:
        health = assign_pick_health(row, TODAY)
        wh_counts[health] = wh_counts.get(health, 0) + 1

    # ── Multi-domain risk and top root cause ──────────────────────────────────
    # An order has "multi-domain risk" if it has problems in 2+ domains.
    # We count root causes across all delayed orders to find the top cause.
    multi_domain_count = 0
    root_cause_counts  = {}

    for ship_row in ship_rows:
        s = _gather_signals(ship_row, inventory_index, freight_index, warehouse_index)

        # Skip orders that are already shipped or cancelled
        if s["delay_status"] in ("SHIPPED", "CANCELLED"):
            continue

        # Count how many domains have a problem for this order
        issues = 0
        if s["delay_status"] in ("DELAYED", "NEED_ACTION"):
            issues += 1
        if s["inventory_status"] in ("OUT_OF_STOCK", "ON_BACKORDER", "CRITICAL"):
            issues += 1
        if s["freight_hold"] or s["freight_status"] in ("ON_HOLD", "PICKUP_MISSED"):
            issues += 1
        if s["pick_health"] in ("DELAYED", "AT_RISK"):
            issues += 1

        if issues >= 2:
            multi_domain_count += 1

        # Tally root causes for delayed orders only
        if s["delay_status"] in ("DELAYED", "NEED_ACTION"):
            report = build_investigation_report(
                sales_order_no      = s["sales_order_no"],
                customer_name       = s["customer_name"],
                scheduled_pick_date = s["scheduled_pick_date"],
                delay_days          = s["delay_days"],
                delay_status        = s["delay_status"],
                shipping_reason     = s["shipping_reason"],
                inventory_status    = s["inventory_status"],
                freight_status      = s["freight_status"],
                freight_hold        = s["freight_hold"],
                freight_hold_reason = s["freight_hold_reason"],
                pick_health         = s["pick_health"],
                carrier_tier        = s["carrier_tier"],
                carrier_name        = s["carrier_name"],
            )
            cause = report.get("root_cause", "UNKNOWN_NEEDS_REVIEW")
            root_cause_counts[cause] = root_cause_counts.get(cause, 0) + 1

    top_cause = (
        max(root_cause_counts, key=root_cause_counts.get)
        if root_cause_counts else "NONE"
    )

    # ── Build plain-English briefing ──────────────────────────────────────────
    delayed_total = ship_counts["DELAYED"] + ship_counts["NEED_ACTION"]
    need_action   = ship_counts["NEED_ACTION"]
    inv_problems  = inv_counts["CRITICAL"] + inv_counts["OUT_OF_STOCK"] + inv_counts["ON_BACKORDER"]
    frt_problems  = frt_counts["ON_HOLD"]  + frt_counts["PICKUP_MISSED"]
    wh_problems   = wh_counts["DELAYED"]   + wh_counts["AT_RISK"]

    parts = []
    if need_action > 0:
        parts.append(f"{need_action} order(s) need IMMEDIATE action — more than 5 days overdue.")
    if delayed_total > 0:
        parts.append(
            f"{delayed_total} of {ship_counts['total']} shipments are delayed. "
            f"Top root cause: {top_cause.replace('_', ' ')}."
        )
    if multi_domain_count > 0:
        parts.append(
            f"{multi_domain_count} order(s) have problems across multiple domains — highest priority."
        )
    if inv_problems > 0:
        parts.append(f"{inv_problems} inventory item(s) are critical, out of stock, or on backorder.")
    if frt_problems > 0:
        parts.append(f"{frt_problems} freight record(s) have holds or missed pickups.")
    if wh_problems > 0:
        parts.append(f"{wh_problems} warehouse pick(s) are delayed or at risk.")
    if not parts:
        parts.append("All systems are performing normally. No immediate action required.")

    briefing = " ".join(parts)

    return {
        "date":                     str(TODAY),
        "briefing":                 briefing,
        "shipment_health":          ship_counts,
        "inventory_health":         inv_counts,
        "freight_health":           frt_counts,
        "warehouse_health":         wh_counts,
        "multi_domain_risk_orders": multi_domain_count,
        "top_root_cause":           top_cause,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 5: escalate_critical_orders
# ─────────────────────────────────────────────────────────────────────────────
# Returns all orders in NEED_ACTION status (more than 5 days overdue),
# each enriched with full investigation and recommendation context.
# This is the "manager's escalation list" — one call to see everything urgent.

def escalate_critical_orders() -> dict:
    """
    Finds all orders in NEED_ACTION status and returns a complete
    escalation package for each one.

    An order is NEED_ACTION when it is more than 5 days past its
    scheduled pick date and has not shipped.

    Returns for each order:
    - Order identity and customer
    - How many days overdue
    - Investigation severity and root cause
    - Recommended action and assigned team
    - Whether manager escalation is confirmed
    """
    ship_rows = load_shipments(SHIPMENTS_FILE)
    inv_rows  = load_inventory(INVENTORY_FILE)
    frt_rows  = load_freight(FREIGHT_FILE)
    wh_rows   = load_warehouse_picks(WAREHOUSE_FILE)

    inventory_index = _index_by(inv_rows, "item_no")
    freight_index   = _index_by(frt_rows, "sales_order_no")
    warehouse_index = _index_by(wh_rows,  "sales_order_no")

    escalations = []

    for ship_row in ship_rows:
        s = _gather_signals(ship_row, inventory_index, freight_index, warehouse_index)

        # Only include NEED_ACTION orders
        if s["delay_status"] != "NEED_ACTION":
            continue

        # Run full investigation
        investigation = build_investigation_report(
            sales_order_no      = s["sales_order_no"],
            customer_name       = s["customer_name"],
            scheduled_pick_date = s["scheduled_pick_date"],
            delay_days          = s["delay_days"],
            delay_status        = s["delay_status"],
            shipping_reason     = s["shipping_reason"],
            inventory_status    = s["inventory_status"],
            freight_status      = s["freight_status"],
            freight_hold        = s["freight_hold"],
            freight_hold_reason = s["freight_hold_reason"],
            pick_health         = s["pick_health"],
            carrier_tier        = s["carrier_tier"],
            carrier_name        = s["carrier_name"],
        )

        root_cause     = investigation.get("root_cause", "UNKNOWN_NEEDS_REVIEW")
        priority_score = calculate_priority_score(
            delay_days       = s["delay_days"],
            severity         = investigation.get("severity", "HIGH"),
            freight_hold     = s["freight_hold"],
            inventory_status = s["inventory_status"],
        )

        escalations.append({
            "sales_order_no":   s["sales_order_no"],
            "customer_name":    s["customer_name"],
            "delay_days":       s["delay_days"],
            "severity":         investigation.get("severity", "HIGH"),
            "root_cause":       root_cause,
            "first_action":     investigation.get("first_action", ""),
            "assigned_team":    get_responsible_team(root_cause),
            "priority_score":   priority_score,
            "freight_hold":     s["freight_hold"],
            "needs_escalation": True,  # Every NEED_ACTION order is by definition escalated
        })

    # Sort by priority score descending — most urgent first
    escalations.sort(key=lambda x: x["priority_score"], reverse=True)

    return {
        "date":               str(TODAY),
        "total_escalations":  len(escalations),
        "orders":             escalations,
        "summary": (
            f"{len(escalations)} order(s) require immediate escalation today."
            if escalations
            else "No orders currently require escalation."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 6: route_question
# ─────────────────────────────────────────────────────────────────────────────
# Takes a plain-English question and an optional order number.
# Uses keyword matching to decide which function(s) to call.
# Returns a unified answer with a "routed_to" field showing the logic.
#
# Why keyword matching instead of AI?
# This runs inside an MCP server that IS the AI layer. We don't call
# another AI from inside an AI tool — that would be circular and expensive.
# Simple keyword matching is fast, predictable, and free.

def route_question(question: str, order_no: str = "") -> dict:
    """
    Routes a plain-English question to the right function(s) and returns
    a unified answer.

    Examples:
      "What's the status of SO10001?"         → get_order_health("SO10001")
      "Show me today's briefing"              → get_daily_brief()
      "Which orders need escalation?"         → escalate_critical_orders()
      "Are all agents working?"               → get_system_status()
      "What agents do we have?"               → get_agent_roster()
      "Investigate SO10003"                   → get_order_health("SO10003")

    The order_no parameter is used when the caller already parsed the
    order number out of the question. If not provided, we try to extract
    it from the question text.
    """
    q_lower = question.lower().strip()

    # ── Try to extract order number from question if not passed directly ──────
    # Order IDs always start with "SO" followed by digits (e.g. SO10001).
    # We scan each word in the question looking for this pattern.
    extracted_order = order_no.strip()
    if not extracted_order:
        for word in question.split():
            clean = word.strip("?.,!").upper()
            if clean.startswith("SO") and len(clean) > 2 and clean[2:].isdigit():
                extracted_order = clean
                break

    # ── Routing logic: keyword matching ──────────────────────────────────────
    # We check the most specific keywords first (order-level), then
    # broader keywords (system-level). This prevents false matches.

    # Rule 1: If there's an order number → get_order_health
    if extracted_order:
        result = get_order_health(extracted_order)
        result["routed_to"]    = "get_order_health"
        result["routing_reason"] = f"Order number {extracted_order} detected in question."
        return result

    # Rule 2: Daily briefing / morning report
    briefing_keywords = ["briefing", "brief", "morning", "today", "daily", "summary",
                         "overview", "status", "picture", "standup"]
    if any(kw in q_lower for kw in briefing_keywords):
        result = get_daily_brief()
        result["routed_to"]      = "get_daily_brief"
        result["routing_reason"] = "Daily briefing keywords detected."
        return result

    # Rule 3: Escalation / urgent / critical orders
    escalation_keywords = ["escalat", "urgent", "critical", "need action",
                           "immediate", "overdue", "worst", "priority"]
    if any(kw in q_lower for kw in escalation_keywords):
        result = escalate_critical_orders()
        result["routed_to"]      = "escalate_critical_orders"
        result["routing_reason"] = "Escalation or urgency keywords detected."
        return result

    # Rule 4: System health / agent health / are agents working
    health_keywords = ["health", "working", "alive", "agents", "status",
                       "system", "all agents", "are agents", "roster"]
    if any(kw in q_lower for kw in health_keywords):
        # Distinguish "show me agents" from "check agent health"
        if any(kw in q_lower for kw in ["roster", "list", "how many", "what agents"]):
            result = get_agent_roster()
            result["routed_to"]      = "get_agent_roster"
            result["routing_reason"] = "Agent roster / list keywords detected."
        else:
            result = get_system_status()
            result["routed_to"]      = "get_system_status"
            result["routing_reason"] = "System health keywords detected."
        return result

    # Rule 5: Default — if we can't route confidently, return a daily brief
    # This is better than returning an error — it gives the user useful info
    # while also explaining that the question wasn't specifically matched.
    result = get_daily_brief()
    result["routed_to"]      = "get_daily_brief"
    result["routing_reason"] = (
        "Could not match question to a specific domain. "
        "Returning daily brief as default. "
        "Try including an order number (e.g. SO10001) or a keyword like "
        "'escalate', 'health', or 'brief'."
    )
    return result
