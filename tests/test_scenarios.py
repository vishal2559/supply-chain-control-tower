# tests/test_scenarios.py
#
# Test scenario definitions for the Supply Chain Control Tower.
#
# WHAT THIS FILE IS:
#   A pure-Python data file. It contains no test execution logic.
#   It only defines what the tests ARE — not how they run.
#   test_runner.py reads these definitions and executes them.
#
# WHY SEPARATE FROM test_runner.py:
#   - You can add new test scenarios here without touching the runner.
#   - The runner can be reused for any set of scenarios.
#   - Same principle as rules.py (data) vs mcp_server (execution).
#
# HOW EACH SCENARIO IS STRUCTURED:
#   {
#     "id":          unique test ID string (e.g. "SHIP-001")
#     "agent":       which agent this tests (e.g. "shipping-delay-agent")
#     "description": plain-English description of what is being tested
#     "function":    the Python module path and function name to call
#                    format: "module_name.function_name"
#     "inputs":      dict of keyword arguments to pass to the function
#                    (any "today" value is replaced at runtime with date.today())
#     "expect_key":  which key in the return value to check
#                    (use "return" if the function returns a plain string)
#     "expect_value":the exact value we expect at that key
#   }
#
# FUNCTION SIGNATURES VERIFIED from actual source files:
#   rules.py:               assign_delay_status(row, today) -> str
#                           assign_reason_code(row, today) -> str
#                           calculate_delay_days(row, today) -> int
#   inventory_rules.py:     assign_inventory_status(row) -> str
#                           can_fulfill(qty_available, qty_needed) -> bool
#                           calculate_shortage(qty_available, qty_needed) -> int
#   freight_rules.py:       assign_freight_status(row, today) -> str
#                           assign_carrier_tier(score_str) -> str
#                           calculate_pickup_delay_days(row, today) -> int
#   warehouse_rules.py:     assign_pick_health(row, today) -> str
#                           calculate_pick_delay_days(row, today) -> int
#   recommendation_engine.py: calculate_priority_score(...) -> int
#                              needs_escalation(...) -> bool
#                              get_responsible_team(root_cause) -> str
#                              get_action_sentence(root_cause) -> str
#   coordinator_engine.py:  get_agent_roster() -> dict
#                           get_system_status() -> dict
#
# Owner: Vishal
# Version: 3.0

from datetime import date, timedelta

# Build date references used throughout scenarios.
# Using TODAY so tests never become stale — they always compute relative to now.
TODAY        = date.today()
YESTERDAY    = TODAY - timedelta(days=1)
THREE_AGO    = TODAY - timedelta(days=3)   # 3 days ago → DELAYED
TEN_AGO      = TODAY - timedelta(days=10)  # 10 days ago → NEED_ACTION
TOMORROW     = TODAY + timedelta(days=1)   # future → ON_TIME
FUTURE_5     = TODAY + timedelta(days=5)   # 5 days ahead → ON_TIME


# ─────────────────────────────────────────────────────────────────────────────
# SHIPPING DELAY AGENT TESTS  (SHIP-001 through SHIP-012)
# Tests assign_delay_status, assign_reason_code, calculate_delay_days
# ─────────────────────────────────────────────────────────────────────────────

SHIPPING_SCENARIOS = [

    {
        "id": "SHIP-001",
        "agent": "shipping-delay-agent",
        "description": "Order with future pick date → ON_TIME",
        "function": "supply_chain.rules.assign_delay_status",
        "inputs": {
            "row": {
                "scheduled_pick_date": str(TOMORROW),
                "order_status": "OPEN",
                "ship_confirm_date": "",
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "ON_TIME",
    },

    {
        "id": "SHIP-002",
        "agent": "shipping-delay-agent",
        "description": "Order 3 days overdue, not shipped → DELAYED",
        "function": "supply_chain.rules.assign_delay_status",
        "inputs": {
            "row": {
                "scheduled_pick_date": str(THREE_AGO),
                "order_status": "OPEN",
                "ship_confirm_date": "",
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "DELAYED",
    },

    {
        "id": "SHIP-003",
        "agent": "shipping-delay-agent",
        "description": "Order 10 days overdue → NEED_ACTION",
        "function": "supply_chain.rules.assign_delay_status",
        "inputs": {
            "row": {
                "scheduled_pick_date": str(TEN_AGO),
                "order_status": "OPEN",
                "ship_confirm_date": "",
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "NEED_ACTION",
    },

    {
        "id": "SHIP-004",
        "agent": "shipping-delay-agent",
        "description": "Order with ship_confirm_date filled → SHIPPED",
        "function": "supply_chain.rules.assign_delay_status",
        "inputs": {
            "row": {
                "scheduled_pick_date": str(TEN_AGO),
                "order_status": "OPEN",
                "ship_confirm_date": str(YESTERDAY),
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "SHIPPED",
    },

    {
        "id": "SHIP-005",
        "agent": "shipping-delay-agent",
        "description": "Cancelled order → CANCELLED",
        "function": "supply_chain.rules.assign_delay_status",
        "inputs": {
            "row": {
                "scheduled_pick_date": str(TEN_AGO),
                "order_status": "CANCELLED",
                "ship_confirm_date": "",
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "CANCELLED",
    },

    {
        "id": "SHIP-006",
        "agent": "shipping-delay-agent",
        "description": "Freight hold flag = YES → FREIGHT_HOLD reason code",
        "function": "supply_chain.rules.assign_reason_code",
        "inputs": {
            "row": {
                "scheduled_pick_date": str(THREE_AGO),
                "order_status": "OPEN",
                "ship_confirm_date": "",
                "freight_hold_flag": "YES",
                "backorder_qty": "0",
                "qty_ordered": "10",
                "qty_allocated": "10",
                "available_inventory": "10",
                "truck_available": "YES",
                "carrier_status": "ON_TIME",
                "pick_status": "READY",
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "FREIGHT_HOLD",
    },

    {
        "id": "SHIP-007",
        "agent": "shipping-delay-agent",
        "description": "Backorder qty > 0 → BACKORDER reason code",
        "function": "supply_chain.rules.assign_reason_code",
        "inputs": {
            "row": {
                "scheduled_pick_date": str(THREE_AGO),
                "order_status": "OPEN",
                "ship_confirm_date": "",
                "freight_hold_flag": "NO",
                "backorder_qty": "5",
                "qty_ordered": "10",
                "qty_allocated": "5",
                "available_inventory": "0",
                "truck_available": "YES",
                "carrier_status": "ON_TIME",
                "pick_status": "READY",
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "BACKORDER",
    },

    {
        "id": "SHIP-008",
        "agent": "shipping-delay-agent",
        "description": "Truck not available → TRUCK_NOT_AVAILABLE reason code",
        "function": "supply_chain.rules.assign_reason_code",
        "inputs": {
            "row": {
                "scheduled_pick_date": str(THREE_AGO),
                "order_status": "OPEN",
                "ship_confirm_date": "",
                "freight_hold_flag": "NO",
                "backorder_qty": "0",
                "qty_ordered": "10",
                "qty_allocated": "10",
                "available_inventory": "10",
                "truck_available": "NO",
                "carrier_status": "ON_TIME",
                "pick_status": "READY",
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "TRUCK_NOT_AVAILABLE",
    },

    {
        "id": "SHIP-009",
        "agent": "shipping-delay-agent",
        "description": "Carrier status DELAYED → CARRIER_DELAY reason code",
        "function": "supply_chain.rules.assign_reason_code",
        "inputs": {
            "row": {
                "scheduled_pick_date": str(THREE_AGO),
                "order_status": "OPEN",
                "ship_confirm_date": "",
                "freight_hold_flag": "NO",
                "backorder_qty": "0",
                "qty_ordered": "10",
                "qty_allocated": "10",
                "available_inventory": "10",
                "truck_available": "YES",
                "carrier_status": "DELAYED",
                "pick_status": "READY",
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "CARRIER_DELAY",
    },

    {
        "id": "SHIP-010",
        "agent": "shipping-delay-agent",
        "description": "Pick not started → WAREHOUSE_PICK_DELAY reason code",
        "function": "supply_chain.rules.assign_reason_code",
        "inputs": {
            "row": {
                "scheduled_pick_date": str(THREE_AGO),
                "order_status": "OPEN",
                "ship_confirm_date": "",
                "freight_hold_flag": "NO",
                "backorder_qty": "0",
                "qty_ordered": "10",
                "qty_allocated": "10",
                "available_inventory": "10",
                "truck_available": "YES",
                "carrier_status": "ON_TIME",
                "pick_status": "NOT_STARTED",
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "WAREHOUSE_PICK_DELAY",
    },

    {
        "id": "SHIP-011",
        "agent": "shipping-delay-agent",
        "description": "On-time order → reason code NOT_APPLICABLE",
        "function": "supply_chain.rules.assign_reason_code",
        "inputs": {
            "row": {
                "scheduled_pick_date": str(TOMORROW),
                "order_status": "OPEN",
                "ship_confirm_date": "",
                "freight_hold_flag": "NO",
                "backorder_qty": "0",
                "qty_ordered": "10",
                "qty_allocated": "10",
                "available_inventory": "10",
                "truck_available": "YES",
                "carrier_status": "ON_TIME",
                "pick_status": "READY",
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "NOT_APPLICABLE",
    },

    {
        "id": "SHIP-012",
        "agent": "shipping-delay-agent",
        "description": "calculate_delay_days returns correct integer for 10-day delay",
        "function": "supply_chain.rules.calculate_delay_days",
        "inputs": {
            "row": {"scheduled_pick_date": str(TEN_AGO)},
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": 10,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# INVENTORY AGENT TESTS  (INV-001 through INV-008)
# Tests assign_inventory_status, can_fulfill, calculate_shortage
# ─────────────────────────────────────────────────────────────────────────────

INVENTORY_SCENARIOS = [

    {
        "id": "INV-001",
        "agent": "inventory-agent",
        "description": "backorder_flag=Y → ON_BACKORDER",
        "function": "supply_chain.inventory_rules.assign_inventory_status",
        "inputs": {
            "row": {
                "backorder_flag": "Y",
                "qty_available": "0",
                "safety_stock": "10",
                "reorder_point": "20",
            }
        },
        "expect_key": "return",
        "expect_value": "ON_BACKORDER",
    },

    {
        "id": "INV-002",
        "agent": "inventory-agent",
        "description": "qty_available=0, no backorder → OUT_OF_STOCK",
        "function": "supply_chain.inventory_rules.assign_inventory_status",
        "inputs": {
            "row": {
                "backorder_flag": "N",
                "qty_available": "0",
                "safety_stock": "10",
                "reorder_point": "20",
            }
        },
        "expect_key": "return",
        "expect_value": "OUT_OF_STOCK",
    },

    {
        "id": "INV-003",
        "agent": "inventory-agent",
        "description": "qty_available below safety_stock → CRITICAL",
        "function": "supply_chain.inventory_rules.assign_inventory_status",
        "inputs": {
            "row": {
                "backorder_flag": "N",
                "qty_available": "5",
                "safety_stock": "10",
                "reorder_point": "20",
            }
        },
        "expect_key": "return",
        "expect_value": "CRITICAL",
    },

    {
        "id": "INV-004",
        "agent": "inventory-agent",
        "description": "qty_available between safety_stock and reorder_point → LOW",
        "function": "supply_chain.inventory_rules.assign_inventory_status",
        "inputs": {
            "row": {
                "backorder_flag": "N",
                "qty_available": "15",
                "safety_stock": "10",
                "reorder_point": "20",
            }
        },
        "expect_key": "return",
        "expect_value": "LOW",
    },

    {
        "id": "INV-005",
        "agent": "inventory-agent",
        "description": "qty_available at or above reorder_point → HEALTHY",
        "function": "supply_chain.inventory_rules.assign_inventory_status",
        "inputs": {
            "row": {
                "backorder_flag": "N",
                "qty_available": "50",
                "safety_stock": "10",
                "reorder_point": "20",
            }
        },
        "expect_key": "return",
        "expect_value": "HEALTHY",
    },

    {
        "id": "INV-006",
        "agent": "inventory-agent",
        "description": "can_fulfill returns True when stock covers need",
        "function": "supply_chain.inventory_rules.can_fulfill",
        "inputs": {"qty_available": 100, "qty_needed": 50},
        "expect_key": "return",
        "expect_value": True,
    },

    {
        "id": "INV-007",
        "agent": "inventory-agent",
        "description": "can_fulfill returns False when stock is insufficient",
        "function": "supply_chain.inventory_rules.can_fulfill",
        "inputs": {"qty_available": 10, "qty_needed": 50},
        "expect_key": "return",
        "expect_value": False,
    },

    {
        "id": "INV-008",
        "agent": "inventory-agent",
        "description": "calculate_shortage returns correct shortage units",
        "function": "supply_chain.inventory_rules.calculate_shortage",
        "inputs": {"qty_available": 10, "qty_needed": 30},
        "expect_key": "return",
        "expect_value": 20,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# FREIGHT AGENT TESTS  (FRT-001 through FRT-008)
# Tests assign_freight_status, assign_carrier_tier, calculate_pickup_delay_days
# ─────────────────────────────────────────────────────────────────────────────

FREIGHT_SCENARIOS = [

    {
        "id": "FRT-001",
        "agent": "freight-agent",
        "description": "freight_status=DELIVERED → DELIVERED",
        "function": "supply_chain.freight_rules.assign_freight_status",
        "inputs": {
            "row": {
                "freight_status": "DELIVERED",
                "freight_hold_flag": "NO",
                "pickup_scheduled_date": str(TEN_AGO),
                "pickup_actual_date": str(TEN_AGO),
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "DELIVERED",
    },

    {
        "id": "FRT-002",
        "agent": "freight-agent",
        "description": "freight_status=IN_TRANSIT → IN_TRANSIT",
        "function": "supply_chain.freight_rules.assign_freight_status",
        "inputs": {
            "row": {
                "freight_status": "IN_TRANSIT",
                "freight_hold_flag": "NO",
                "pickup_scheduled_date": str(THREE_AGO),
                "pickup_actual_date": str(THREE_AGO),
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "IN_TRANSIT",
    },

    {
        "id": "FRT-003",
        "agent": "freight-agent",
        "description": "freight_hold_flag=YES → ON_HOLD (overrides all else)",
        "function": "supply_chain.freight_rules.assign_freight_status",
        "inputs": {
            "row": {
                "freight_status": "SCHEDULED",
                "freight_hold_flag": "YES",
                "pickup_scheduled_date": str(TOMORROW),
                "pickup_actual_date": "",
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "ON_HOLD",
    },

    {
        "id": "FRT-004",
        "agent": "freight-agent",
        "description": "Pickup date past, no actual pickup → PICKUP_MISSED",
        "function": "supply_chain.freight_rules.assign_freight_status",
        "inputs": {
            "row": {
                "freight_status": "SCHEDULED",
                "freight_hold_flag": "NO",
                "pickup_scheduled_date": str(THREE_AGO),
                "pickup_actual_date": "",
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "PICKUP_MISSED",
    },

    {
        "id": "FRT-005",
        "agent": "freight-agent",
        "description": "Future pickup scheduled, no hold → SCHEDULED",
        "function": "supply_chain.freight_rules.assign_freight_status",
        "inputs": {
            "row": {
                "freight_status": "SCHEDULED",
                "freight_hold_flag": "NO",
                "pickup_scheduled_date": str(TOMORROW),
                "pickup_actual_date": "",
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "SCHEDULED",
    },

    {
        "id": "FRT-006",
        "agent": "freight-agent",
        "description": "Score >= 85 → STRONG carrier tier",
        "function": "supply_chain.freight_rules.assign_carrier_tier",
        "inputs": {"score_str": "90"},
        "expect_key": "return",
        "expect_value": "STRONG",
    },

    {
        "id": "FRT-007",
        "agent": "freight-agent",
        "description": "Score < 55 → CRITICAL carrier tier",
        "function": "supply_chain.freight_rules.assign_carrier_tier",
        "inputs": {"score_str": "40"},
        "expect_key": "return",
        "expect_value": "CRITICAL",
    },

    {
        "id": "FRT-008",
        "agent": "freight-agent",
        "description": "Pickup 3 days overdue, no actual pickup → delay days = 3",
        "function": "supply_chain.freight_rules.calculate_pickup_delay_days",
        "inputs": {
            "row": {
                "pickup_scheduled_date": str(THREE_AGO),
                "pickup_actual_date": "",
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": 3,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# WAREHOUSE AGENT TESTS  (WH-001 through WH-006)
# Tests assign_pick_health, calculate_pick_delay_days
# ─────────────────────────────────────────────────────────────────────────────

WAREHOUSE_SCENARIOS = [

    {
        "id": "WH-001",
        "agent": "warehouse-agent",
        "description": "pick_status=COMPLETE → ON_TRACK",
        "function": "supply_chain.warehouse_rules.assign_pick_health",
        "inputs": {
            "row": {
                "pick_status": "COMPLETE",
                "equipment_issue": "NO",
                "staffing_flag": "NO",
                "scheduled_pick_date": str(YESTERDAY),
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "ON_TRACK",
    },

    {
        "id": "WH-002",
        "agent": "warehouse-agent",
        "description": "pick_status=BLOCKED → DELAYED",
        "function": "supply_chain.warehouse_rules.assign_pick_health",
        "inputs": {
            "row": {
                "pick_status": "BLOCKED",
                "equipment_issue": "NO",
                "staffing_flag": "NO",
                "scheduled_pick_date": str(YESTERDAY),
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "DELAYED",
    },

    {
        "id": "WH-003",
        "agent": "warehouse-agent",
        "description": "pick_status=NOT_STARTED, date past → DELAYED",
        "function": "supply_chain.warehouse_rules.assign_pick_health",
        "inputs": {
            "row": {
                "pick_status": "NOT_STARTED",
                "equipment_issue": "NO",
                "staffing_flag": "NO",
                "scheduled_pick_date": str(THREE_AGO),
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "DELAYED",
    },

    {
        "id": "WH-004",
        "agent": "warehouse-agent",
        "description": "pick_status=IN_PROGRESS with equipment_issue=YES → AT_RISK",
        "function": "supply_chain.warehouse_rules.assign_pick_health",
        "inputs": {
            "row": {
                "pick_status": "IN_PROGRESS",
                "equipment_issue": "YES",
                "staffing_flag": "NO",
                "scheduled_pick_date": str(TODAY),
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "AT_RISK",
    },

    {
        "id": "WH-005",
        "agent": "warehouse-agent",
        "description": "pick_status=IN_PROGRESS, no issues → ON_TRACK",
        "function": "supply_chain.warehouse_rules.assign_pick_health",
        "inputs": {
            "row": {
                "pick_status": "IN_PROGRESS",
                "equipment_issue": "NO",
                "staffing_flag": "NO",
                "scheduled_pick_date": str(TODAY),
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": "ON_TRACK",
    },

    {
        "id": "WH-006",
        "agent": "warehouse-agent",
        "description": "calculate_pick_delay_days = 3 for pick 3 days overdue",
        "function": "supply_chain.warehouse_rules.calculate_pick_delay_days",
        "inputs": {
            "row": {
                "pick_status": "NOT_STARTED",
                "scheduled_pick_date": str(THREE_AGO),
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": 3,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# RECOMMENDATION AGENT TESTS  (REC-001 through REC-008)
# Tests calculate_priority_score, needs_escalation, get_responsible_team,
#       get_action_sentence
# ─────────────────────────────────────────────────────────────────────────────

RECOMMENDATION_SCENARIOS = [

    {
        "id": "REC-001",
        "agent": "recommendation-agent",
        "description": "Max delay + CRITICAL severity + freight hold → score = 100 (capped)",
        "function": "supply_chain.recommendation_engine.calculate_priority_score",
        "inputs": {
            "delay_days": 30,
            "severity": "CRITICAL",
            "freight_hold": True,
            "inventory_status": "OUT_OF_STOCK",
        },
        "expect_key": "return",
        "expect_value": 100,
    },

    {
        "id": "REC-002",
        "agent": "recommendation-agent",
        "description": "Zero delay, LOW severity, no hold, healthy stock → score = 5",
        "function": "supply_chain.recommendation_engine.calculate_priority_score",
        "inputs": {
            "delay_days": 0,
            "severity": "LOW",
            "freight_hold": False,
            "inventory_status": "HEALTHY",
        },
        "expect_key": "return",
        "expect_value": 5,
    },

    {
        "id": "REC-003",
        "agent": "recommendation-agent",
        "description": "Score >= 70 → needs_escalation returns True",
        "function": "supply_chain.recommendation_engine.needs_escalation",
        "inputs": {
            "priority_score": 75,
            "delay_status": "DELAYED",
            "freight_hold": False,
        },
        "expect_key": "return",
        "expect_value": True,
    },

    {
        "id": "REC-004",
        "agent": "recommendation-agent",
        "description": "NEED_ACTION status → needs_escalation returns True regardless of score",
        "function": "supply_chain.recommendation_engine.needs_escalation",
        "inputs": {
            "priority_score": 30,
            "delay_status": "NEED_ACTION",
            "freight_hold": False,
        },
        "expect_key": "return",
        "expect_value": True,
    },

    {
        "id": "REC-005",
        "agent": "recommendation-agent",
        "description": "Low score, ON_TIME, no hold → needs_escalation returns False",
        "function": "supply_chain.recommendation_engine.needs_escalation",
        "inputs": {
            "priority_score": 20,
            "delay_status": "ON_TIME",
            "freight_hold": False,
        },
        "expect_key": "return",
        "expect_value": False,
    },

    {
        "id": "REC-006",
        "agent": "recommendation-agent",
        "description": "FREIGHT_HOLD root cause → Freight / Carrier Team assigned",
        "function": "supply_chain.recommendation_engine.get_responsible_team",
        "inputs": {"root_cause": "FREIGHT_HOLD"},
        "expect_key": "return",
        "expect_value": "Freight / Carrier Team",
    },

    {
        "id": "REC-007",
        "agent": "recommendation-agent",
        "description": "BACKORDER root cause → Procurement / Supplier Team assigned",
        "function": "supply_chain.recommendation_engine.get_responsible_team",
        "inputs": {"root_cause": "BACKORDER"},
        "expect_key": "return",
        "expect_value": "Procurement / Supplier Team",
    },

    {
        "id": "REC-008",
        "agent": "recommendation-agent",
        "description": "get_action_sentence returns non-empty string for CARRIER_DELAY",
        "function": "supply_chain.recommendation_engine.get_action_sentence",
        "inputs": {"root_cause": "CARRIER_DELAY"},
        "expect_key": "return_nonempty",   # special check — just verify it's a non-empty string
        "expect_value": True,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# COORDINATOR AGENT TESTS  (COORD-001 through COORD-005)
# Tests get_agent_roster, get_system_status
# ─────────────────────────────────────────────────────────────────────────────

COORDINATOR_SCENARIOS = [

    {
        "id": "COORD-001",
        "agent": "coordinator-agent",
        "description": "get_agent_roster returns 12 agents",
        "function": "supply_chain.coordinator_engine.get_agent_roster",
        "inputs": {},
        "expect_key": "total_agents",
        "expect_value": 12,
    },

    {
        "id": "COORD-002",
        "agent": "coordinator-agent",
        "description": "get_agent_roster reports 65 total tools",
        "function": "supply_chain.coordinator_engine.get_agent_roster",
        "inputs": {},
        "expect_key": "total_tools",
        "expect_value": 65,
    },

    {
        "id": "COORD-003",
        "agent": "coordinator-agent",
        "description": "get_agent_roster has at least 10 live agents",
        "function": "supply_chain.coordinator_engine.get_agent_roster",
        "inputs": {},
        "expect_key": "live_agents",
        "expect_value": 11,
    },

    {
        "id": "COORD-004",
        "agent": "coordinator-agent",
        "description": "get_system_status returns a dict with overall_health key",
        "function": "supply_chain.coordinator_engine.get_system_status",
        "inputs": {},
        "expect_key": "key_exists:overall_health",   # special check — key must exist
        "expect_value": True,
    },

    {
        "id": "COORD-005",
        "agent": "coordinator-agent",
        "description": "get_system_status healthy_count >= 10",
        "function": "supply_chain.coordinator_engine.get_system_status",
        "inputs": {},
        "expect_key": "healthy_count_gte:10",  # special check — value >= threshold
        "expect_value": True,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# EDGE CASE TESTS  (EDGE-001 through EDGE-006)
# Tests boundary values and unexpected inputs that should not crash the system
# ─────────────────────────────────────────────────────────────────────────────

EDGE_CASE_SCENARIOS = [

    {
        "id": "EDGE-001",
        "agent": "shipping-delay-agent",
        "description": "Empty scheduled_pick_date → delay days = 0 (no crash)",
        "function": "supply_chain.rules.calculate_delay_days",
        "inputs": {
            "row": {"scheduled_pick_date": ""},
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": 0,
    },

    {
        "id": "EDGE-002",
        "agent": "inventory-agent",
        "description": "calculate_shortage with equal qty → returns 0 (no negative shortage)",
        "function": "supply_chain.inventory_rules.calculate_shortage",
        "inputs": {"qty_available": 50, "qty_needed": 50},
        "expect_key": "return",
        "expect_value": 0,
    },

    {
        "id": "EDGE-003",
        "agent": "freight-agent",
        "description": "Non-numeric carrier score → UNKNOWN tier (no crash)",
        "function": "supply_chain.freight_rules.assign_carrier_tier",
        "inputs": {"score_str": "N/A"},
        "expect_key": "return",
        "expect_value": "UNKNOWN",
    },

    {
        "id": "EDGE-004",
        "agent": "freight-agent",
        "description": "Empty pickup_scheduled_date → pickup delay = 0 (no crash)",
        "function": "supply_chain.freight_rules.calculate_pickup_delay_days",
        "inputs": {
            "row": {
                "pickup_scheduled_date": "",
                "pickup_actual_date": "",
            },
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": 0,
    },

    {
        "id": "EDGE-005",
        "agent": "recommendation-agent",
        "description": "Unknown root cause → get_responsible_team returns fallback string",
        "function": "supply_chain.recommendation_engine.get_responsible_team",
        "inputs": {"root_cause": "TOTALLY_UNKNOWN_CODE"},
        "expect_key": "return",
        "expect_value": "Supply Chain Coordinator",
    },

    {
        "id": "EDGE-006",
        "agent": "shipping-delay-agent",
        "description": "calculate_delay_days never returns negative for future date",
        "function": "supply_chain.rules.calculate_delay_days",
        "inputs": {
            "row": {"scheduled_pick_date": str(FUTURE_5)},
            "today": TODAY,
        },
        "expect_key": "return",
        "expect_value": 0,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# MASTER SCENARIO LIST
# test_runner.py imports ALL_SCENARIOS and runs every test in this list.
# To skip a test temporarily, remove it from this list (don't delete it).
# ─────────────────────────────────────────────────────────────────────────────

ALL_SCENARIOS = (
    SHIPPING_SCENARIOS
    + INVENTORY_SCENARIOS
    + FREIGHT_SCENARIOS
    + WAREHOUSE_SCENARIOS
    + RECOMMENDATION_SCENARIOS
    + COORDINATOR_SCENARIOS
    + EDGE_CASE_SCENARIOS
)

# Quick summary for imports
SCENARIO_COUNT = len(ALL_SCENARIOS)
AGENTS_COVERED = sorted(set(s["agent"] for s in ALL_SCENARIOS))
