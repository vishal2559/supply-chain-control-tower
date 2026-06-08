# src/supply_chain/security_guard.py
# Supply Chain Control Tower — Security Guard
# =============================================================================
#
# PURPOSE:
#   Enforces security rules across all 12 MCP agents:
#     1. Read-only mode  — agents can only SELECT, never write/delete data
#     2. SQL whitelist   — blocks any query containing write operations
#     3. Audit logging   — every tool call logged with timestamp + input
#     4. Rate limiting   — blocks rapid repeated calls (abuse protection)
#
# WHY THIS EXISTS:
#   Your supply chain data must never be accidentally or maliciously modified.
#   Even if someone crafted a prompt injection attack through a tool parameter,
#   security_guard.py is a second layer of defence (after input_validation.py).
#
# HOW TO USE IN AN MCP SERVER:
#
#   1. Log every tool call at the start:
#      from supply_chain.security_guard import audit_log, check_read_only
#
#      @mcp.tool()
#      def get_delayed_shipments() -> list:
#          audit_log("get_delayed_shipments", "shipping-delay-agent")
#          ...
#
#   2. Validate any SQL query before running it:
#      from supply_chain.security_guard import validate_sql
#      safe, reason = validate_sql(my_query)
#      if not safe:
#          return {"error": reason}
#
# SETTINGS THAT CONTROL THIS MODULE (all in config/settings.yaml):
#   security.read_only_mode          → true/false
#   security.log_all_tool_calls      → true/false
#   security.audit_log_path          → where to write audit log
#   security.block_write_operations  → true/false
#   security.allowed_sql_operations  → list of permitted SQL keywords
#   security.max_calls_per_minute    → rate limit threshold
#   security.rate_limit_window_seconds → window for rate limiting
#
# =============================================================================

import os
import sys
import json
import time
import threading
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
))))

from config.settings_loader import get_setting, get_log_path

# ─── Thread lock ──────────────────────────────────────────────────────────────
_LOCK = threading.Lock()

# ─── Rate limit tracker ───────────────────────────────────────────────────────
# Tracks call timestamps per tool name for rate limiting
# Format: { "tool_name": [timestamp1, timestamp2, ...] }
_CALL_TIMES: dict = defaultdict(list)


# ─── SQL write keywords to block ─────────────────────────────────────────────
# These keywords must never appear in any SQL query run by the agents.
# This list is intentionally broad — better to block too much than too little.
_BLOCKED_SQL_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE",
    "ALTER", "CREATE", "REPLACE", "UPSERT", "MERGE",
    "ATTACH", "DETACH", "PRAGMA",
]


# ─── Audit log writer ─────────────────────────────────────────────────────────

def audit_log(
    tool_name:  str,
    agent_name: str,
    input_data: dict = None,
    notes:      str  = None,
):
    """
    Logs one tool call to the audit log file.

    Call this at the very start of every tool function, before any logic runs.
    This ensures even failed or rejected calls are recorded.

    Parameters:
        tool_name  : str  — name of the tool e.g. "get_delayed_shipments"
        agent_name : str  — which agent e.g. "shipping-delay-agent"
        input_data : dict — any input parameters the tool received (optional)
                           e.g. {"sales_order_no": "SO10001"}
        notes      : str  — any additional context to log (optional)

    Example:
        @mcp.tool()
        def get_shipment_by_order(sales_order_no: str) -> dict:
            audit_log("get_shipment_by_order", "shipping-delay-agent",
                      input_data={"sales_order_no": sales_order_no})
            ...
    """
    if not get_setting("security.log_all_tool_calls", default=True):
        return

    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tool":      tool_name,
        "agent":     agent_name,
        "input":     input_data or {},
        "notes":     notes or "",
    }

    try:
        log_path = get_log_path("security.audit_log_path")
        with _LOCK:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
    except Exception as e:
        # Audit log failure must never crash the tool
        print(f"[security_guard] WARNING: audit log write failed: {e}")


# ─── Read-only mode checker ───────────────────────────────────────────────────

def check_read_only() -> tuple:
    """
    Checks whether read-only mode is active.

    Returns:
        (is_enforced: bool, message: str)

    Usage in a tool that might write data:
        enforced, msg = check_read_only()
        if enforced:
            return {"error": msg}

    For purely read tools this check is optional — read-only mode
    doesn't affect SELECT queries. Use it as a guard on any tool
    that could potentially modify data.
    """
    is_enforced = get_setting("security.read_only_mode", default=True)
    if is_enforced:
        return True, (
            "Read-only mode is active. This system is configured for "
            "data viewing only. No modifications are permitted. "
            "To manage data, use DB Browser for SQLite directly."
        )
    return False, "Read-only mode is inactive."


# ─── SQL validator ────────────────────────────────────────────────────────────

def validate_sql(sql: str) -> tuple:
    """
    Validates a SQL query to ensure it contains only permitted operations.

    Checks the query against the blocked keyword list.
    This is a defence-in-depth measure — even if read_only_mode is somehow
    bypassed, this function blocks write operations at the SQL level.

    Parameters:
        sql : str — the SQL query string to validate

    Returns:
        (is_safe: bool, reason: str)
        is_safe = True  → query is permitted, proceed
        is_safe = False → query is blocked, return the reason as an error

    Example:
        safe, reason = validate_sql("SELECT * FROM shipments WHERE status='DELAYED'")
        # safe = True, reason = "Query is permitted."

        safe, reason = validate_sql("DELETE FROM shipments WHERE sales_order_no='SO10001'")
        # safe = False, reason = "Blocked: query contains 'DELETE' operation..."
    """
    if not get_setting("security.block_write_operations", default=True):
        return True, "Write protection is disabled in settings.yaml."

    # Normalise to uppercase for case-insensitive matching
    sql_upper = sql.upper().strip()

    for keyword in _BLOCKED_SQL_KEYWORDS:
        # Check for keyword as a word (not part of another word)
        # e.g. "SELECT" in "SELECTED" should not trigger
        import re
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sql_upper):
            # Log the blocked attempt to audit log
            audit_log(
                tool_name  = "validate_sql",
                agent_name = "security-guard",
                input_data = {"blocked_keyword": keyword},
                notes      = f"Blocked SQL query containing '{keyword}'"
            )
            return False, (
                f"Security: query contains '{keyword}' which is not permitted. "
                f"Only SELECT operations are allowed. "
                f"This event has been logged to the audit log."
            )

    return True, "Query is permitted."


# ─── Rate limiter ─────────────────────────────────────────────────────────────

def check_rate_limit(tool_name: str) -> tuple:
    """
    Checks whether a tool is being called too rapidly.

    If the same tool is called more than max_calls_per_minute times
    within the rate_limit_window_seconds window, this returns False
    and the tool should return an error rather than executing.

    Parameters:
        tool_name : str — name of the tool being called

    Returns:
        (is_allowed: bool, message: str)

    Example:
        allowed, msg = check_rate_limit("get_delayed_shipments")
        if not allowed:
            return {"error": msg}
    """
    max_calls   = get_setting("security.max_calls_per_minute", default=30)
    window_secs = get_setting("security.rate_limit_window_seconds", default=60)
    now         = time.time()

    with _LOCK:
        # Remove timestamps older than the window
        _CALL_TIMES[tool_name] = [
            t for t in _CALL_TIMES[tool_name]
            if now - t < window_secs
        ]

        call_count = len(_CALL_TIMES[tool_name])

        if call_count >= max_calls:
            audit_log(
                tool_name  = tool_name,
                agent_name = "security-guard",
                notes      = f"Rate limit hit: {call_count} calls in {window_secs}s window"
            )
            return False, (
                f"Rate limit: '{tool_name}' has been called {call_count} times "
                f"in the last {window_secs} seconds (limit: {max_calls}). "
                f"Please wait before calling again."
            )

        # Record this call
        _CALL_TIMES[tool_name].append(now)
        return True, "OK"


# ─── Combined security check ──────────────────────────────────────────────────

def run_security_checks(
    tool_name:  str,
    agent_name: str,
    input_data: dict = None,
    sql:        str  = None,
) -> tuple:
    """
    Runs all security checks in one call.
    Use this at the top of any tool that needs full security enforcement.

    Checks performed (in order):
        1. Audit log the call
        2. Rate limit check
        3. SQL validation (only if sql parameter is provided)

    Parameters:
        tool_name  : str  — tool name for logging
        agent_name : str  — agent name for logging
        input_data : dict — tool input parameters for logging
        sql        : str  — SQL query to validate (optional)

    Returns:
        (passed: bool, error_dict: dict or None)
        passed = True  → all checks passed, proceed normally
        passed = False → a check failed, return error_dict to Claude

    Example (simplest usage):
        passed, error = run_security_checks(
            "get_delayed_shipments", "shipping-delay-agent"
        )
        if not passed:
            return error

    Example (with SQL validation):
        my_sql = "SELECT * FROM shipments WHERE status = ?"
        passed, error = run_security_checks(
            "get_delayed_shipments", "shipping-delay-agent",
            sql=my_sql
        )
        if not passed:
            return error
    """
    # Step 1 — always audit log first
    audit_log(tool_name, agent_name, input_data)

    # Step 2 — rate limit check
    allowed, rate_msg = check_rate_limit(tool_name)
    if not allowed:
        return False, {"error": rate_msg, "security_block": "rate_limit"}

    # Step 3 — SQL validation (only if a query was passed in)
    if sql is not None:
        safe, sql_msg = validate_sql(sql)
        if not safe:
            return False, {"error": sql_msg, "security_block": "sql_blocked"}

    return True, None


# ─── Security status ──────────────────────────────────────────────────────────

def get_security_status() -> dict:
    """
    Returns the current security configuration.
    Used by the Coordinator Agent for health checks.
    """
    return {
        "read_only_mode":       get_setting("security.read_only_mode", default=True),
        "audit_logging":        get_setting("security.log_all_tool_calls", default=True),
        "write_ops_blocked":    get_setting("security.block_write_operations", default=True),
        "max_calls_per_minute": get_setting("security.max_calls_per_minute", default=30),
        "audit_log_path":       get_log_path("security.audit_log_path"),
        "status":               "SECURE",
    }
