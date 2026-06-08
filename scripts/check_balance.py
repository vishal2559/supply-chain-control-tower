# =============================================================================
# scripts/check_balance.py
# Supply Chain Control Tower — OpenRouter Balance Monitor
# =============================================================================
#
# PURPOSE:
#   Checks your OpenRouter credit balance and warns you when it drops
#   below the threshold set in config/settings.yaml (default: $5.00).
#
# HOW TO RUN:
#   cd "C:\Users\preet\Documents\AI Work\supply_chain_mcp_project"
#   python scripts\check_balance.py
#
# SCHEDULE IT (optional):
#   Run once a day via Windows Task Scheduler to get automatic alerts.
#
# =============================================================================

import os           # For reading environment variables and file paths
import sys          # For sys.exit() when something goes wrong
import json         # For reading/writing the balance log file
import requests     # For making HTTP calls to the OpenRouter API
from datetime import datetime  # For timestamping log entries
from pathlib import Path       # For creating directories safely

# ── Step 1: Fix Python path ───────────────────────────────────────────────────
# This ensures Python can find our config and supply_chain modules
# regardless of which folder you run the script from.
# os.path.abspath(__file__) = full path to THIS file
# dirname twice = go up two levels (scripts\ → project root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ── Step 2: Load settings ─────────────────────────────────────────────────────
# get_setting() reads a value from config/settings.yaml using dot notation.
# Example: get_setting("llm_providers.fallback.balance_alert_threshold")
# reads the YAML key: llm_providers → fallback → balance_alert_threshold
from config.settings_loader import get_setting

# ── Step 3: Load the API key from .env file ───────────────────────────────────
# We use python-dotenv to read the .env file at the project root.
# This loads OPENROUTER_API_KEY into os.environ so we can read it safely.
# The key never appears in this code — it stays in the .env file only.
try:
    from dotenv import load_dotenv
    # Load .env from the project root folder
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    # dotenv not installed — we'll try reading from Windows env vars directly
    pass


def get_api_key():
    """
    Reads the OpenRouter API key from environment variables.
    
    First tries the .env file (loaded above by dotenv).
    Falls back to Windows system environment variables.
    
    Returns the key string, or exits with an error if not found.
    """
    # get_setting returns the NAME of the env var, not the key itself
    # That name is "OPENROUTER_API_KEY" as set in settings.yaml
    env_var_name = get_setting("llm_providers.fallback.api_key_env_var")
    
    # os.environ.get() reads the actual value from environment variables
    api_key = os.environ.get(env_var_name)
    
    if not api_key:
        print(f"ERROR: Environment variable '{env_var_name}' not found.")
        print("Make sure your .env file exists at the project root and contains:")
        print(f"  {env_var_name}=sk-or-v1-your-key-here")
        sys.exit(1)  # Exit with error code 1 = failure
    
    return api_key


def check_balance(api_key):
    """
    Calls the OpenRouter API to get current credit balance.
    
    OpenRouter endpoint: GET https://openrouter.ai/api/v1/auth/key
    This endpoint returns information about the API key including credits used.
    
    Returns a dict with balance information, or None if the call failed.
    """
    base_url = get_setting("llm_providers.fallback.base_url")
    # The auth/key endpoint tells us about our key's usage and limits
    url = f"{base_url}/auth/key"
    
    headers = {
        # Authorization header — standard Bearer token format
        # Every OpenRouter API call requires this header
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    try:
        # requests.get() makes an HTTP GET request to the URL
        # timeout=10 means: give up after 10 seconds if no response
        response = requests.get(url, headers=headers, timeout=10)
        
        # raise_for_status() throws an error if the HTTP status is 4xx or 5xx
        # (e.g. 401 Unauthorized = bad API key, 429 = rate limited)
        response.raise_for_status()
        
        # Parse the JSON response body into a Python dict
        data = response.json()
        return data
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to OpenRouter. Check your internet connection.")
        return None
    except requests.exceptions.Timeout:
        print("ERROR: OpenRouter API timed out after 10 seconds.")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: OpenRouter API returned an error: {e}")
        if response.status_code == 401:
            print("Your API key appears to be invalid. Check your .env file.")
        return None


def parse_balance(data):
    """
    Extracts the usable credit balance from the OpenRouter API response.
    
    OpenRouter returns balance as: data.limit - data.usage
    If limit is None, it means you have no hard credit cap set (unlimited).
    In that case we return the raw usage so you can still see spend.
    
    Returns (balance_usd, usage_usd, limit_usd) as floats.
    """
    if not data or "data" not in data:
        return None, None, None
    
    info = data["data"]
    
    # usage = how much you have spent so far (in USD)
    usage = float(info.get("usage", 0))
    
    # limit = your total credit limit (None = unlimited / pay-as-you-go)
    limit = info.get("limit")
    
    if limit is not None:
        limit = float(limit)
        # Remaining balance = what you bought minus what you spent
        balance = limit - usage
    else:
        # No limit set = pay-as-you-go account
        # We can't calculate remaining balance without a limit
        balance = None
    
    return balance, usage, limit


def notify_low_balance(balance, threshold):
    """
    Sends a Windows desktop notification when balance is below threshold.
    
    Uses the same notification system as the rest of the project.
    Falls back to a printed warning if desktop notifications aren't available.
    """
    message = (
        f"OpenRouter balance is ${balance:.2f} — "
        f"below the ${threshold:.2f} alert threshold. "
        f"Top up at https://openrouter.ai/credits"
    )
    
    # Try Windows toast notification first
    try:
        from winotify import Notification, audio
        toast = Notification(
            app_id="Supply Chain Control Tower",
            title="⚠️  Low OpenRouter Balance",
            msg=message,
            duration="long",
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
        print("Desktop notification sent.")
    except Exception:
        # winotify not installed or failed — print to terminal instead
        print("\n" + "=" * 60)
        print("⚠️  LOW BALANCE WARNING")
        print(message)
        print("=" * 60 + "\n")


def log_balance(balance, usage, limit):
    """
    Saves the balance check result to logs/balance_log.json.
    
    Appends a new entry each time the script runs.
    Keeps the last 30 entries so you can see balance history over time.
    """
    log_path = os.path.join(PROJECT_ROOT, "logs", "balance_log.json")
    
    # Create the logs directory if it doesn't exist yet
    Path(os.path.dirname(log_path)).mkdir(parents=True, exist_ok=True)
    
    # Build the log entry for this check
    entry = {
        "timestamp": datetime.now().isoformat(),  # e.g. "2025-01-15T09:30:00"
        "balance_usd": round(balance, 4) if balance is not None else None,
        "usage_usd": round(usage, 4) if usage is not None else None,
        "limit_usd": round(limit, 4) if limit is not None else None,
    }
    
    # Load existing log entries (if the file already exists)
    existing = []
    if os.path.exists(log_path):
        try:
            with open(log_path, encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = []  # If file is corrupt, start fresh
    
    # Append the new entry
    existing.append(entry)
    
    # Keep only the most recent 30 entries to prevent the file growing forever
    existing = existing[-30:]
    
    # Write back to the file
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)
    
    print(f"Balance logged to: logs/balance_log.json")


def main():
    """
    Main function — runs the full balance check sequence:
    1. Get API key
    2. Call OpenRouter API
    3. Parse the balance
    4. Compare against threshold
    5. Notify if low
    6. Log the result
    """
    print("=" * 50)
    print("  OpenRouter Balance Check")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Step 1: Get API key from .env
    api_key = get_api_key()
    print("API key loaded. Checking balance...")
    
    # Step 2: Call the API
    data = check_balance(api_key)
    if data is None:
        print("Balance check failed. See errors above.")
        sys.exit(1)
    
    # Step 3: Parse the response
    balance, usage, limit = parse_balance(data)
    
    # Step 4: Display results
    print()
    if usage is not None:
        print(f"  Usage so far:  ${usage:.4f}")
    if limit is not None:
        print(f"  Credit limit:  ${limit:.4f}")
    if balance is not None:
        print(f"  Remaining:     ${balance:.4f}")
    else:
        print("  Account type:  Pay-as-you-go (no credit limit set)")
        print(f"  Total spent:   ${usage:.4f}")
    
    # Step 5: Check against threshold and alert if needed
    threshold = float(get_setting("llm_providers.fallback.balance_alert_threshold"))
    print(f"  Alert below:   ${threshold:.2f}")
    print()
    
    if balance is not None and balance < threshold:
        print(f"WARNING: Balance ${balance:.4f} is below threshold ${threshold:.2f}!")
        notify_low_balance(balance, threshold)
    elif balance is not None:
        print(f"OK: Balance is healthy (${balance:.4f} remaining).")
    else:
        print("INFO: Pay-as-you-go account — no balance limit to check.")
    
    # Step 6: Log the result
    log_balance(balance, usage, limit)
    
    print()
    print("Done.")


# This block runs main() only when you execute this file directly.
# It does NOT run if another file imports this module.
if __name__ == "__main__":
    main()