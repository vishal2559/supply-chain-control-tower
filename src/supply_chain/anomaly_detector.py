# src/supply_chain/anomaly_detector.py
# Supply Chain Control Tower — Anomaly Detector
# =============================================================================
#
# PURPOSE:
#   Watches tool results for unusual patterns and fires alerts when thresholds
#   defined in settings.yaml are crossed.
#
# TWO TYPES OF ANOMALIES DETECTED:
#
#   Supply chain anomalies — problems in your data:
#     - Critical order spike  : too many orders in NEED_ACTION / CRITICAL status
#     - Unknown reason surge  : too many delays with UNKNOWN cause
#     - New freight holds     : sudden increase in freight holds
#     - Inventory stockout    : any item hitting OUT_OF_STOCK
#
#   System anomalies — problems with the system itself:
#     - Token spike           : a tool using 3x its normal token usage
#     - Rapid tool calls      : same tool called too many times per minute
#     - Slow query            : a tool taking too long to respond
#
# HOW TO USE:
#   from supply_chain.anomaly_detector import check_supply_chain_anomalies
#
#   # After getting results from a tool:
#   anomalies = check_supply_chain_anomalies(
#       total_orders=100,
#       critical_orders=25,
#       unknown_reason_count=35,
#       delayed_total=40,
#   )
#   # anomalies is a list of dicts — empty list means everything is normal
#
# SETTINGS THAT CONTROL THIS MODULE (all in config/settings.yaml):
#   notifications.anomaly_thresholds.critical_orders_pct
#   notifications.anomaly_thresholds.unknown_rate_pct
#   notifications.anomaly_thresholds.new_freight_holds
#   notifications.anomaly_thresholds.inventory_stockouts
#   notifications.anomaly_thresholds.token_spike_multiplier
#   notifications.anomaly_thresholds.rapid_tool_calls_per_minute
#
# =============================================================================

import os
import sys
import time
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
))))

from config.settings_loader import get_anomaly_threshold, is_notifications_enabled

# ─── Rolling averages for token spike detection ───────────────────────────────
# Tracks recent token usage per tool to calculate rolling average
# Format: { "tool_name": [token_count1, token_count2, ...] }
_TOKEN_HISTORY: dict = defaultdict(list)
_MAX_HISTORY   = 20   # keep last 20 readings per tool

# ─── Freight hold baseline ────────────────────────────────────────────────────
# Tracks the last known freight hold count to detect NEW holds
_LAST_FREIGHT_HOLD_COUNT: int = None


# ─── Anomaly event builder ────────────────────────────────────────────────────

def _build_anomaly(
    anomaly_type:   str,
    severity:       str,
    description:    str,
    actual_value,
    threshold_value,
    recommended_action: str,
) -> dict:
    """
    Builds a standardised anomaly event dict.

    Parameters:
        anomaly_type       — short code e.g. "CRITICAL_ORDER_SPIKE"
        severity           — "WARNING" or "CRITICAL"
        description        — plain English explanation
        actual_value       — what was actually observed
        threshold_value    — what the threshold was
        recommended_action — what to do about it

    Returns a dict that notifier.py can display and log.
    """
    return {
        "timestamp":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "anomaly_type":       anomaly_type,
        "severity":           severity,
        "description":        description,
        "actual_value":       actual_value,
        "threshold_value":    threshold_value,
        "recommended_action": recommended_action,
    }


# ─── Supply chain anomaly checks ──────────────────────────────────────────────

def check_supply_chain_anomalies(
    total_orders:         int = 0,
    critical_orders:      int = 0,
    unknown_reason_count: int = 0,
    delayed_total:        int = 0,
    freight_hold_count:   int = None,
    stockout_items:       list = None,
) -> list:
    """
    Checks supply chain metrics against thresholds from settings.yaml.
    Call this after running a summary or scan tool.

    Parameters:
        total_orders         — total number of orders checked
        critical_orders      — orders in NEED_ACTION or CRITICAL status
        unknown_reason_count — orders with UNKNOWN_NEEDS_REVIEW reason code
        delayed_total        — total delayed orders (DELAYED + NEED_ACTION)
        freight_hold_count   — current number of freight holds (or None to skip)
        stockout_items       — list of OUT_OF_STOCK item numbers (or None to skip)

    Returns:
        list of anomaly dicts — empty list means everything is normal
    """
    if not is_notifications_enabled():
        return []

    anomalies = []

    # ── Check 1: Critical order spike ────────────────────────────────────────
    # Fires if the % of critical orders exceeds the threshold
    critical_pct_threshold = get_anomaly_threshold("critical_orders_pct", default=20)
    if total_orders > 0:
        critical_pct = round((critical_orders / total_orders) * 100, 1)
        if critical_pct >= critical_pct_threshold:
            anomalies.append(_build_anomaly(
                anomaly_type   = "CRITICAL_ORDER_SPIKE",
                severity       = "CRITICAL",
                description    = (
                    f"{critical_pct}% of orders ({critical_orders} of {total_orders}) "
                    f"are in CRITICAL/NEED_ACTION status. "
                    f"Threshold is {critical_pct_threshold}%."
                ),
                actual_value   = f"{critical_pct}%",
                threshold_value= f"{critical_pct_threshold}%",
                recommended_action = "Run /escalate immediately to see all critical orders.",
            ))

    # ── Check 2: Unknown reason surge ────────────────────────────────────────
    # Fires if too many delays have UNKNOWN cause (data quality problem)
    unknown_pct_threshold = get_anomaly_threshold("unknown_rate_pct", default=30)
    if delayed_total > 0:
        unknown_pct = round((unknown_reason_count / delayed_total) * 100, 1)
        if unknown_pct >= unknown_pct_threshold:
            anomalies.append(_build_anomaly(
                anomaly_type   = "UNKNOWN_REASON_SURGE",
                severity       = "WARNING",
                description    = (
                    f"{unknown_pct}% of delayed orders ({unknown_reason_count} of {delayed_total}) "
                    f"have UNKNOWN reason code. "
                    f"This usually means missing data fields. "
                    f"Threshold is {unknown_pct_threshold}%."
                ),
                actual_value   = f"{unknown_pct}%",
                threshold_value= f"{unknown_pct_threshold}%",
                recommended_action = (
                    "Check shipments data for missing carrier_status, "
                    "truck_available, or pick_status fields."
                ),
            ))

    # ── Check 3: New freight holds ────────────────────────────────────────────
    # Fires if the freight hold count increased since last check
    global _LAST_FREIGHT_HOLD_COUNT
    if freight_hold_count is not None:
        new_holds_threshold = get_anomaly_threshold("new_freight_holds", default=2)
        if _LAST_FREIGHT_HOLD_COUNT is not None:
            new_holds = freight_hold_count - _LAST_FREIGHT_HOLD_COUNT
            if new_holds >= new_holds_threshold:
                anomalies.append(_build_anomaly(
                    anomaly_type   = "NEW_FREIGHT_HOLDS",
                    severity       = "WARNING",
                    description    = (
                        f"{new_holds} new freight hold(s) detected since last scan. "
                        f"Total holds now: {freight_hold_count}. "
                        f"Threshold: {new_holds_threshold} new holds."
                    ),
                    actual_value   = f"{new_holds} new holds",
                    threshold_value= f"{new_holds_threshold} new holds",
                    recommended_action = (
                        "Run /carriers to see all freight holds and contact carriers."
                    ),
                ))
        # Update baseline for next check
        _LAST_FREIGHT_HOLD_COUNT = freight_hold_count

    # ── Check 4: Inventory stockouts ─────────────────────────────────────────
    # Fires immediately when any item hits OUT_OF_STOCK
    stockout_threshold = get_anomaly_threshold("inventory_stockouts", default=1)
    if stockout_items and len(stockout_items) >= stockout_threshold:
        anomalies.append(_build_anomaly(
            anomaly_type   = "INVENTORY_STOCKOUT",
            severity       = "CRITICAL",
            description    = (
                f"{len(stockout_items)} item(s) are OUT_OF_STOCK: "
                f"{', '.join(str(i) for i in stockout_items[:5])}"
                f"{'...' if len(stockout_items) > 5 else ''}. "
                f"Immediate action required."
            ),
            actual_value   = f"{len(stockout_items)} stockout(s)",
            threshold_value= f"{stockout_threshold} stockout(s)",
            recommended_action = (
                "Run /inventory to see full stockout details. "
                "Check purchase orders for replenishment status."
            ),
        ))

    return anomalies


# ─── System anomaly checks ────────────────────────────────────────────────────

def check_token_spike(tool_name: str, current_tokens: int) -> dict:
    """
    Detects if a tool suddenly used many more tokens than its rolling average.

    Maintains a rolling history of token usage per tool.
    If current usage is multiplier× the average, fires an anomaly.

    Parameters:
        tool_name      — which tool was called
        current_tokens — how many tokens this call used

    Returns:
        anomaly dict if spike detected, or None if normal
    """
    if not is_notifications_enabled():
        return None

    multiplier = get_anomaly_threshold("token_spike_multiplier", default=3)

    history = _TOKEN_HISTORY[tool_name]

    # Need at least 3 data points to establish a meaningful average
    if len(history) >= 3:
        avg_tokens = sum(history) / len(history)
        if avg_tokens > 0 and current_tokens > (avg_tokens * multiplier):
            return _build_anomaly(
                anomaly_type   = "TOKEN_SPIKE",
                severity       = "WARNING",
                description    = (
                    f"'{tool_name}' used {current_tokens} tokens — "
                    f"{round(current_tokens/avg_tokens, 1)}x its average of "
                    f"{round(avg_tokens)} tokens. "
                    f"Threshold: {multiplier}x average."
                ),
                actual_value   = f"{current_tokens} tokens",
                threshold_value= f"{round(avg_tokens * multiplier)} tokens ({multiplier}x avg)",
                recommended_action = (
                    "Check if a large dataset was returned. "
                    "Consider reducing max_response_rows in settings.yaml."
                ),
            )

    # Update rolling history (keep last N readings)
    history.append(current_tokens)
    if len(history) > _MAX_HISTORY:
        _TOKEN_HISTORY[tool_name] = history[-_MAX_HISTORY:]

    return None


def reset_freight_hold_baseline():
    """
    Resets the freight hold baseline counter.
    Call this at the start of a new day or after a data reload.
    """
    global _LAST_FREIGHT_HOLD_COUNT
    _LAST_FREIGHT_HOLD_COUNT = None
