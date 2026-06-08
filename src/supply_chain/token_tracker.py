# src/supply_chain/token_tracker.py
# Supply Chain Control Tower — Token + Timing Tracker
# =============================================================================
#
# PURPOSE:
#   Wraps tool responses to measure and log:
#     - How many tokens each tool response consumes (estimated)
#     - How long each tool call took to run (milliseconds)
#     - Whether data came from cache or SQLite
#     - How many rows were returned
#
# WHY THIS EXISTS:
#   Claude Desktop has a usage limit. Each tool response consumes tokens
#   from that limit. Without tracking, you have no idea which tools are
#   expensive or which queries are burning your quota.
#   After Step F (Performance Agent), you can ask Claude:
#     "Which tool used the most tokens today?"
#     "What are my slowest queries?"
#     "Am I close to my token limit?"
#
# HOW TOKEN ESTIMATION WORKS:
#   We convert the response to a string, count characters, divide by 4.
#   Example: 8,000 characters ÷ 4 = ~2,000 tokens (estimated)
#   This is the standard approximation used across the industry.
#   It won't be perfectly exact but correctly identifies expensive tools.
#
# HOW TO USE IN A NEW MCP SERVER TOOL:
#   # At the top of the file:
#   from supply_chain.token_tracker import track
#
#   # Wrap your tool return value:
#   result = {"sales_order_no": "SO10001", ...}
#   return track("get_shipment_by_order", "shipping-delay-agent", result)
#
#   # With cache tracking:
#   return track("get_delayed_shipments", "shipping-delay-agent",
#                result, cache_hit=True, rows_returned=len(result))
#
# SETTINGS THAT CONTROL THIS MODULE (all in config/settings.yaml):
#   performance.token_tracking_enabled → true/false master switch
#   performance.token_chars_per_token  → chars per token (default: 4)
#   performance.token_alert_threshold  → alert if tokens > this (default: 2000)
#   performance.token_log_path         → where to write the log
#   performance.slow_query_threshold_ms → flag slow queries (default: 500)
#
# PHASE 4 NOTE (SaaS):
#   In Phase 4, this tracker becomes the billing meter.
#   Every token logged here = a unit of billing for that tenant.
#   The interface is already designed for this — agent name maps to tenant.
#
# =============================================================================

import json
import time
import os
import sys
import threading
from datetime import datetime

# ─── Path setup ──────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
))))

from config.settings_loader import (
    get_setting,
    get_log_path,
    is_token_tracking_enabled,
    get_token_alert_threshold,
)

# ─── Thread lock ──────────────────────────────────────────────────────────────
# Prevents two tools running simultaneously from corrupting the log file
_LOCK = threading.Lock()

# ─── In-memory log buffer ────────────────────────────────────────────────────
# Stores all entries for the current session.
# Written to disk on each track() call AND available in memory for fast queries.
_SESSION_LOG: list = []


# ─── Core tracking function ───────────────────────────────────────────────────

def track(
    tool_name:     str,
    agent_name:    str,
    result,
    start_time:    float = None,
    cache_hit:     bool  = False,
    rows_returned: int   = None,
) -> object:
    """
    Measures a tool response and logs token + timing data.
    Always returns the original result unchanged — it is purely observational.

    Parameters:
        tool_name     : str   — name of the tool being called
                                e.g. "get_delayed_shipments"
        agent_name    : str   — which agent owns this tool
                                e.g. "shipping-delay-agent"
        result        : any   — the tool's return value (dict or list)
                                this is passed through unchanged
        start_time    : float — Unix timestamp from time.time() when tool started
                                If None, execution_ms is recorded as 0
        cache_hit     : bool  — True if data came from cache, False if from SQLite
        rows_returned : int   — number of rows in the result (optional)
                                If None, we count list length or use 1 for dicts

    Returns:
        The original result — unchanged. track() never modifies data.

    Example usage in a tool:
        start = time.time()
        rows = get_cached("shipments", load_shipments, DB_FILE)
        result = [build_row(r) for r in rows if condition]
        return track("get_delayed_shipments", "shipping-delay-agent",
                     result, start_time=start, cache_hit=True,
                     rows_returned=len(result))
    """
    # If token tracking is disabled in settings.yaml, return immediately
    # with zero overhead — no measurement, no logging
    if not is_token_tracking_enabled():
        return result

    try:
        # ── Measure execution time ────────────────────────────────────────────
        # If start_time was passed in, calculate how long the tool took
        execution_ms = 0.0
        if start_time is not None:
            execution_ms = round((time.time() - start_time) * 1000, 2)

        # ── Count rows returned ───────────────────────────────────────────────
        if rows_returned is None:
            if isinstance(result, list):
                rows_returned = len(result)
            elif isinstance(result, dict):
                rows_returned = 1
            else:
                rows_returned = 0

        # ── Estimate token usage ──────────────────────────────────────────────
        # Convert result to JSON string to get character count
        # json.dumps handles both dicts and lists
        try:
            result_str = json.dumps(result, default=str)
        except Exception:
            result_str = str(result)

        chars_per_token = get_setting(
            "performance.token_chars_per_token", default=4
        )
        response_chars    = len(result_str)
        estimated_tokens  = round(response_chars / chars_per_token)

        # ── Check alert thresholds ────────────────────────────────────────────
        alert_threshold   = get_token_alert_threshold()
        slow_threshold_ms = get_setting(
            "performance.slow_query_threshold_ms", default=500
        )

        token_alert = estimated_tokens > alert_threshold
        slow_query  = execution_ms > slow_threshold_ms and start_time is not None

        # ── Build log entry ───────────────────────────────────────────────────
        entry = {
            "timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tool_name":       tool_name,
            "agent":           agent_name,
            "rows_returned":   rows_returned,
            "response_chars":  response_chars,
            "estimated_tokens": estimated_tokens,
            "execution_ms":    execution_ms,
            "cache_hit":       cache_hit,
            "token_alert":     token_alert,
            "slow_query":      slow_query,
        }

        # ── Store in memory ───────────────────────────────────────────────────
        with _LOCK:
            _SESSION_LOG.append(entry)

            # ── Write to disk ─────────────────────────────────────────────────
            # We append to the JSON log file on every call so data is never lost
            _append_to_log(entry)

            # ── Print alerts to console ───────────────────────────────────────
            if token_alert:
                print(
                    f"[token_tracker] ALERT: '{tool_name}' used ~{estimated_tokens} tokens "
                    f"(threshold: {alert_threshold})"
                )
            if slow_query:
                print(
                    f"[token_tracker] SLOW QUERY: '{tool_name}' took {execution_ms}ms "
                    f"(threshold: {slow_threshold_ms}ms)"
                )

    except Exception as e:
        # IMPORTANT: If token tracking fails for any reason, we still return
        # the original result. Tracking is observational — it must never
        # break the tool it is wrapping.
        print(f"[token_tracker] WARNING: tracking failed for '{tool_name}': {e}")

    # Always return the original result, no matter what happened above
    return result


# ─── Log file writer ──────────────────────────────────────────────────────────

def _append_to_log(entry: dict):
    """
    Appends one log entry to the token usage JSON log file.

    The log file is a JSON Lines file — one JSON object per line.
    This format is easy to parse and append to without loading the whole file.

    Why JSON Lines and not a regular JSON array?
    A regular JSON array like [{...}, {...}] requires rewriting the entire file
    every time you add an entry. JSON Lines just appends a new line — much faster
    and safer (a crash mid-write doesn't corrupt the whole file).
    """
    try:
        log_path = get_log_path("performance.token_log_path")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        # Log write failure should never crash the tool
        print(f"[token_tracker] WARNING: Could not write to log: {e}")


# ─── Session summary ──────────────────────────────────────────────────────────

def get_session_summary() -> dict:
    """
    Returns a summary of all tool calls in the current session.

    Used by the Performance Agent (Step F) to answer questions like:
        "How many tokens have been used so far today?"
        "Which tool is the most expensive?"

    Returns a dict with:
        total_calls         → number of tool calls tracked this session
        total_tokens        → estimated total tokens used this session
        total_execution_ms  → total time spent in tools this session
        cache_hit_rate_pct  → % of calls that hit the cache
        alerts_fired        → number of token alert thresholds crossed
        slow_queries        → number of slow query alerts
        by_tool             → per-tool breakdown (tokens, calls, avg_ms)
        most_expensive_tool → tool name with highest total token usage
    """
    with _LOCK:
        if not _SESSION_LOG:
            return {
                "total_calls": 0,
                "total_tokens": 0,
                "total_execution_ms": 0,
                "cache_hit_rate_pct": 0,
                "alerts_fired": 0,
                "slow_queries": 0,
                "by_tool": {},
                "most_expensive_tool": "none",
                "message": "No tool calls tracked yet this session.",
            }

        total_calls    = len(_SESSION_LOG)
        total_tokens   = sum(e["estimated_tokens"] for e in _SESSION_LOG)
        total_ms       = sum(e["execution_ms"] for e in _SESSION_LOG)
        cache_hits     = sum(1 for e in _SESSION_LOG if e["cache_hit"])
        alerts_fired   = sum(1 for e in _SESSION_LOG if e["token_alert"])
        slow_queries   = sum(1 for e in _SESSION_LOG if e["slow_query"])
        cache_hit_rate = round(cache_hits / total_calls * 100, 1)

        # Per-tool breakdown
        by_tool: dict = {}
        for e in _SESSION_LOG:
            t = e["tool_name"]
            if t not in by_tool:
                by_tool[t] = {
                    "calls": 0,
                    "total_tokens": 0,
                    "total_ms": 0,
                    "cache_hits": 0,
                }
            by_tool[t]["calls"]        += 1
            by_tool[t]["total_tokens"] += e["estimated_tokens"]
            by_tool[t]["total_ms"]     += e["execution_ms"]
            by_tool[t]["cache_hits"]   += 1 if e["cache_hit"] else 0

        # Add average execution time per tool
        for t in by_tool:
            calls = by_tool[t]["calls"]
            by_tool[t]["avg_ms"] = round(by_tool[t]["total_ms"] / calls, 1)

        # Find most expensive tool by total tokens
        most_expensive = max(by_tool, key=lambda t: by_tool[t]["total_tokens"])

        return {
            "total_calls":        total_calls,
            "total_tokens":       total_tokens,
            "total_execution_ms": round(total_ms, 1),
            "cache_hit_rate_pct": cache_hit_rate,
            "alerts_fired":       alerts_fired,
            "slow_queries":       slow_queries,
            "by_tool":            by_tool,
            "most_expensive_tool": most_expensive,
        }


def get_recent_entries(n: int = 10) -> list:
    """
    Returns the N most recent log entries from the current session.
    Used by Performance Agent to show the last few tool calls.

    Parameters:
        n : int — number of entries to return (default 10)
    """
    with _LOCK:
        return _SESSION_LOG[-n:]


def reset_session_log():
    """
    Clears the in-memory session log.
    Useful at the start of a new work session or before running tests.
    Does NOT delete the on-disk log file — that persists across sessions.
    """
    with _LOCK:
        _SESSION_LOG.clear()
