# mcp_server/coordinator_mcp_server.py
#
# Coordinator Agent — the 11th MCP server in the Supply Chain Control Tower.
#
# This is the FRONT DOOR for the entire system. Instead of manually calling
# 10 different agents, you ask the coordinator one question and it routes
# to the right place, gathers results, and returns a unified answer.
#
# This file is a thin wrapper around coordinator_engine.py.
# All real logic lives there. This file's only job is to:
#   1. Expose each engine function as an MCP tool
#   2. Write clear tool docstrings so Claude Desktop knows when to use each one
#   3. Catch errors gracefully so a failure in one tool doesn't crash the server
#
# Tools in this server (6 total):
#   route_question         — routes any plain-English question to the right agent(s)
#   get_order_health       — full cross-agent snapshot for one specific order
#   get_system_status      — health check on all 11 live agents
#   get_daily_brief        — morning summary across all four operational domains
#   escalate_critical_orders — all NEED_ACTION orders with full investigation context
#   get_agent_roster       — complete list of all 12 agents, tools, and status
#
# To run manually (for testing):
#   cd "C:\Users\preet\Documents\AI Work\supply_chain_mcp_project"
#   python mcp_server\coordinator_mcp_server.py
#
# Owner: Vishal
# Version: 3.0

import sys
import os

# ── Path fix — must be FIRST, before any local imports ───────────────────────
# Claude Desktop launches MCP servers from an unknown working directory.
# This line makes sure Python can always find the supply_chain package
# regardless of where the server is launched from.
# __file__  =  mcp_server/coordinator_mcp_server.py
# one dirname up  =  project root
# join with src   =  src/  (where supply_chain package lives)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from mcp.server.fastmcp import FastMCP

# ── Import all engine functions ───────────────────────────────────────────────
# These are the pure-Python functions we tested in the terminal.
# The MCP tools below are just thin wrappers around them.
from supply_chain.coordinator_engine import (
    get_agent_roster      as _get_agent_roster,
    get_system_status     as _get_system_status,
    get_order_health      as _get_order_health,
    get_daily_brief       as _get_daily_brief,
    escalate_critical_orders as _escalate_critical_orders,
    route_question        as _route_question,
)

# We rename imports with a leading underscore (_) so that the MCP tool
# functions below can use the clean names without collision.
# For example: _get_daily_brief() is the engine function,
#              get_daily_brief()  is the MCP tool Claude calls.

mcp = FastMCP("coordinator-agent")


# ─── TOOL 1 ─────────────────────────────────────────────────────────────────

@mcp.tool()
def route_question(question: str, order_no: str = "") -> dict:
    """
    Use this tool as the FIRST CHOICE when the user asks any supply chain
    question and you are not sure which agent to call.

    This tool reads the question, identifies what domain it belongs to,
    calls the right function(s), and returns a unified answer.

    It also returns a 'routed_to' field explaining which function was called
    and a 'routing_reason' field explaining why.

    Routing rules:
    - Question contains an order number (e.g. SO10001) → get_order_health
    - Question mentions briefing / morning / today / summary → get_daily_brief
    - Question mentions escalate / urgent / critical / overdue → escalate_critical_orders
    - Question mentions agents / health / working / system → get_system_status or get_agent_roster
    - Anything else → get_daily_brief as default

    Use this when the user asks things like:
    - "What is happening with SO10003?"
    - "Give me today's briefing"
    - "Which orders need immediate action?"
    - "Is everything working?"
    - "What should I focus on today?"
    - "Show me the worst orders right now"
    - "Route this question: what's going on with freight holds today?"

    Parameters:
      question — the user's plain-English question (required)
      order_no — optional order number if already known (e.g. "SO10001")
    """
    try:
        return _route_question(question=question, order_no=order_no)
    except Exception as e:
        return {
            "error": f"route_question failed: {str(e)}",
            "question": question,
            "hint": "Try calling get_daily_brief or get_order_health directly.",
        }


# ─── TOOL 2 ─────────────────────────────────────────────────────────────────

@mcp.tool()
def get_order_health(sales_order_no: str) -> dict:
    """
    Use this tool when the user wants a COMPLETE picture of one specific order.

    This is the most powerful single-order tool in the system. It pulls data
    from all four operational domains simultaneously — shipping, inventory,
    freight, and warehouse — and also runs the investigation and recommendation
    engines on top of that data.

    One call replaces what would otherwise require 5 separate agent calls.

    Returns for one order:
    - Customer name and item number
    - Scheduled pick date
    - Delay status (ON_TIME / DELAYED / NEED_ACTION / SHIPPED / CANCELLED)
    - How many days overdue
    - Inventory status for the item on this order
    - Freight status and whether a hold is active
    - Warehouse pick health
    - Carrier name and performance tier
    - Investigation severity (CRITICAL / HIGH / MEDIUM / LOW)
    - Root cause of the delay
    - List of contributing factors
    - The most important action to take right now
    - Priority score (0-100)
    - Which team should own resolution
    - Whether this order needs manager escalation

    Use this when the user asks things like:
    - "Give me the full picture for SO10002"
    - "What is the health of order SO10005?"
    - "Everything about SO10001"
    - "Check order SO10003 across all agents"
    - "What is wrong with SO10007 and what should we do?"
    - "Investigate SO10004" (use this instead of investigation-agent for a quick summary)
    """
    try:
        return _get_order_health(sales_order_no=sales_order_no)
    except Exception as e:
        return {
            "error": f"get_order_health failed: {str(e)}",
            "sales_order_no": sales_order_no,
            "hint": "Order IDs use SO10001 format — no dashes.",
        }


# ─── TOOL 3 ─────────────────────────────────────────────────────────────────

@mcp.tool()
def get_system_status() -> dict:
    """
    Use this tool when the user wants to know if all agents are working correctly.

    Health-checks all 11 live agents by verifying their core modules can be
    imported and their key functions exist. Returns HEALTHY or DEGRADED per agent.

    Overall health is HEALTHY only if every single agent passes.
    If any agent is DEGRADED, the overall status is DEGRADED.

    Returns:
    - overall_health: "HEALTHY" or "DEGRADED"
    - healthy_count and degraded_count
    - Per-agent breakdown with health status and diagnostic note
    - Today's date

    Use this when the user asks things like:
    - "Are all agents working?"
    - "Check the health of the system"
    - "Is everything online?"
    - "Run a health check"
    - "Which agents are having problems?"
    - "/health" (slash command trigger)
    - "Are the MCP servers running correctly?"
    """
    try:
        return _get_system_status()
    except Exception as e:
        return {
            "error": f"get_system_status failed: {str(e)}",
            "hint": "PYTHONPATH may not be set correctly.",
        }


# ─── TOOL 4 ─────────────────────────────────────────────────────────────────

@mcp.tool()
def get_daily_brief() -> dict:
    """
    Use this tool when the user wants a morning briefing or daily summary
    across the entire supply chain.

    This is the single most useful tool to start any conversation with.
    It scans all four operational domains — shipping delays, inventory health,
    freight status, and warehouse picks — and returns counts, a top root cause,
    and a plain-English briefing paragraph.

    Returns:
    - briefing: one plain-English paragraph summarising what needs attention today
    - shipment_health: counts by status (ON_TIME, DELAYED, NEED_ACTION, SHIPPED, CANCELLED)
    - inventory_health: counts by status (HEALTHY, LOW, CRITICAL, OUT_OF_STOCK, ON_BACKORDER)
    - freight_health: counts by status (SCHEDULED, IN_TRANSIT, ON_HOLD, PICKUP_MISSED, etc.)
    - warehouse_health: counts by pick health (ON_TRACK, AT_RISK, DELAYED)
    - multi_domain_risk_orders: number of orders with problems in 2+ domains
    - top_root_cause: the most common root cause across delayed orders today
    - date: today's date

    Use this when the user asks things like:
    - "Morning briefing"
    - "What does the supply chain look like today?"
    - "Give me today's summary"
    - "Daily overview"
    - "What should I know before my standup?"
    - "How is the supply chain performing?"
    - "What is the current state of all orders?"
    - "/briefing" (slash command trigger)
    """
    try:
        return _get_daily_brief()
    except Exception as e:
        return {
            "error": f"get_daily_brief failed: {str(e)}",
            "hint": "Check that data files exist in the data/ folder.",
        }


# ─── TOOL 5 ─────────────────────────────────────────────────────────────────

@mcp.tool()
def escalate_critical_orders() -> dict:
    """
    Use this tool when the user wants to see ALL orders that require
    immediate manager escalation — in one unified list.

    An order qualifies for escalation when it is in NEED_ACTION status,
    meaning it is more than 5 days past its scheduled pick date and
    has not yet shipped.

    For each escalated order, this tool runs the full investigation engine
    and recommendation engine, then sorts results by priority score
    (highest priority first).

    Returns for each order:
    - Sales order number and customer name
    - How many days overdue
    - Investigation severity (always CRITICAL or HIGH for these orders)
    - Root cause of the delay
    - The single most important action to take right now
    - Which team should own resolution
    - Priority score (0-100), sorted descending

    Also returns:
    - total_escalations: count of qualifying orders
    - summary: one-sentence plain-English escalation summary

    Use this when the user asks things like:
    - "What orders need escalation?"
    - "Show me all critical orders"
    - "Which orders are most urgent right now?"
    - "Escalation list for today"
    - "What needs immediate attention?"
    - "Manager escalation report"
    - "/escalate" (slash command trigger)
    """
    try:
        return _escalate_critical_orders()
    except Exception as e:
        return {
            "error": f"escalate_critical_orders failed: {str(e)}",
            "hint": "Check that data files exist in the data/ folder.",
        }


# ─── TOOL 6 ─────────────────────────────────────────────────────────────────

@mcp.tool()
def get_agent_roster() -> dict:
    """
    Use this tool when the user wants to know what agents exist, what each
    one does, how many tools each has, and which ones are live vs pending.

    Returns the complete agent directory for the Supply Chain Control Tower.

    Returns:
    - total_agents: 12
    - live_agents: count of agents currently connected to Claude Desktop
    - pending_agents: count of agents not yet built or registered
    - total_tools: total number of MCP tools across all agents
    - agents: full list with agent number, name, file, tool count, domain, status

    Use this when the user asks things like:
    - "What agents do we have?"
    - "List all agents"
    - "How many MCP servers are running?"
    - "What can each agent do?"
    - "Show me the agent map"
    - "Which agents are still pending?"
    - "What is the full system architecture?"
    """
    try:
        return _get_agent_roster()
    except Exception as e:
        return {
            "error": f"get_agent_roster failed: {str(e)}",
        }


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
# Every MCP server in this project ends with this exact block.
# mcp.run() starts the server and keeps it running, waiting for tool calls
# from Claude Desktop via the MCP protocol.

if __name__ == "__main__":
    mcp.run()
