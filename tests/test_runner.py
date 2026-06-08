# tests/test_runner.py
#
# Test Runner for the Supply Chain Control Tower.
#
# WHAT THIS FILE DOES:
#   Reads every scenario from test_scenarios.py, executes it against the
#   real live code, records pass/fail, and writes a full report to
#   logs/test_results.json.
#
# HOW TO RUN FROM TERMINAL:
#   cd "C:\Users\preet\Documents\AI Work\supply_chain_mcp_project"
#   $env:PYTHONPATH = "C:\Users\preet\Documents\AI Work\supply_chain_mcp_project\src"
#   python tests\test_runner.py
#
# HOW IT WORKS:
#   Each scenario has a "function" field like "supply_chain.rules.assign_delay_status".
#   The runner splits this string, imports the module dynamically using importlib,
#   gets the function with getattr, calls it with the scenario's "inputs" dict,
#   then compares the result to the expected value.
#
#   "Dynamic import" means we don't hardcode 'import supply_chain.rules' at the
#   top of this file. Instead we build the import at runtime from the scenario
#   data. This makes the runner reusable for any scenario in any module.
#
# SPECIAL expect_key PATTERNS:
#   "return"              — function returns a plain value; compare directly
#   "return_nonempty"     — verify return is a non-empty string
#   "key_exists:X"        — verify key X exists in the returned dict
#   "healthy_count_gte:N" — verify result["healthy_count"] >= N
#   "dict_key:X"          — verify result[X] equals expect_value
#
# Owner: Vishal
# Version: 3.0

import sys
import os
import json
import importlib
import traceback
from datetime import datetime, date

# ── Path fix ─────────────────────────────────────────────────────────────────
# This file lives at tests/test_runner.py.
# We need to add both:
#   - src/  so supply_chain.* modules are importable
#   - project root  so tests.test_scenarios is importable
_HERE    = os.path.dirname(os.path.abspath(__file__))   # tests/
_ROOT    = os.path.dirname(_HERE)                        # project root
_SRC     = os.path.join(_ROOT, "src")                   # src/
_LOGS    = os.path.join(_ROOT, "logs")                  # logs/

sys.path.insert(0, _SRC)    # makes supply_chain.* importable
sys.path.insert(0, _ROOT)   # makes tests.test_scenarios importable

# ── Import all scenarios ──────────────────────────────────────────────────────
from tests.test_scenarios import ALL_SCENARIOS, SCENARIO_COUNT

# ── Report output path ────────────────────────────────────────────────────────
REPORT_FILE = os.path.join(_LOGS, "test_results.json")


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: resolve and call a function from a dotted path string
# ─────────────────────────────────────────────────────────────────────────────

def _call_function(function_path: str, inputs: dict):
    """
    Dynamically imports a module and calls a function by dotted path string.

    Example:
      function_path = "supply_chain.rules.assign_delay_status"
      → module_path  = "supply_chain.rules"
      → function_name = "assign_delay_status"
      → importlib.import_module("supply_chain.rules")
      → getattr(module, "assign_delay_status")(**inputs)

    Why importlib instead of hardcoded imports?
      Because the runner works for ANY function in ANY module — we don't
      need to update this file when new scenarios are added.

    Returns the raw return value of the function call.
    Raises any exception the function raises (caught by the caller).
    """
    # Split "supply_chain.rules.assign_delay_status"
    # into "supply_chain.rules" and "assign_delay_status"
    parts         = function_path.rsplit(".", 1)
    module_path   = parts[0]    # everything before the last dot
    function_name = parts[1]    # everything after the last dot

    # Import the module (same as writing "import supply_chain.rules")
    module = importlib.import_module(module_path)

    # Get the function from the module (same as "supply_chain.rules.assign_delay_status")
    func = getattr(module, function_name)

    # Call with the inputs dict unpacked as keyword arguments
    return func(**inputs)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: evaluate the result against the expectation
# ─────────────────────────────────────────────────────────────────────────────

def _evaluate(result, expect_key: str, expect_value) -> tuple:
    """
    Compares the function's return value against the expected value.

    Returns:
      (passed: bool, detail: str)

    Handles four expect_key patterns:
      "return"              — direct equality check on the return value
      "return_nonempty"     — check return is a non-empty string
      "key_exists:X"        — check key X is present in result dict
      "healthy_count_gte:N" — check result["healthy_count"] >= N
      "dict_key:X"          — check result[X] == expect_value
      anything else         — treat as a dict key lookup
    """

    # Pattern 1: direct equality — function returns a plain string/int/bool
    if expect_key == "return":
        passed = (result == expect_value)
        detail = (
            f"Expected {repr(expect_value)}, got {repr(result)}"
            if not passed else
            f"Returned {repr(result)} ✓"
        )
        return passed, detail

    # Pattern 2: non-empty string check
    if expect_key == "return_nonempty":
        passed = isinstance(result, str) and len(result.strip()) > 0
        detail = (
            f"Expected non-empty string, got {repr(result)}"
            if not passed else
            f"Returned non-empty string ({len(result)} chars) ✓"
        )
        return passed, detail

    # Pattern 3: key_exists:X — check a key is present in the result dict
    if expect_key.startswith("key_exists:"):
        key_to_check = expect_key.split(":", 1)[1]
        passed = isinstance(result, dict) and key_to_check in result
        detail = (
            f"Expected key '{key_to_check}' in result dict, not found"
            if not passed else
            f"Key '{key_to_check}' exists in result ✓"
        )
        return passed, detail

    # Pattern 4: healthy_count_gte:N — check a numeric value meets a minimum
    if expect_key.startswith("healthy_count_gte:"):
        threshold = int(expect_key.split(":", 1)[1])
        actual    = result.get("healthy_count", 0) if isinstance(result, dict) else 0
        passed    = actual >= threshold
        detail = (
            f"Expected healthy_count >= {threshold}, got {actual}"
            if not passed else
            f"healthy_count = {actual} >= {threshold} ✓"
        )
        return passed, detail

    # Pattern 5: dict_key:X — look up a specific key in result dict
    if expect_key.startswith("dict_key:"):
        key_to_check = expect_key.split(":", 1)[1]
        if not isinstance(result, dict):
            return False, f"Expected dict result, got {type(result).__name__}"
        actual = result.get(key_to_check)
        passed = (actual == expect_value)
        detail = (
            f"result['{key_to_check}']: expected {repr(expect_value)}, got {repr(actual)}"
            if not passed else
            f"result['{key_to_check}'] = {repr(actual)} ✓"
        )
        return passed, detail

    # Fallback: treat expect_key as a direct dict key
    if isinstance(result, dict):
        actual = result.get(expect_key)
        passed = (actual == expect_value)
        detail = (
            f"result['{expect_key}']: expected {repr(expect_value)}, got {repr(actual)}"
            if not passed else
            f"result['{expect_key}'] = {repr(actual)} ✓"
        )
        return passed, detail

    return False, f"Cannot evaluate: result is {type(result).__name__}, expect_key is '{expect_key}'"


# ─────────────────────────────────────────────────────────────────────────────
# CORE: run a single scenario
# ─────────────────────────────────────────────────────────────────────────────

def run_scenario(scenario: dict) -> dict:
    """
    Runs one test scenario and returns a result dict.

    Returns:
    {
        "id":          scenario ID
        "agent":       agent name
        "description": test description
        "status":      "PASS" | "FAIL" | "ERROR"
        "detail":      what matched or what went wrong
        "duration_ms": how long the function call took
    }

    "ERROR" means the function raised an exception (not a wrong value).
    "FAIL"  means the function ran but returned the wrong value.
    "PASS"  means the function returned exactly what we expected.
    """
    import time

    scenario_id  = scenario["id"]
    agent        = scenario["agent"]
    description  = scenario["description"]
    function_path = scenario["function"]
    inputs        = scenario["inputs"].copy()   # copy so we don't mutate the original
    expect_key    = scenario["expect_key"]
    expect_value  = scenario["expect_value"]

    # Replace any "today" value that is already a date object
    # (test_scenarios.py sets today=TODAY at module load time,
    #  so it's already a date — no substitution needed)

    start_ms = time.time() * 1000

    try:
        result = _call_function(function_path, inputs)
        duration_ms = round(time.time() * 1000 - start_ms, 2)

        passed, detail = _evaluate(result, expect_key, expect_value)

        return {
            "id":          scenario_id,
            "agent":       agent,
            "description": description,
            "function":    function_path,
            "status":      "PASS" if passed else "FAIL",
            "detail":      detail,
            "duration_ms": duration_ms,
        }

    except Exception as e:
        duration_ms = round(time.time() * 1000 - start_ms, 2)
        # Get the full traceback so the error is diagnosable
        tb = traceback.format_exc()
        return {
            "id":          scenario_id,
            "agent":       agent,
            "description": description,
            "function":    function_path,
            "status":      "ERROR",
            "detail":      f"{type(e).__name__}: {str(e)}",
            "traceback":   tb,
            "duration_ms": duration_ms,
        }


# ─────────────────────────────────────────────────────────────────────────────
# CORE: run a list of scenarios and return summary + results
# ─────────────────────────────────────────────────────────────────────────────

def run_scenarios(scenarios: list, label: str = "all") -> dict:
    """
    Runs a list of scenarios. Returns a full report dict.

    Parameters:
      scenarios — list of scenario dicts (from test_scenarios.py)
      label     — name shown in the report (e.g. "all", "shipping-delay-agent")

    Returns:
    {
        "run_label":     label
        "run_at":        ISO timestamp
        "total":         total scenarios run
        "passed":        count of PASS results
        "failed":        count of FAIL results
        "errors":        count of ERROR results
        "pass_rate_pct": percentage that passed (PASS / total * 100)
        "results":       list of per-scenario result dicts
        "failed_ids":    list of IDs that did not pass (for quick triage)
    }
    """
    results     = []
    passed      = 0
    failed      = 0
    errors      = 0
    failed_ids  = []

    for scenario in scenarios:
        result = run_scenario(scenario)
        results.append(result)

        if result["status"] == "PASS":
            passed += 1
        elif result["status"] == "FAIL":
            failed += 1
            failed_ids.append(result["id"])
        else:  # ERROR
            errors += 1
            failed_ids.append(result["id"])

    total        = len(scenarios)
    pass_rate    = round((passed / total * 100), 1) if total > 0 else 0.0

    return {
        "run_label":     label,
        "run_at":        datetime.now().isoformat(),
        "total":         total,
        "passed":        passed,
        "failed":        failed,
        "errors":        errors,
        "pass_rate_pct": pass_rate,
        "failed_ids":    failed_ids,
        "results":       results,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC: run all tests
# ─────────────────────────────────────────────────────────────────────────────

def run_all_tests() -> dict:
    """
    Runs every scenario in ALL_SCENARIOS.
    Saves the report to logs/test_results.json.
    Returns the report dict.
    """
    report = run_scenarios(ALL_SCENARIOS, label="all")
    _save_report(report)
    return report


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC: run tests for one specific agent
# ─────────────────────────────────────────────────────────────────────────────

def run_agent_tests(agent_name: str) -> dict:
    """
    Runs only the scenarios for a specific agent.

    Example: run_agent_tests("shipping-delay-agent")
    Returns a report containing only those scenarios.
    """
    # Filter scenarios to only those matching the agent name
    filtered = [s for s in ALL_SCENARIOS if s["agent"] == agent_name]

    if not filtered:
        return {
            "error": f"No scenarios found for agent '{agent_name}'.",
            "available_agents": sorted(set(s["agent"] for s in ALL_SCENARIOS)),
        }

    report = run_scenarios(filtered, label=agent_name)
    _save_report(report)
    return report


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC: get last saved report without re-running
# ─────────────────────────────────────────────────────────────────────────────

def get_last_test_report() -> dict:
    """
    Reads and returns the most recently saved test report from disk.
    Does NOT re-run any tests.

    Returns an error dict if no report exists yet.
    """
    if not os.path.exists(REPORT_FILE):
        return {
            "error": "No test report found. Run run_all_tests() first.",
            "report_path": REPORT_FILE,
        }

    try:
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {
            "error": f"Could not read report file: {str(e)}",
            "report_path": REPORT_FILE,
        }


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC: get only failed tests from last report
# ─────────────────────────────────────────────────────────────────────────────

def get_failed_tests() -> dict:
    """
    Reads the last saved report and returns only the FAIL and ERROR results.
    Useful for fast triage — no need to scroll through 47 passing tests.

    Returns a summary with:
    - run_at, pass_rate_pct, total from the original run
    - failures: list of failed/errored result dicts only
    - failure_count
    """
    report = get_last_test_report()

    if "error" in report:
        return report

    failures = [
        r for r in report.get("results", [])
        if r["status"] in ("FAIL", "ERROR")
    ]

    return {
        "run_at":        report.get("run_at"),
        "pass_rate_pct": report.get("pass_rate_pct"),
        "total_run":     report.get("total"),
        "failure_count": len(failures),
        "failures":      failures,
        "summary": (
            f"{len(failures)} test(s) failed or errored in the last run."
            if failures
            else "All tests passed in the last run."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC: reset saved report
# ─────────────────────────────────────────────────────────────────────────────

def reset_test_results() -> dict:
    """
    Deletes the saved test report so the next run starts fresh.
    Does NOT re-run any tests.
    """
    if not os.path.exists(REPORT_FILE):
        return {"message": "No report file exists. Nothing to reset."}

    try:
        os.remove(REPORT_FILE)
        return {
            "message": "Test report cleared successfully.",
            "deleted": REPORT_FILE,
        }
    except Exception as e:
        return {"error": f"Could not delete report: {str(e)}"}


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL: save report to disk
# ─────────────────────────────────────────────────────────────────────────────

def _save_report(report: dict) -> None:
    """
    Saves the report dict to logs/test_results.json.
    Creates the logs/ directory if it doesn't exist.
    Overwrites any previous report (only the latest run is kept).
    """
    os.makedirs(_LOGS, exist_ok=True)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL: print a readable summary to the terminal
# ─────────────────────────────────────────────────────────────────────────────

def _print_summary(report: dict) -> None:
    """
    Prints a clean, readable summary to the terminal.
    Called when the script is run directly (not via MCP).
    """
    print("\n" + "=" * 60)
    print(f"  SUPPLY CHAIN CONTROL TOWER — TEST REPORT")
    print(f"  Run label : {report['run_label']}")
    print(f"  Run at    : {report['run_at']}")
    print("=" * 60)
    print(f"  Total     : {report['total']}")
    print(f"  Passed    : {report['passed']}")
    print(f"  Failed    : {report['failed']}")
    print(f"  Errors    : {report['errors']}")
    print(f"  Pass rate : {report['pass_rate_pct']}%")
    print("=" * 60)

    # Print failures and errors so they're immediately visible
    problems = [r for r in report["results"] if r["status"] != "PASS"]
    if problems:
        print(f"\n  FAILURES / ERRORS ({len(problems)}):")
        for r in problems:
            print(f"\n  [{r['status']}] {r['id']} — {r['description']}")
            print(f"         {r['detail']}")
            if "traceback" in r:
                # Print just the last line of the traceback for brevity
                tb_lines = r["traceback"].strip().splitlines()
                print(f"         {tb_lines[-1]}")
    else:
        print("\n  All tests passed!")

    print(f"\n  Report saved to: {REPORT_FILE}")
    print("=" * 60 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT — run directly from terminal
# ─────────────────────────────────────────────────────────────────────────────
# When you run "python tests/test_runner.py" from the terminal,
# this block executes. It runs all tests and prints the summary.
#
# When imported by test_mcp_server.py, this block is skipped —
# the MCP server calls run_all_tests() directly instead.

if __name__ == "__main__":
    print(f"Running {SCENARIO_COUNT} test scenarios...")
    report = run_all_tests()
    _print_summary(report)
