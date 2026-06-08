# =============================================================================
# scripts/fallback_chat.py
# Supply Chain Control Tower — OpenRouter Fallback Chat
# =============================================================================
#
# PURPOSE:
#   A terminal chat interface using OpenRouter when Claude Desktop hits
#   its usage limit. Tries free models in a chain, falls back to paid.
#
# HOW TO RUN:
#   cd "C:\Users\preet\Documents\AI Work\supply_chain_mcp_project"
#   python scripts\fallback_chat.py
#
# COMMANDS DURING CHAT:
#   quit      — exit the chat
#   balance   — check your OpenRouter credit balance
#   model     — show which model is currently active
#   models    — show all models in the fallback chain
#   paid      — switch to the paid model
#   free      — restart from the first free model in the chain
#   clear     — clear conversation history (start fresh)
#   help      — show these commands
#
# MODEL CHAIN (tried in order when a model fails):
#   1. google/gemma-4-31b-it:free
#   2. meta-llama/llama-3.3-70b-instruct:free
#   3. nousresearch/hermes-3-llama-3.1-405b:free
#   4. qwen/qwen3-coder:free
#   If all free models fail → paid model is used automatically
#
# =============================================================================

import os
import sys
import json
import requests
from datetime import datetime

# ── Fix Python path ───────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ── Load settings ─────────────────────────────────────────────────────────────
from config.settings_loader import get_setting

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    pass


# ── Constants from settings.yaml ─────────────────────────────────────────────
BASE_URL    = get_setting("llm_providers.fallback.base_url")
PAID_MODEL  = get_setting("llm_providers.fallback.paid_model")
MAX_TOKENS  = int(get_setting("llm_providers.fallback.max_tokens"))
TEMPERATURE = float(get_setting("llm_providers.fallback.temperature"))
SITE_URL    = get_setting("llm_providers.fallback.site_url")
SITE_NAME   = get_setting("llm_providers.fallback.site_name")
THRESHOLD   = float(get_setting("llm_providers.fallback.balance_alert_threshold"))

# ── Free model chain ──────────────────────────────────────────────────────────
# Loaded from settings.yaml — llm_providers.fallback.free_model_chain
# This is a list of free models tried in order when one fails.
# get_setting returns the list directly since YAML supports lists.
FREE_MODEL_CHAIN = get_setting("llm_providers.fallback.free_model_chain")

# Safety check — if the chain setting is missing, use a hardcoded default
# so the script never crashes on startup.
if not FREE_MODEL_CHAIN:
    FREE_MODEL_CHAIN = [
        "google/gemma-4-31b-it:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "qwen/qwen3-coder:free",
    ]


# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an AI assistant for the Supply Chain Control Tower,
a multi-agent system built by Vishal that monitors and analyses supply chain
operations including shipments, inventory, freight, warehouse picks, and
purchase orders.

The system uses 12 MCP agents:
- Shipping Delay Agent   — tracks order delays and reason codes
- Inventory Agent        — monitors stock levels and backorders
- PO Agent               — tracks purchase order status
- Freight Agent          — monitors carrier performance and freight holds
- Warehouse Agent        — tracks pick status and warehouse operations
- Investigation Agent    — performs root cause analysis on delayed orders
- Recommendation Agent   — generates prioritised action plans
- CI Agent               — continuous improvement and learning
- Performance Agent      — monitors system performance and token usage
- Coordinator Agent      — routes questions across all agents
- Test Agent             — runs automated test suites
- Memory Agent           — manages cross-session memory

Key business logic:
- Delay statuses: ON_TIME, DELAYED (1-5 days), NEED_ACTION (5+ days)
- Reason codes: FREIGHT_HOLD, BACKORDER, INVENTORY_SHORTAGE,
  TRUCK_NOT_AVAILABLE, CARRIER_DELAY, WAREHOUSE_PICK_DELAY, UNKNOWN_NEEDS_REVIEW
- Inventory statuses: HEALTHY, LOW, CRITICAL, OUT_OF_STOCK, ON_BACKORDER
- Carrier tiers: STRONG (>=85), AVERAGE (>=70), WEAK (>=55), CRITICAL (<55)
- Order ID format: SO10001 (no dashes)
- Tech stack: Python 3.10, FastMCP, SQLite, Streamlit, Windows

Note: In fallback mode you do not have direct access to the live SQLite
database or MCP tools. You can answer questions, explain concepts, help
debug code, write Python code, and discuss supply chain strategy.
For live data queries, use Claude Desktop with the MCP agents connected.

When writing code, follow the project conventions:
- Always add encoding='utf-8' to file operations
- Read config from settings.yaml via get_setting()
- Add sys.path.insert for MCP server files
- Explain every line of code for a beginner audience.

Be concise, practical, and specific to this project."""


def get_api_key():
    """Reads the OpenRouter API key from environment variables."""
    env_var_name = get_setting("llm_providers.fallback.api_key_env_var")
    api_key = os.environ.get(env_var_name)
    if not api_key:
        print(f"ERROR: '{env_var_name}' not found.")
        print("Run: python scripts\\check_balance.py to diagnose.")
        sys.exit(1)
    return api_key


def call_openrouter(api_key, messages, model):
    """
    Sends a chat request to OpenRouter and returns the response.

    Returns (response_text, model_used, finish_reason).
    Returns (None, None, reason_code) on failure.

    Reason codes on failure:
      "timeout"              — model took too long
      "rate_limited"         — too many requests to this model
      "insufficient_credits" — no credits left
      "model_unavailable"    — 404, model doesn't exist or is down
      "http_error"           — other HTTP error
      "error"                — unexpected exception
    """
    url = f"{BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": SITE_URL,
        "X-Title": SITE_NAME,
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]
        text = choice["message"]["content"]
        model_used = data.get("model", model)
        finish_reason = choice.get("finish_reason", "unknown")
        return text, model_used, finish_reason

    except requests.exceptions.Timeout:
        return None, None, "timeout"
    except requests.exceptions.HTTPError:
        code = response.status_code
        if code == 429:
            return None, None, "rate_limited"
        elif code == 402:
            return None, None, "insufficient_credits"
        elif code == 404:
            return None, None, "model_unavailable"
        else:
            return None, None, "http_error"
    except Exception:
        return None, None, "error"


def call_with_fallback_chain(api_key, messages, current_model):
    """
    Tries to get a response, working through the fallback chain on failure.

    How it works:
    1. Try current_model first
    2. If it fails with a retryable error (rate limit, timeout, unavailable):
       - Walk through FREE_MODEL_CHAIN trying each model in order
       - Skip models we already tried
    3. If all free models fail → try PAID_MODEL as last resort
    4. Return the first successful response

    Returns (response_text, model_that_worked, was_model_switched).
    was_model_switched = True means the active model should be updated.
    """
    # Retryable failure reasons — these mean "try another model"
    # Non-retryable: "insufficient_credits", "error" — no point trying more
    retryable = {"timeout", "rate_limited", "model_unavailable", "http_error"}

    # ── Try the current model first ───────────────────────────────────────
    label = current_model.split("/")[-1]
    print(f"  [{label}] Thinking...", end="", flush=True)
    text, model_used, reason = call_openrouter(api_key, messages, current_model)
    print("\r" + " " * 60 + "\r", end="", flush=True)

    if text is not None:
        # Current model worked — return immediately, no switch needed
        return text, model_used, False

    if reason not in retryable:
        # Non-retryable failure — don't try others
        return None, None, False

    # ── Current model failed — walk the chain ────────────────────────────
    # Build the full list of models to try:
    # All free models in chain + paid model at the end
    all_models = FREE_MODEL_CHAIN + [PAID_MODEL]

    for model in all_models:
        # Skip the model we already tried
        if model == current_model:
            continue

        label = model.split("/")[-1]
        tier = "free" if ":free" in model else "paid"
        print(f"  Trying {tier} model: {label}...", end="", flush=True)

        text, model_used, reason = call_openrouter(api_key, messages, model)
        print("\r" + " " * 60 + "\r", end="", flush=True)

        if text is not None:
            # This model worked
            print(f"  (Switched to: {label})")
            return text, model_used, True

        if reason not in retryable:
            # Hit a hard stop (e.g. no credits) — don't try more
            print(f"  Hard stop: {reason}")
            break

        # This model also failed — loop continues to next model

    # All models failed
    return None, None, False


def check_balance_quick(api_key):
    """Quick balance check called when user types 'balance'."""
    url = f"{BASE_URL}/auth/key"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        info = r.json().get("data", {})
        usage = float(info.get("usage", 0))
        limit = info.get("limit")
        if limit:
            balance = float(limit) - usage
            print(f"  Balance: ${balance:.4f} remaining of ${float(limit):.4f}")
            if balance < THRESHOLD:
                print(f"  WARNING: Below ${THRESHOLD:.2f} threshold!")
        else:
            print(f"  Account: Pay-as-you-go | Spent so far: ${usage:.4f}")
    except Exception as e:
        print(f"  Could not retrieve balance: {e}")


def print_help():
    """Prints available commands."""
    print("""
  Commands:
    quit    — exit the chat
    balance — check OpenRouter credit balance
    model   — show active model
    models  — show full fallback chain
    free    — restart from first free model
    paid    — switch to paid model
    clear   — clear conversation history
    help    — show this help
    """)


def print_banner(current_model):
    """Prints the startup banner."""
    print()
    print("=" * 60)
    print("  Supply Chain Control Tower — Fallback Chat")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Model: {current_model}")
    print(f"  Chain: {len(FREE_MODEL_CHAIN)} free models + 1 paid fallback")
    print("=" * 60)
    print("  Type 'help' for commands. Type 'quit' to exit.")
    print("  No live MCP data — use Claude Desktop for agent queries.")
    print("=" * 60)
    print()


def main():
    """Main chat loop with automatic model fallback chain."""
    api_key = get_api_key()

    # Start with the first model in the free chain
    current_model = FREE_MODEL_CHAIN[0]

    print_banner(current_model)

    # Full conversation history for this session
    conversation_history = []

    while True:
        # ── Get user input ────────────────────────────────────────────────
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nExiting. Goodbye!")
            break

        if not user_input:
            continue

        # ── Handle commands ───────────────────────────────────────────────
        cmd = user_input.lower()

        if cmd == "quit":
            print("Goodbye!")
            break

        elif cmd == "balance":
            check_balance_quick(api_key)
            continue

        elif cmd == "model":
            print(f"  Active model: {current_model}")
            continue

        elif cmd == "models":
            print("  Free model chain (tried in order):")
            for i, m in enumerate(FREE_MODEL_CHAIN, 1):
                marker = " ← active" if m == current_model else ""
                print(f"    {i}. {m}{marker}")
            print(f"  Paid fallback: {PAID_MODEL}")
            continue

        elif cmd == "free":
            current_model = FREE_MODEL_CHAIN[0]
            print(f"  Reset to first free model: {current_model}")
            continue

        elif cmd == "paid":
            current_model = PAID_MODEL
            print(f"  Switched to paid model: {current_model}")
            continue

        elif cmd == "clear":
            conversation_history = []
            print("  Conversation history cleared.")
            continue

        elif cmd == "help":
            print_help()
            continue

        # ── Build messages for this API call ──────────────────────────────
        messages = (
            [{"role": "system", "content": SYSTEM_PROMPT}]
            + conversation_history
            + [{"role": "user", "content": user_input}]
        )

        # ── Call LLM with automatic fallback chain ────────────────────────
        text, model_used, was_switched = call_with_fallback_chain(
            api_key, messages, current_model
        )

        # ── Handle complete failure ───────────────────────────────────────
        if text is None:
            print("  All models failed. Options:")
            print("  - Wait a few minutes and try again (rate limits reset)")
            print("  - Type 'paid' to force the paid model")
            print("  - Add credits at https://openrouter.ai/credits")
            continue

        # ── Update active model if we switched ────────────────────────────
        if was_switched and model_used:
            current_model = model_used

        # ── Display response ──────────────────────────────────────────────
        model_label = (model_used or current_model).split("/")[-1]
        print(f"Assistant [{model_label}]:")
        print(text)
        print()

        # ── Save to history ───────────────────────────────────────────────
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": text})

        # Keep last 20 conversation pairs (40 entries) to manage context size
        if len(conversation_history) > 40:
            conversation_history = conversation_history[2:]


if __name__ == "__main__":
    main()