"""
Unit & Integration Tests for Agent 10: Pivot Advisor Agent.
Verifies trigger condition guardrails, foundation reuse mechanisms, required additions, and prompt construction.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from platform_core.agents.pivot_advisor_agent import PivotAdvisorAgent


def test_pivot_advisor_trigger_conditions():
    """Verifies that the Pivot Advisor only executes when 15% <= domain_alignment AND reusability < 80%."""
    agent = PivotAdvisorAgent()

    # Case 1: Low domain alignment (< 15%) -> Should NOT trigger
    assert agent.should_trigger(domain_alignment=10.0, reusability_score=40.0) is False
    assert agent.should_trigger(domain_alignment=0.0, reusability_score=20.0) is False

    # Case 2: Near-perfect reusability (>= 80%) -> Should NOT trigger
    assert agent.should_trigger(domain_alignment=85.0, reusability_score=85.0) is False
    assert agent.should_trigger(domain_alignment=90.0, reusability_score=80.0) is False

    # Case 3: Valid Pivot Candidate (15% <= domain_alignment AND reusability < 80%) -> MUST trigger
    assert agent.should_trigger(domain_alignment=75.0, reusability_score=25.0) is True
    assert agent.should_trigger(domain_alignment=15.0, reusability_score=0.0) is True
    assert agent.should_trigger(domain_alignment=50.0, reusability_score=79.9) is True

    # When context fails trigger, run() returns None
    res_skipped = agent.run({
        "domain_alignment": 10.0,
        "reusability_score": 50.0,
        "capability_manifest": {},
        "requirement_matrix": []
    })
    assert res_skipped is None, "Pivot Advisor must return None when trigger condition is not met"


def test_pivot_advisor_transformation_generation():
    """Verifies complete transformation plan generation for a candidate project."""
    agent = PivotAdvisorAgent()

    manifest = {
        "repo": {"name": "smart-inventory", "owner": "logistics-corp"},
        "capabilities": [
            {
                "name": "Time-Series Demand Forecasting",
                "evidence": ["services/forecasting.py: generate_demand_forecast()"],
                "confidence": 0.95
            },
            {
                "name": "REST API Service Layer",
                "evidence": ["api/routes.py: GET /api/inventory/stock"],
                "confidence": 0.95
            }
        ],
        "endpoints": [
            {"method": "GET", "path": "/api/inventory/stock", "file": "api/routes.py"},
            {"method": "POST", "path": "/api/forecast/demand", "file": "api/routes.py"}
        ],
        "data_models": [
            {"model_name": "InventoryItem", "table_name": "inventory_items", "columns": ["id", "sku", "quantity"], "file": "models.py"}
        ]
    }

    gap_matrix = [
        {
            "requirement": "Multi-warehouse Inventory Tracking",
            "sih_expects": "Centralized stock ledger across distributed fulfillment centers",
            "current_project": "services/forecasting.py",
            "status": "PARTIAL",
            "reason": "Basic stock lookup exists in api/routes.py but lacks multi-facility synchronization"
        },
        {
            "requirement": "Automated Supplier Procurement Dispatch",
            "sih_expects": "Automated purchase order generation via EDI / REST to vendors",
            "current_project": "None",
            "status": "MISSING",
            "reason": "No procurement or purchase order endpoints found in codebase"
        },
        {
            "requirement": "Multi-Modal Freight Fleet Routing",
            "sih_expects": "Dynamic road/rail consignment routing under severe weather delays",
            "current_project": "None",
            "status": "MISSING",
            "reason": "No route optimization or GIS routing logic detected"
        }
    ]

    problem_statement = {
        "id": "SIH26002",
        "title": "AI-Based Smart Logistics and Accessibility Intelligence Platform for North Eastern Region (NER)",
        "theme": "Transportation & Logistics",
        "organization": "Ministry of Development of North Eastern Region (MDoNER)",
        "expected_solution": "A centralized logistics dashboard with demand forecasting, freight fleet tracking, and supplier inventory reordering."
    }

    context = {
        "capability_manifest": manifest,
        "requirement_matrix": gap_matrix,
        "problem_statement": problem_statement,
        "domain_alignment": 80.0,
        "reusability_score": 33.3,
        "analysis_data": {
            "backend_framework": "FastAPI",
            "frontend_framework": "React",
            "detected_languages": ["Python", "JavaScript"]
        },
        "repo_info": {
            "repo_name": "smart-inventory",
            "owner": "logistics-corp"
        }
    }

    result = agent.run(context)
    assert result is not None, "Pivot Advisor must produce output for valid candidate"
    assert result["is_applicable"] is True
    assert result["domain_alignment"] == 80.0
    assert result["reusability_score"] == 33.3

    # Check Reused Foundations
    reused = result["reused_foundations"]
    assert len(reused) >= 1, "Must extract at least one reused foundation"
    assert any("Inventory" in r["capability"] or "API" in r["capability"] for r in reused)
    for r in reused:
        assert "capability" in r and "source_evidence" in r and "reuse_mechanism" in r
        assert len(r["reuse_mechanism"]) > 20, "Reuse mechanism must be a descriptive explanation"

    # Check Required Additions
    additions = result["required_additions"]
    assert len(additions) >= 2, "Must extract required additions for missing features"
    for a in additions:
        assert "feature" in a and "priority" in a and "effort_estimate" in a
        assert "build_approach" in a and "integration_target" in a
        assert "why_needed" in a

    # Check Prompt Construction
    prompt = result["copy_paste_prompt"]
    assert "REPOSITORY PIVOT TRANSFORMATION PROMPT" in prompt
    assert "smart-inventory" in prompt
    assert "SIH26002" in prompt
    assert "REUSABLE ARCHITECTURAL FOUNDATIONS" in prompt
    assert "REQUIRED NET-NEW ADDITIONS" in prompt

    print("\n[PASS] Pivot Advisor Agent produced complete transformation plan with concrete reuse mechanisms & prompt.")


if __name__ == "__main__":
    test_pivot_advisor_trigger_conditions()
    test_pivot_advisor_transformation_generation()
