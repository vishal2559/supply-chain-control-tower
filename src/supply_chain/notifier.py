# src/supply_chain/notifier.py
# Supply Chain Control Tower — Anomaly Notifier
# =============================================================================
#
# PURPOSE:
#   Sends anomaly alerts through configured notification channels.
#   Currently supports:
#     - "log"     : always writes to logs/anomaly.log (recommended: always on)
#     - "desktop" : Windows toast notification (pops up on screen)
#     - "email"   : sends email via SMTP (disabled by default)
#
# HOW TO USE:
#   from supply_chain.notifier import notify
#   from supply_chain.anomaly_detector import check_supply_chain_anomalies
#
#   anomalies = check_supply_chain_anomalies(
#       total_orders=100, critical_orders=25, ...
#   )
#   for anomaly in anomalies:
#       notify(anomaly)
#
# SETTINGS THAT CONTROL THIS MODULE (all in config/settings.yaml):
#   notifications.enabled          → master switch
#   notifications.channels         → list: ["log", "desktop", "email"]
#   notifications.email_enabled    → true/false
#   notifications.anomaly_log_path → where to write anomaly log
#   notifications.email_*_env_var  → Windows env var names for SMTP config
#
# SECURITY:
#   Email credentials (SMTP host, password) are never stored in any file.
#   They live in Windows environment variables only.
#   This file only reads the NAME of those variables from settings.yaml.
#
# =============================================================================

import os
import sys
import json
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
))))

from config.settings_loader import get_setting, get_log_path, is_notifications_enabled

_LOCK = threading.Lock()


# ─── Main notify function ─────────────────────────────────────────────────────

def notify(anomaly: dict):
    """
    Sends an anomaly alert through all configured channels.

    Parameters:
        anomaly : dict — anomaly event dict from anomaly_detector.py
                         must have: anomaly_type, severity, description,
                                    actual_value, threshold_value,
                                    recommended_action, timestamp

    This function never raises an exception — notification failure
    must never crash the tool that called it.
    """
    if not is_notifications_enabled():
        return

    channels = get_setting("notifications.channels", default=["log"])

    for channel in channels:
        try:
            if channel == "log":
                _notify_log(anomaly)
            elif channel == "desktop":
                _notify_desktop(anomaly)
            elif channel == "email":
                if get_setting("notifications.email_enabled", default=False):
                    _notify_email(anomaly)
        except Exception as e:
            # Never let notification failure crash the caller
            print(f"[notifier] WARNING: channel '{channel}' failed: {e}")


def notify_all(anomalies: list):
    """
    Convenience function — notifies for a list of anomalies.
    Call this with the full list returned by check_supply_chain_anomalies().

    Parameters:
        anomalies : list — list of anomaly dicts from anomaly_detector.py
    """
    for anomaly in anomalies:
        notify(anomaly)


# ─── Channel: Log file ────────────────────────────────────────────────────────

def _notify_log(anomaly: dict):
    """
    Writes the anomaly to logs/anomaly.log in JSON Lines format.

    This channel is always the safest — no network, no external dependencies,
    just a file write. Always include "log" in your channels list.
    """
    try:
        log_path = get_log_path("notifications.anomaly_log_path")
        with _LOCK:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(anomaly) + "\n")

        # Also print a clear summary to the terminal
        severity = anomaly.get("severity", "WARNING")
        atype    = anomaly.get("anomaly_type", "UNKNOWN")
        desc     = anomaly.get("description", "")
        action   = anomaly.get("recommended_action", "")
        ts       = anomaly.get("timestamp", "")

        print(f"\n{'='*60}")
        print(f"[ANOMALY] {ts} | {severity} | {atype}")
        print(f"  {desc}")
        print(f"  Action: {action}")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"[notifier] Log write failed: {e}")


# ─── Channel: Windows desktop toast ──────────────────────────────────────────

def _notify_desktop(anomaly: dict):
    """
    Shows a Windows toast notification (pop-up in the bottom right corner).

    Uses the 'winotify' library if available.
    If winotify is not installed, falls back to a print statement with
    clear instructions on how to install it.

    To install winotify:
        pip install winotify

    Why winotify and not win10toast?
    winotify is more reliable on Windows 10/11 and doesn't require admin rights.
    """
    severity = anomaly.get("severity", "WARNING")
    atype    = anomaly.get("anomaly_type", "ANOMALY")
    desc     = anomaly.get("description", "")[:200]   # Toast has character limit
    action   = anomaly.get("recommended_action", "")[:100]

    # Title varies by severity
    if severity == "CRITICAL":
        title = f"🚨 CRITICAL: {atype}"
    else:
        title = f"⚠️  WARNING: {atype}"

    message = f"{desc}\n\nAction: {action}"

    try:
        # Try winotify first (preferred)
        from winotify import Notification, audio

        toast = Notification(
            app_id  = "Supply Chain Control Tower",
            title   = title,
            msg     = message,
            duration= "long",    # stays on screen longer than default
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()

    except ImportError:
        # winotify not installed — print a clear desktop-style message instead
        print(f"\n{'#'*60}")
        print(f"# DESKTOP NOTIFICATION (winotify not installed)")
        print(f"# {title}")
        print(f"# {desc[:100]}")
        print(f"# To enable real Windows toasts: pip install winotify")
        print(f"{'#'*60}\n")

    except Exception as e:
        # Any other toast failure — don't crash
        print(f"[notifier] Desktop notification failed: {e}")
        print(f"  Anomaly: {atype} | {desc[:80]}")


# ─── Channel: Email ───────────────────────────────────────────────────────────

def _notify_email(anomaly: dict):
    """
    Sends an email notification via SMTP.

    All credentials are read from Windows environment variables — never from files.
    Enable this channel by:
        1. Set notifications.email_enabled: true in settings.yaml
        2. Add "email" to notifications.channels list
        3. Set these Windows environment variables:
               NOTIFY_EMAIL_TO   = recipient@example.com
               NOTIFY_EMAIL_FROM = sender@example.com
               NOTIFY_SMTP_HOST  = smtp.gmail.com
               NOTIFY_SMTP_PORT  = 587
               NOTIFY_SMTP_PASS  = your-app-password

    For Gmail: use an App Password, not your regular password.
    Generate at: https://myaccount.google.com/apppasswords
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # Read all credentials from environment variables
    to_env   = get_setting("notifications.email_to_env_var",   default="NOTIFY_EMAIL_TO")
    frm_env  = get_setting("notifications.email_from_env_var", default="NOTIFY_EMAIL_FROM")
    host_env = get_setting("notifications.smtp_host_env_var",  default="NOTIFY_SMTP_HOST")
    port_env = get_setting("notifications.smtp_port_env_var",  default="NOTIFY_SMTP_PORT")
    pass_env = get_setting("notifications.smtp_pass_env_var",  default="NOTIFY_SMTP_PASS")

    to_addr   = os.environ.get(to_env)
    from_addr = os.environ.get(frm_env)
    smtp_host = os.environ.get(host_env)
    smtp_port = int(os.environ.get(port_env, "587"))
    smtp_pass = os.environ.get(pass_env)

    # Check all required env vars are set
    missing = []
    if not to_addr:   missing.append(to_env)
    if not from_addr: missing.append(frm_env)
    if not smtp_host: missing.append(host_env)
    if not smtp_pass: missing.append(pass_env)

    if missing:
        print(
            f"[notifier] Email skipped — missing environment variables: "
            f"{', '.join(missing)}\n"
            f"Set these in Windows System Settings → Advanced → Environment Variables"
        )
        return

    # Build the email
    severity = anomaly.get("severity", "WARNING")
    atype    = anomaly.get("anomaly_type", "ANOMALY")
    desc     = anomaly.get("description", "")
    action   = anomaly.get("recommended_action", "")
    ts       = anomaly.get("timestamp", "")

    subject = f"[Supply Chain Control Tower] {severity}: {atype}"
    body = f"""Supply Chain Control Tower — Anomaly Alert

Time:      {ts}
Severity:  {severity}
Type:      {atype}

Description:
{desc}

Recommended Action:
{action}

---
This notification was sent automatically by Supply Chain Control Tower.
To adjust notification thresholds, edit config/settings.yaml
"""

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"]    = from_addr
    msg["To"]      = to_addr
    msg.attach(MIMEText(body, "plain"))

    # Send via SMTP with TLS
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(from_addr, smtp_pass)
        server.send_message(msg)

    print(f"[notifier] Email sent to {to_addr}: {atype}")


# ─── Anomaly log reader ───────────────────────────────────────────────────────

def get_recent_anomalies(n: int = 20) -> list:
    """
    Reads the last N anomalies from the anomaly log file.
    Used by the Performance Agent to surface recent anomaly history to Claude.

    Parameters:
        n : int — number of recent anomalies to return (default 20)

    Returns:
        list of anomaly dicts, most recent last
    """
    try:
        log_path = get_log_path("notifications.anomaly_log_path")
        if not os.path.exists(log_path):
            return []

        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Parse the last N lines (JSON Lines format)
        recent = []
        for line in lines[-n:]:
            line = line.strip()
            if line:
                try:
                    recent.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # skip malformed lines

        return recent

    except Exception as e:
        print(f"[notifier] Could not read anomaly log: {e}")
        return []
