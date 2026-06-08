# config/settings_loader.py
# Supply Chain Control Tower — Central Settings Loader
# =============================================================================
#
# PURPOSE:
# ...

"""
Central settings loader for the Supply Chain Control Tower.

Implements a single-load configuration pattern: settings.yaml is parsed
once at module import time and all 12 MCP agents read from the same
in-memory dict via get_setting(). This ensures consistent behaviour
across agents and means a single settings.yaml change propagates
everywhere without restarting individual servers.
"""

import os        # ← imports start here
import yaml

# ─── Find the project root ────────────────────────────────────────────────────
#
# This file lives at: project_root/config/settings_loader.py
# os.path.abspath(__file__)          → full path to this file
# os.path.dirname(...)               → the config/ folder
# os.path.dirname(... again ...)     → the project root folder
#
# We need the project root so we can build absolute paths to settings.yaml
# and to the database file, regardless of where Python is run from.

_THIS_FILE   = os.path.abspath(__file__)
_CONFIG_DIR  = os.path.dirname(_THIS_FILE)
_PROJECT_ROOT = os.path.dirname(_CONFIG_DIR)

# Full path to settings.yaml
_SETTINGS_PATH = os.path.join(_CONFIG_DIR, "settings.yaml")


# ─── Load settings once at import time ───────────────────────────────────────
#
# We load the YAML file once when this module is first imported.
# All subsequent calls to get_setting() read from this in-memory dict.
# This avoids reading the file from disk on every tool call.

def _load_settings() -> dict:
    """
    Opens and parses settings.yaml.
    Returns a dict of all settings.
    If the file doesn't exist or has a YAML error, raises a clear error message.
    """
    if not os.path.exists(_SETTINGS_PATH):
        raise FileNotFoundError(
            f"settings.yaml not found at: {_SETTINGS_PATH}\n"
            f"Please create it from the settings.yaml template."
        )
    with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        raise ValueError(f"settings.yaml is empty at: {_SETTINGS_PATH}")
    return data

# Load once at module import time
_SETTINGS: dict = _load_settings()


# ─── Core getter ─────────────────────────────────────────────────────────────

def get_setting(key_path: str, default=None):
    """
    Gets any value from settings.yaml using dot notation.

    Examples:
        get_setting("database.path")                  → "data/supply_chain.db"
        get_setting("performance.cache_ttl_seconds")  → 300
        get_setting("security.read_only_mode")        → True
        get_setting("notifications.enabled")          → True

    Parameters:
        key_path : str  — dot-separated path into the YAML structure
        default         — value to return if the key does not exist
                          (default: None, which will raise KeyError if not set)

    Returns the value at that path, or raises KeyError if missing and
    no default was given.
    """
    keys = key_path.split(".")
    node = _SETTINGS

    for key in keys:
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            if default is not None:
                return default
            raise KeyError(
                f"Setting '{key_path}' not found in settings.yaml. "
                f"Add it under the correct section."
            )
    return node


# ─── Convenience helpers ──────────────────────────────────────────────────────
# These are shortcuts for the most frequently used settings.
# Every MCP server calls get_database_path() instead of reading the YAML directly.

def get_database_path() -> str:
    """
    Returns the absolute path to supply_chain.db.

    Why absolute path?
    Claude Desktop launches MCP servers from an unknown working directory.
    A relative path like "data/supply_chain.db" would break because Python
    wouldn't know which folder to look in.
    We resolve it to an absolute path using the project root.

    Usage:
        from config.settings_loader import get_database_path
        DB_FILE = get_database_path()
    """
    relative_path = get_setting("database.path")
    return os.path.join(_PROJECT_ROOT, relative_path)


def get_log_path(log_key: str) -> str:
    """
    Returns the absolute path to any log file defined in settings.yaml.

    Parameters:
        log_key : str — dot-notation key for the log path
                        e.g. "performance.token_log_path"
                             "security.audit_log_path"
                             "notifications.anomaly_log_path"

    Usage:
        from config.settings_loader import get_log_path
        LOG_FILE = get_log_path("security.audit_log_path")
    """
    relative_path = get_setting(log_key)
    full_path = os.path.join(_PROJECT_ROOT, relative_path)

    # Ensure the logs/ directory exists — create it if not.
    # This prevents FileNotFoundError when the first log entry is written.
    log_dir = os.path.dirname(full_path)
    os.makedirs(log_dir, exist_ok=True)

    return full_path


def get_max_response_rows() -> int:
    """
    Returns the maximum number of rows any list tool should return to Claude.

    Why this matters:
    Returning 500 rows to Claude uses thousands of tokens and slows responses.
    This cap ensures tools return a manageable summary, not a data dump.

    Usage:
        from config.settings_loader import get_max_response_rows
        rows = rows[:get_max_response_rows()]
    """
    return get_setting("performance.max_response_rows", default=100)


def get_cache_ttl() -> int:
    """
    Returns the cache TTL in seconds.

    Usage:
        from config.settings_loader import get_cache_ttl
        ttl = get_cache_ttl()
    """
    return get_setting("performance.cache_ttl_seconds", default=300)


def is_cache_enabled() -> bool:
    """
    Returns True if the in-memory cache is enabled.

    Usage:
        from config.settings_loader import is_cache_enabled
        if is_cache_enabled(): ...
    """
    return get_setting("performance.cache_enabled", default=True)


def is_read_only_mode() -> bool:
    """
    Returns True if read-only mode is enforced.
    All agents should check this before running any query.

    Usage:
        from config.settings_loader import is_read_only_mode
        if not is_read_only_mode(): raise PermissionError(...)
    """
    return get_setting("security.read_only_mode", default=True)


def is_token_tracking_enabled() -> bool:
    """
    Returns True if token usage tracking is active.

    Usage:
        from config.settings_loader import is_token_tracking_enabled
    """
    return get_setting("performance.token_tracking_enabled", default=True)


def get_token_alert_threshold() -> int:
    """
    Returns the token count above which a single tool call triggers an alert.

    Usage:
        from config.settings_loader import get_token_alert_threshold
    """
    return get_setting("performance.token_alert_threshold", default=2000)


def is_notifications_enabled() -> bool:
    """
    Returns True if the notification system is active.

    Usage:
        from config.settings_loader import is_notifications_enabled
    """
    return get_setting("notifications.enabled", default=True)


def get_anomaly_threshold(threshold_key: str, default=None):
    """
    Returns a specific anomaly threshold value from settings.yaml.

    Parameters:
        threshold_key : str — the threshold name under notifications.anomaly_thresholds
                              e.g. "critical_orders_pct"
                                   "new_freight_holds"
                                   "inventory_stockouts"

    Usage:
        from config.settings_loader import get_anomaly_threshold
        pct = get_anomaly_threshold("critical_orders_pct")  # returns 20
    """
    return get_setting(f"notifications.anomaly_thresholds.{threshold_key}", default=default)


def get_llm_fallback_config() -> dict:
    """
    Returns the full fallback LLM provider config dict.
    Used by scripts/fallback_chat.py to connect to OpenRouter.

    Returns a dict with keys: name, base_url, model, api_key_env_var,
                               max_tokens, temperature

    Usage:
        from config.settings_loader import get_llm_fallback_config
        config = get_llm_fallback_config()
        api_key = os.environ.get(config["api_key_env_var"])
    """
    return get_setting("llm_providers.fallback")


def is_agent_enabled(agent_key: str) -> bool:
    """
    Returns True if a specific agent is enabled in settings.yaml.

    Parameters:
        agent_key : str — the agent key under the agents: block
                          e.g. "coordinator_agent", "performance_agent"

    Usage:
        from config.settings_loader import is_agent_enabled
        if not is_agent_enabled("coordinator_agent"):
            print("Coordinator agent is disabled in settings.yaml")
    """
    return get_setting(f"agents.{agent_key}", default=False)


def get_project_root() -> str:
    """
    Returns the absolute path to the project root folder.
    Useful when any script needs to build paths to project files.

    Usage:
        from config.settings_loader import get_project_root
        claude_md_path = os.path.join(get_project_root(), "CLAUDE.md")
    """
    return _PROJECT_ROOT
