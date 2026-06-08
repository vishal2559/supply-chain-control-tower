# mcp_server/performance_mcp_server.py
# Supply Chain Control Tower — Performance Agent
# =============================================================================
#
# Owner: Vishal
# This is the 10th MCP server in the Supply Chain Control Tower.
#
# PURPOSE:
#   Exposes performance metrics, token usage, cache statistics, and
#   anomaly history to Claude Desktop as queryable tools.
#
# WHAT IT ANSWERS:
#   "Which tool used the most tokens today?"
#   "What are my slowest queries?"
#   "Is the cache working? What's the hit rate?"
#   "Have there been any anomalies today?"
#   "Give me a full performance dashboard."
#   "Is the system secure and healthy?"
#
# TOOLS (5 total):
#   get_performance_dashboard  → full overview in one call
#   get_token_usage_summary    → per-tool token breakdown
#   get_slow_queries           → tools that exceeded timing threshold
#   get_cache_stats            → cache hit rate and status
#   get_anomaly_log            → recent anomaly history
#
# SECURITY:
#   This server is READ-ONLY. It reads logs and in-memory stats only.
#   It never writes to the database or modifies any data.
#   All tool calls are audit-logged via security_guard.py.
#
# HOW TO REGISTER IN CLAUDE DESKTOP:
#   Add to claude_desktop_config.json:
#   "performance-agent": {
#       "command": "python",
#       "args": ["C:\\...\\mcp_server\\performance_mcp_server.py"]
#   }
#
# =============================================================================

import sys
import os

# ─── Path setup ───────────────────────────────────────────────────────────────
# Must be the first thing — ensures all local imports work regardless of
# where Claude Desktop launches this server from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from mcp.server.fastmcp import FastMCP

# ─── Internal module imports ──────────────────────────────────────────────────
from supply_chain.token_tracker  import (
    get_session_summary, get_recent_entries, reset_session_log
)
from supply_chain.cache_manager  import get_cache_stats, get_cache_status
from supply_chain.security_guard import audit_log, get_security_status
from supply_chain.notifier       import get_recent_anomalies
from config.settings_loader      import get_setting, get_log_path

mcp = FastMCP("performance-agent")


# ─── TOOL 1 ───────────────────────────────────────────────────────────────────

@mcp.tool()
def get_performance_dashboard() -> dict:
    """
    Use this tool when the user wants a complete performance overview of the
    Supply Chain Control Tower system.

    Returns a single unified report covering:
    - Token usage summary for this session (total tokens, most expensive tool)
    - Cache health (hit rate, what is cached, TTL status)
    - Security status (read-only mode, audit logging, write protection)
    - Recent anomalies (last 5 anomaly events)
    - System settings summary (key thresholds from settings.yaml)

    Use this when the user asks things like:
    - "How is the system performing?"
    - "Give me a performance dashboard"
    - "Is everything healthy?"
    - "System status"
    - "How many tokens have I used?"
    - "Quick health check"
    """
    audit_log("get_performance_dashboard", "performance-agent")

    # Gather all data sources
    token_summary  = get_session_summary()
    cache          = get_cache_stats()
    security       = get_security_status()
    anomalies      = get_recent_anomalies(5)

    # Count anomalies by severity
    critical_anomalies = [a for a in anomalies if a.get("severity") == "CRITICAL"]
    warning_anomalies  = [a for a in anomalies if a.get("severity") == "WARNING"]

    # Determine overall system health
    if critical_anomalies:
        overall_health = "CRITICAL — action required"
    elif warning_anomalies:
        overall_health = "WARNING — review recommended"
    elif token_summary["total_calls"] == 0:
        overall_health = "IDLE — no tool calls yet this session"
    else:
        overall_health = "HEALTHY"

    return {
        "overall_health": overall_health,

        "tokens": {
            "total_this_session":  token_summary["total_tokens"],
            "total_tool_calls":    token_summary["total_calls"],
            "most_expensive_tool": token_summary["most_expensive_tool"],
            "alerts_fired":        token_summary["alerts_fired"],
            "cache_hit_rate_pct":  token_summary["cache_hit_rate_pct"],
        },

        "cache": {
            "status":        cache["enabled"],
            "hit_rate_pct":  cache["hit_rate_pct"],
            "cached_tables": cache["cached_keys"],
            "ttl_seconds":   cache["ttl_seconds"],
        },

        "security": {
            "read_only_mode":    security["read_only_mode"],
            "audit_logging":     security["audit_logging"],
            "write_ops_blocked": security["write_ops_blocked"],
            "status":            security["status"],
        },

        "anomalies": {
            "recent_count":    len(anomalies),
            "critical_count":  len(critical_anomalies),
            "warning_count":   len(warning_anomalies),
            "latest":          anomalies[-1] if anomalies else None,
        },

        "settings": {
            "cache_ttl_seconds":      get_setting("performance.cache_ttl_seconds"),
            "max_response_rows":      get_setting("performance.max_response_rows"),
            "token_alert_threshold":  get_setting("performance.token_alert_threshold"),
            "slow_query_ms":          get_setting("performance.slow_query_threshold_ms"),
            "indexes_built":          get_setting("database.indexes_built"),
        },
    }


# ─── TOOL 2 ───────────────────────────────────────────────────────────────────

@mcp.tool()
def get_token_usage_summary() -> dict:
    """
    Use this tool when the user wants to understand token consumption across
    all tool calls in the current session.

    Returns a breakdown of token usage by tool including:
    - Total estimated tokens used this session
    - Per-tool breakdown (calls, total tokens, average tokens per call)
    - Most expensive tool (highest total token usage)
    - Number of token alert threshold crossings
    - Last 5 individual tool call records

    Use this when the user asks things like:
    - "How many tokens have I used today?"
    - "Which tool is using the most tokens?"
    - "Show me token usage by agent"
    - "Am I using too many tokens?"
    - "What is the most expensive query?"
    - "Token breakdown"
    - "How close am I to my usage limit?"
    """
    audit_log("get_token_usage_summary", "performance-agent")

    summary = get_session_summary()
    recent  = get_recent_entries(5)

    # Add percentage contribution per tool
    total = summary["total_tokens"] if summary["total_tokens"] > 0 else 1
    by_tool_enriched = {}
    for tool_name, stats in summary["by_tool"].items():
        by_tool_enriched[tool_name] = {
            **stats,
            "pct_of_total": round(stats["total_tokens"] / total * 100, 1),
        }

    # Sort by total tokens descending for easy reading
    sorted_tools = dict(
        sorted(by_tool_enriched.items(),
               key=lambda x: x[1]["total_tokens"], reverse=True)
    )

    return {
        "session_total_tokens":   summary["total_tokens"],
        "session_total_calls":    summary["total_calls"],
        "session_total_ms":       summary["total_execution_ms"],
        "most_expensive_tool":    summary["most_expensive_tool"],
        "token_alerts_fired":     summary["alerts_fired"],
        "alert_threshold":        get_setting("performance.token_alert_threshold"),
        "by_tool":                sorted_tools,
        "recent_calls":           recent,
        "note": (
            "Token counts are estimates (characters ÷ 4). "
            "Actual Claude tokenisation may differ slightly."
        ),
    }


# ─── TOOL 3 ───────────────────────────────────────────────────────────────────

@mcp.tool()
def get_slow_queries() -> dict:
    """
    Use this tool when the user wants to identify which tools are taking
    the longest to execute.

    Returns all tool calls from the current session that exceeded the
    slow_query_threshold_ms setting, plus overall timing statistics.

    Use this when the user asks things like:
    - "Which tools are slow?"
    - "What are my slowest queries?"
    - "Why is the system feeling slow?"
    - "Show me query performance"
    - "Are there any performance problems?"
    - "Timing breakdown"
    """
    audit_log("get_slow_queries", "performance-agent")

    threshold_ms = get_setting("performance.slow_query_threshold_ms", default=500)
    all_entries  = get_recent_entries(100)   # look at last 100 calls

    # Filter to slow queries only
    slow = [e for e in all_entries if e.get("execution_ms", 0) > threshold_ms]

    # Build timing stats for all tools
    timing_by_tool: dict = {}
    for e in all_entries:
        t = e["tool_name"]
        ms = e.get("execution_ms", 0)
        if t not in timing_by_tool:
            timing_by_tool[t] = {"calls": 0, "total_ms": 0, "max_ms": 0}
        timing_by_tool[t]["calls"]    += 1
        timing_by_tool[t]["total_ms"] += ms
        timing_by_tool[t]["max_ms"]    = max(timing_by_tool[t]["max_ms"], ms)

    for t in timing_by_tool:
        calls = timing_by_tool[t]["calls"]
        timing_by_tool[t]["avg_ms"] = round(
            timing_by_tool[t]["total_ms"] / calls, 1
        )

    return {
        "threshold_ms":       threshold_ms,
        "slow_query_count":   len(slow),
        "slow_queries":       slow,
        "timing_by_tool":     timing_by_tool,
        "recommendation": (
            "If queries are slow, check: "
            "1) indexes_built is true in settings.yaml, "
            "2) cache_enabled is true, "
            "3) max_response_rows is not too high."
        ) if slow else "No slow queries detected this session.",
    }


# ─── TOOL 4 ───────────────────────────────────────────────────────────────────

@mcp.tool()
def get_cache_stats_tool() -> dict:
    """
    Use this tool when the user wants to understand how the in-memory cache
    is performing.

    Returns cache hit rate, what tables are currently cached, how old
    the cached data is, and the TTL (time-to-live) setting.

    Use this when the user asks things like:
    - "Is the cache working?"
    - "What is the cache hit rate?"
    - "How old is the cached data?"
    - "Is my data being cached?"
    - "Cache status"
    - "Why is the system loading data again?"
    """
    audit_log("get_cache_stats_tool", "performance-agent")

    stats = get_cache_stats()

    # Build age descriptions for cached items
    age_descriptions = {}
    for key, age_sec in stats.get("cache_ages_sec", {}).items():
        if age_sec < 60:
            age_descriptions[key] = f"{age_sec}s old (fresh)"
        elif age_sec < stats["ttl_seconds"]:
            age_descriptions[key] = f"{round(age_sec/60, 1)} min old (fresh)"
        else:
            age_descriptions[key] = f"{round(age_sec/60, 1)} min old (EXPIRED — will reload)"

    return {
        "cache_enabled":      stats["enabled"],
        "hit_rate_pct":       stats["hit_rate_pct"],
        "total_requests":     stats["total_requests"],
        "hits":               stats["hits"],
        "misses":             stats["misses"],
        "expirations":        stats["expirations"],
        "ttl_seconds":        stats["ttl_seconds"],
        "cached_tables":      stats["cached_keys"],
        "cache_age":          age_descriptions,
        "status":             get_cache_status(),
        "tip": (
            f"Cache TTL is {stats['ttl_seconds']}s. "
            f"To change it, update performance.cache_ttl_seconds in settings.yaml."
        ),
    }


# ─── TOOL 5 ───────────────────────────────────────────────────────────────────

@mcp.tool()
def get_anomaly_log() -> dict:
    """
    Use this tool when the user wants to see recent anomaly events detected
    by the Supply Chain Control Tower.

    Returns the last 20 anomaly events from logs/anomaly.log, grouped by
    severity and type.

    Anomaly types include:
    - CRITICAL_ORDER_SPIKE  : too many orders in NEED_ACTION status
    - UNKNOWN_REASON_SURGE  : too many delays with unknown cause
    - NEW_FREIGHT_HOLDS     : sudden increase in freight holds
    - INVENTORY_STOCKOUT    : items with no stock available
    - TOKEN_SPIKE           : a tool using unusually many tokens
    - SLOW_QUERY            : a tool taking too long to respond

    Use this when the user asks things like:
    - "Have there been any anomalies?"
    - "Show me recent alerts"
    - "Any critical events today?"
    - "What anomalies have been detected?"
    - "System alerts"
    - "Has anything unusual happened?"
    """
    audit_log("get_anomaly_log", "performance-agent")

    anomalies = get_recent_anomalies(20)

    # Group by severity
    critical = [a for a in anomalies if a.get("severity") == "CRITICAL"]
    warnings = [a for a in anomalies if a.get("severity") == "WARNING"]

    # Group by type
    by_type: dict = {}
    for a in anomalies:
        atype = a.get("anomaly_type", "UNKNOWN")
        if atype not in by_type:
            by_type[atype] = 0
        by_type[atype] += 1

    return {
        "total_anomalies":    len(anomalies),
        "critical_count":     len(critical),
        "warning_count":      len(warnings),
        "by_type":            by_type,
        "critical_events":    critical,
        "warning_events":     warnings,
        "all_recent":         anomalies[-10:],   # last 10 for context
        "log_path":           get_log_path("notifications.anomaly_log_path"),
        "note": (
            "Thresholds are set in config/settings.yaml under "
            "notifications.anomaly_thresholds. "
            "Adjust them to control sensitivity."
        ) if anomalies else "No anomalies recorded yet.",
    }


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
