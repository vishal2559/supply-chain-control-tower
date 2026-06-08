# src/supply_chain/cache_manager.py
# Supply Chain Control Tower — In-Memory TTL Cache
# =============================================================================
#
# PURPOSE:
#   Loads data from SQLite once per session and holds it in memory.
#   All subsequent requests for the same data return from memory instantly,
#   instead of reading from the database every single time.
#
# WHAT IS A TTL CACHE?
#   TTL = Time To Live.
#   When data is loaded into the cache, a timestamp is recorded.
#   If a tool requests data and the cache is younger than cache_ttl_seconds,
#   the cached copy is returned.
#   Once the TTL expires, the next request reloads from SQLite (fresh data).
#
# WHY THIS IS SAFE FOR SUPPLY CHAIN DATA:
#   Supply chain data (shipments, inventory) is updated once or twice a day,
#   not every second. Holding it in memory for 5 minutes (300 seconds) is
#   safe and dramatically reduces database load.
#
# HOW TO USE IN AN MCP SERVER:
#   # OLD way (reads SQLite every time):
#   rows = load_shipments(DB_FILE)
#
#   # NEW way (reads SQLite once, returns from memory after that):
#   from supply_chain.cache_manager import get_cached
#   rows = get_cached("shipments", load_shipments, DB_FILE)
#
# SETTINGS THAT CONTROL THIS MODULE (all in config/settings.yaml):
#   performance.cache_enabled       → true/false master switch
#   performance.cache_ttl_seconds   → how long cache stays fresh (default: 300)
#   performance.cache_max_rows      → safety cap on rows stored (default: 50000)
#
# PHASE 2 NOTE (Docker/Cloud):
#   This cache is in-memory per process. In Phase 2, this module will be
#   updated to use Redis as a shared cache across containers. The interface
#   (get_cached, invalidate_cache) stays identical — only the backend changes.
#
# =============================================================================

import time
import threading
import sys
import os

# ─── Path setup ──────────────────────────────────────────────────────────────
# Ensures config/ is findable regardless of where Claude Desktop launches from
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
))))

from config.settings_loader import (
    get_setting,
    is_cache_enabled,
    get_cache_ttl,
)


# ─── Cache store ─────────────────────────────────────────────────────────────
#
# _CACHE is a dictionary where:
#   key   = a string identifying what is cached (e.g. "shipments", "inventory")
#   value = a dict with two fields:
#             "data"       → the actual list of rows loaded from SQLite
#             "loaded_at"  → the timestamp (seconds since epoch) when it was loaded
#
# Example after first call to get_cached("shipments", ...):
#   _CACHE = {
#       "shipments": {
#           "data": [{...}, {...}, ...],   ← list of row dicts
#           "loaded_at": 1717123456.789    ← Unix timestamp
#       }
#   }

_CACHE: dict = {}

# _LOCK ensures thread safety.
# If two tools are called at almost the same time, the lock prevents them
# from both triggering a database load simultaneously.
# One waits while the other loads, then reuses the result.
_LOCK = threading.Lock()


# ─── Cache statistics ─────────────────────────────────────────────────────────
#
# These counters track how well the cache is working.
# get_cache_stats() returns these so you can see the hit rate.

_STATS = {
    "hits":   0,    # times data was returned from memory
    "misses": 0,    # times data had to be loaded from SQLite
    "expirations": 0,  # times the TTL expired and data was reloaded
}


# ─── Main function: get_cached ────────────────────────────────────────────────

def get_cached(cache_key: str, loader_fn, *loader_args) -> list:
    """
    Returns data from cache if fresh, otherwise loads from SQLite and caches it.

    Parameters:
        cache_key  : str      — unique name for this dataset
                                e.g. "shipments", "inventory", "freight"
        loader_fn  : callable — the function that loads data from SQLite
                                e.g. load_shipments, load_inventory
        *loader_args          — arguments to pass to loader_fn
                                e.g. the DB_FILE path

    Returns:
        list of row dicts — same format as what loader_fn returns directly

    Examples:
        # Cache shipments data
        rows = get_cached("shipments", load_shipments, DB_FILE)

        # Cache inventory data
        rows = get_cached("inventory", load_inventory, DB_FILE)

        # Cache freight data
        rows = get_cached("freight", load_freight, DB_FILE)
    """

    # If caching is disabled in settings.yaml, always load fresh from SQLite.
    # This is useful for debugging — you can turn off caching without code changes.
    if not is_cache_enabled():
        return loader_fn(*loader_args)

    ttl_seconds = get_cache_ttl()
    max_rows    = get_setting("performance.cache_max_rows", default=50000)
    now         = time.time()

    with _LOCK:

        # ── Check if we have a cached copy and whether it is still fresh ──────
        if cache_key in _CACHE:
            entry      = _CACHE[cache_key]
            age        = now - entry["loaded_at"]  # seconds since it was loaded
            is_fresh   = age < ttl_seconds

            if is_fresh:
                # Cache HIT — data is in memory and still fresh
                # Return immediately without touching SQLite
                _STATS["hits"] += 1
                return entry["data"]
            else:
                # Cache EXPIRED — data is too old, need to reload
                # The old data is still in _CACHE but we will replace it below
                _STATS["expirations"] += 1

        # ── Cache MISS or EXPIRED — load from SQLite ─────────────────────────
        # This is the only time we actually read from the database
        _STATS["misses"] += 1

        data = loader_fn(*loader_args)

        # Safety cap: never cache more than cache_max_rows rows
        # This protects against accidentally caching a huge dataset
        if len(data) > max_rows:
            # Log a warning and return uncached (don't crash — just skip caching)
            print(
                f"[cache_manager] WARNING: '{cache_key}' has {len(data)} rows "
                f"which exceeds cache_max_rows ({max_rows}). "
                f"Returning data without caching. "
                f"Increase cache_max_rows in settings.yaml if needed."
            )
            return data

        # Store in cache with current timestamp
        _CACHE[cache_key] = {
            "data":      data,
            "loaded_at": now,
        }

        return data


# ─── Invalidate specific cache entry ─────────────────────────────────────────

def invalidate_cache(cache_key: str = None):
    """
    Clears one cache entry (or all entries if no key given).

    When to use:
        - After running a database reload script (csv_to_sqlite.py)
        - After manual data changes in DB Browser for SQLite
        - In tests: call invalidate_cache() before each test to start fresh

    Parameters:
        cache_key : str or None
            If given, clears only that entry (e.g. "shipments")
            If None, clears the entire cache (all tables)

    Examples:
        invalidate_cache("shipments")   → only shipments reloads next call
        invalidate_cache()              → everything reloads next call
    """
    with _LOCK:
        if cache_key is None:
            _CACHE.clear()
        elif cache_key in _CACHE:
            del _CACHE[cache_key]


# ─── Cache statistics ─────────────────────────────────────────────────────────

def get_cache_stats() -> dict:
    """
    Returns a summary of cache performance.

    Used by the Performance Agent (performance_mcp_server.py) to expose
    cache health to Claude Desktop.

    Returns a dict with:
        hits        → number of times data was served from memory
        misses      → number of times SQLite had to be read
        expirations → number of times TTL expired and data was reloaded
        hit_rate_pct → percentage of requests served from cache (0–100)
        cached_keys → list of what is currently in the cache
        cache_ages  → how old (seconds) each cached entry is
        ttl_seconds → current TTL setting from settings.yaml
        enabled     → whether caching is active
    """
    with _LOCK:
        total = _STATS["hits"] + _STATS["misses"]
        hit_rate = round((_STATS["hits"] / total * 100), 1) if total > 0 else 0.0

        now = time.time()
        cache_ages = {
            key: round(now - entry["loaded_at"], 1)
            for key, entry in _CACHE.items()
        }

        return {
            "hits":          _STATS["hits"],
            "misses":        _STATS["misses"],
            "expirations":   _STATS["expirations"],
            "hit_rate_pct":  hit_rate,
            "cached_keys":   list(_CACHE.keys()),
            "cache_ages_sec": cache_ages,
            "ttl_seconds":   get_cache_ttl(),
            "enabled":       is_cache_enabled(),
            "total_requests": total,
        }


# ─── Cache status for health checks ──────────────────────────────────────────

def get_cache_status() -> str:
    """
    Returns a one-line status string for health check tools.
    Used by the Coordinator Agent to check cache health.

    Returns one of:
        "ENABLED  | 3 keys cached | hit rate 78.5%"
        "DISABLED | caching turned off in settings.yaml"
    """
    if not is_cache_enabled():
        return "DISABLED | caching turned off in settings.yaml"

    stats = get_cache_stats()
    return (
        f"ENABLED  | "
        f"{len(stats['cached_keys'])} keys cached | "
        f"hit rate {stats['hit_rate_pct']}% | "
        f"TTL {stats['ttl_seconds']}s"
    )
