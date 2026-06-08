# mcp_server/test_mcp_server.py
#
# Test Agent — the 12th and final MCP server in the Supply Chain Control Tower.
#
# This server exposes the test runner as 5 MCP tools that Claude Desktop
# can call by name. All execution logic lives in tests/test_runner.py.
# This file is a thin wrapper — same pattern as every other MCP server.
#
# Tools in this server (5 total):
#   run_all_tests        — runs all 53 scenarios, returns full report
#   run_agent_tests      — runs tests for one specific agent only
#   get_last_test_report — returns last saved report without re-running
#   get_failed_tests     — returns only FAIL/ERROR results for fast triage
#   reset_test_results   — clears the saved report so next run starts fresh
#
# To run manually (for testing):
#   cd "C:\Users\preet\Documents\AI Work\supply_chain_mcp_project"
#   python mcp_server\test_mcp_server.py
#
# Owner: Vishal
# Version: 3.0

import sys
import os

# ── Path fix — must be FIRST, before any local imports ───────────────────────
# This file lives at mcp_server/test_mcp_server.py.
# We need to add BOTH src/ (for supply_chain.*) and the project root
# (for tests.test_runner) to sys.path.
_HERE = os.path.dirname(os.path.abspath(__file__))   # mcp_server/
_ROOT = os.path.dirname(_HERE)                        # project root
_SRC  = os.path.join(_ROOT, "src")                   # src/

sys.path.insert(0, _SRC)    # supply_chain.* modules
sys.path.insert(0, _ROOT)   # tests.test_runner module

from mcp.server.fastmcp import FastMCP

# Import all five public functions from the runner.
# We rename them with _ prefix so the MCP tool functions can use clean names.
from tests.test_runner import (
    run_all_tests         as _run_all_tests,
    run_agent_tests       as _run_agent_tests,
    get_last_test_report  as _get_last_test_report,
    get_failed_tests      as _get_failed_tests,
    reset_test_results    as _reset_test_results,
)

mcp = FastMCP("test-agent")


# ─── TOOL 1 ──────────────────────────────────────────────────────────────────

@mcp.tool()
def run_all_tests() -> dict:
    """
    Runs all 53 test scenarios across all 6 agents and returns a full report.

    This is the primary health check for the entire rules engine.
    Run this any time you modify a rules file to confirm nothing broke.

    Tests covered:
    - shipping-delay-agent: 12 scenarios (delay status, reason codes, delay days)
    - inventory-agent:       8 scenarios (inventory status, fulfillment, shortage)
    - freight-agent:         8 scenarios (freight status, carrier tier, pickup delay)
    - warehouse-agent:       6 scenarios (pick health, pick delay days)
    - recommendation-agent:  8 scenarios (priority score, escalation, team assignment)
    - coordinator-agent:     5 scenarios (agent roster, system status)
    - edge cases:            6 scenarios (empty inputs, unknowns, boundary values)

    Returns:
    - run_at:        ISO timestamp of when the run completed
    - total:         total scenarios executed
    - passed:        count of PASS results
    - failed:        count of FAIL results
    - errors:        count of ERROR results (function crashed, not wrong value)
    - pass_rate_pct: percentage that passed
    - failed_ids:    list of scenario IDs that did not pass (empty if all pass)
    - results:       full per-scenario breakdown with status and detail message

    Report is saved to logs/test_results.json after every run.

    Use this when:
    - "Run all tests"
    - "Check if everything is working"
    - "Run the test suite"
    - "/test" slash command
    - "Did I break anything?"
    - "Validate the rules engine"
    - "Run regression tests"
    """
    try:
        return _run_all_tests()
    except Exception as e:
        return {
            "error": f"run_all_tests failed: {str(e)}",
            "hint": "Check that PYTHONPATH is set and all supply_chain modules are importable.",
        }


# ─── TOOL 2 ──────────────────────────────────────────────────────────────────

@mcp.tool()
def run_agent_tests(agent_name: str) -> dict:
    """
    Runs test scenarios for one specific agent only.

    Use this when you have changed rules for a specific domain and only
    want to validate that agent — faster than running all 53 tests.

    Valid agent names:
    - "shipping-delay-agent"   (12 scenarios)
    - "inventory-agent"        (8 scenarios)
    - "freight-agent"          (8 scenarios)
    - "warehouse-agent"        (6 scenarios)
    - "recommendation-agent"   (8 scenarios)
    - "coordinator-agent"      (5 scenarios)

    Returns the same report structure as run_all_tests but filtered to
    only the scenarios belonging to the named agent.

    Also saves the filtered report to logs/test_results.json, overwriting
    the previous report.

    Use this when:
    - "Test only the freight agent"
    - "Run inventory tests"
    - "Check shipping delay rules"
    - "Validate warehouse scenarios"
    - "Did I break the recommendation engine?"
    """
    try:
        return _run_agent_tests(agent_name=agent_name)
    except Exception as e:
        return {
            "error": f"run_agent_tests failed: {str(e)}",
            "agent_name": agent_name,
        }


# ─── TOOL 3 ──────────────────────────────────────────────────────────────────

@mcp.tool()
def get_last_test_report() -> dict:
    """
    Returns the most recently saved test report without re-running any tests.

    Use this when you want to review results from a previous run without
    the overhead of executing all 53 scenarios again.

    Returns the full report dict from logs/test_results.json including:
    - When the tests were run (run_at)
    - Pass/fail counts and pass rate
    - Full per-scenario breakdown
    - List of any failed scenario IDs

    Returns an error dict if no report exists yet (run run_all_tests first).

    Use this when:
    - "Show me the last test results"
    - "What did the tests show?"
    - "Display the test report"
    - "When were tests last run?"
    - "What is the current test status?"
    """
    try:
        return _get_last_test_report()
    except Exception as e:
        return {
            "error": f"get_last_test_report failed: {str(e)}",
        }


# ─── TOOL 4 ──────────────────────────────────────────────────────────────────

@mcp.tool()
def get_failed_tests() -> dict:
    """
    Returns only the FAIL and ERROR results from the last test run.

    This is the fastest triage tool — no need to scroll through 53 passing
    tests to find the one that broke. If all tests passed, returns a
    summary saying so.

    Returns:
    - run_at:        when the last run happened
    - pass_rate_pct: overall pass rate from that run
    - total_run:     total scenarios in that run
    - failure_count: how many failed or errored
    - failures:      list of failed/errored result dicts with full detail
    - summary:       one-sentence plain-English summary

    Each failure includes:
    - id and description of the scenario
    - status (FAIL or ERROR)
    - detail message explaining what was expected vs what was received
    - traceback (for ERROR status only)

    Use this when:
    - "What tests are failing?"
    - "Show me the failures"
    - "Which tests broke?"
    - "What went wrong in the last test run?"
    - "Fast test triage"
    """
    try:
        return _get_failed_tests()
    except Exception as e:
        return {
            "error": f"get_failed_tests failed: {str(e)}",
        }


# ─── TOOL 5 ──────────────────────────────────────────────────────────────────

@mcp.tool()
def reset_test_results() -> dict:
    """
    Clears the saved test report so the next run starts completely fresh.

    Use this when you want to discard old results — for example, after
    fixing a failing test and before running the suite again.

    Does NOT re-run any tests. Only deletes logs/test_results.json.

    Returns a confirmation message, or an error if the file could not
    be deleted.

    Use this when:
    - "Reset the test results"
    - "Clear the test report"
    - "Start fresh test run"
    - "Delete old test results"
    """
    try:
        return _reset_test_results()
    except Exception as e:
        return {
            "error": f"reset_test_results failed: {str(e)}",
        }


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
