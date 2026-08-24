"""
Tests for Gap Analysis Agent 6 & Capability Manifest Verification.
Tests multi-service fixture repo (forecasting, routing, scraping, webhook) to assert:
1. Each distinct service is individually detected as a named capability with concrete evidence.
2. Gap analysis matches corresponding requirements and cites specific capability names and evidence files.
3. Unrelated requirements are marked MISSING with clear non-boilerplate reasons.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from platform_core.github.analyzer import RepositoryStaticAnalyzer
from platform_core.agents.understanding_agent import ProjectUnderstandingAgent
from platform_core.agents.gap_analysis_agent import GapAnalysisAgent, _BANNED_BOILERPLATE


def get_multi_service_fixture():
    """Provides a realistic fixture repository with 4 distinct services, routes, and data models."""
    file_contents = {
        "services/forecasting.py": '''"""Demand forecasting service using time-series models."""
from prophet import Prophet
import pandas as pd

class DemandForecaster:
    """Generates predictive stock and demand forecasts."""
    def predict_demand(self, historical_data: pd.DataFrame) -> dict:
        """Fit time series and return forecasted demand."""
        return {"forecast": [100, 120, 140]}
''',
        "services/routing.py": '''"""Vehicle routing and fleet dispatch optimization service."""
class RouteOptimizer:
    """Calculates shortest path and vehicle routing routes using Dijkstra."""
    def optimize_route(self, stops: list, fleet_capacity: int) -> dict:
        """Return optimized delivery route sequence."""
        return {"optimized_stops": stops}
''',
        "services/scraper.py": '''"""Web scraping and HTML data extraction pipeline."""
from bs4 import BeautifulSoup
import requests

class SIHScraper:
    """Scrapes and parses portal HTML datasets."""
    def scrape_portal(self, url: str) -> list:
        """Extract tabular data without truncation."""
        return [{"id": "26001", "data": "clean"}]
''',
        "services/webhook.py": '''"""Webhook automation and event dispatch system."""
import hmac
import hashlib

class WebhookManager:
    """Handles event subscriptions and HMAC-signed webhook delivery."""
    def dispatch_event(self, event_type: str, payload: dict) -> bool:
        """Dispatch signed event to subscriber callbacks."""
        return True
''',
        "api/routes.py": '''from fastapi import APIRouter
router = APIRouter()

@router.post("/api/v1/forecast")
def get_forecast():
    """Generate demand forecast."""
    return {"status": "ok"}

@router.post("/api/v1/route")
def get_route():
    """Calculate optimal route."""
    return {"status": "ok"}
''',
        "models.py": '''from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class DeliveryOrder(Base):
    __tablename__ = "delivery_orders"
    id = Column(Integer, primary_key=True)
    destination = Column(String)
    status = Column(String)
'''
    }

    file_tree = [
        {"path": p, "size": len(c), "is_priority": True, "extension": ".py"}
        for p, c in file_contents.items()
    ]
    repo_info = {
        "repo_name": "SmartSupply-Platform",
        "owner": "logistics-ai",
        "description": "Smart supply chain platform with demand forecasting, vehicle routing, web scraping, and webhook dispatch.",
        "primary_language": "Python"
    }

    return repo_info, file_tree, file_contents


def test_multi_service_capability_detection():
    """Asserts that all 4 distinct services are detected as named capabilities with evidence."""
    print("=" * 60, flush=True)
    print("TESTING MULTI-SERVICE STATIC AST CAPABILITY EXTRACTION", flush=True)
    print("=" * 60, flush=True)

    repo_info, file_tree, file_contents = get_multi_service_fixture()

    # 1. Static AST Analysis
    static_res = RepositoryStaticAnalyzer.analyze_repository(repo_info, file_tree, file_contents)
    
    assert "endpoints" in static_res
    assert len(static_res["endpoints"]) >= 2
    assert "data_models" in static_res
    assert len(static_res["data_models"]) >= 1
    assert "file_findings" in static_res
    assert len(static_res["file_findings"]) >= 5

    # 2. Understanding Agent Synthesizes Capability Manifest
    understanding_agent = ProjectUnderstandingAgent()
    context = {
        "repo_info": repo_info,
        "static_analysis": static_res,
        "file_contents": file_contents,
        "file_tree": file_tree
    }
    understanding_res = understanding_agent.run(context)
    manifest = understanding_res.get("capability_manifest", {})

    cap_names = [c["name"] for c in manifest.get("capabilities", [])]
    print(f"Detected Capabilities in Manifest: {cap_names}", flush=True)

    # Assert all 4 distinct capabilities are present
    assert any("forecast" in c.lower() for c in cap_names), "Demand forecasting capability not detected"
    assert any("rout" in c.lower() for c in cap_names), "Vehicle routing capability not detected"
    assert any("scrap" in c.lower() for c in cap_names), "Web scraping capability not detected"
    assert any("webhook" in c.lower() for c in cap_names), "Webhook automation capability not detected"

    # Assert evidence is attached per capability
    for c in manifest["capabilities"]:
        assert len(c.get("evidence", [])) > 0, f"No evidence attached to capability {c['name']}"
        print(f"  [OK] {c['name']} -> Evidence: {c['evidence']}", flush=True)

    # 3. Gap Analysis against specific multi-service requirements
    print("\n--- Testing Gap Analysis with Capability Manifest ---", flush=True)
    problem_analysis = {
        "explicit_requirements": [
            "Predictive time-series model for forecasting seasonal commodity demand",
            "Optimal vehicle routing and fleet dispatch for multi-stop delivery",
            "Automated web scraping pipeline to extract real-time market portal prices",
            "Event-driven webhook dispatch system for instant subscriber notifications",
            "EEG biomedical brainwave analysis for neurodegenerative disease diagnosis"
        ],
        "technical_requirements": [
            "REST API service layer with endpoint definitions",
            "Relational database storage for persistent delivery order tracking"
        ]
    }

    gap_agent = GapAnalysisAgent()
    gap_res = gap_agent.run({
        "analysis_data": {
            "capability_manifest": manifest,
            "core_features": cap_names,
            "detected_languages": ["Python"],
            "backend_framework": "FastAPI",
            "database_tech": "SQLAlchemy"
        },
        "problem_analysis": problem_analysis
    })

    matrix = gap_res["requirement_matrix"]
    assert len(matrix) == 7

    # Validate individual verdicts
    forecasting_row = next(r for r in matrix if "forecasting" in r["requirement"].lower() or "predictive" in r["requirement"].lower())
    assert forecasting_row["status"] in ("MATCH", "IMPLEMENTED")
    assert "forecast" in forecasting_row["reason"].lower() or "services/forecasting.py" in forecasting_row["reason"].lower()

    routing_row = next(r for r in matrix if "routing" in r["requirement"].lower())
    assert routing_row["status"] in ("MATCH", "IMPLEMENTED")
    assert "rout" in routing_row["reason"].lower() or "services/routing.py" in routing_row["reason"].lower()

    scraping_row = next(r for r in matrix if "scraping" in r["requirement"].lower())
    assert scraping_row["status"] in ("MATCH", "IMPLEMENTED")
    assert "scrap" in scraping_row["reason"].lower() or "services/scraper.py" in scraping_row["reason"].lower()

    webhook_row = next(r for r in matrix if "webhook" in r["requirement"].lower())
    assert webhook_row["status"] in ("MATCH", "IMPLEMENTED")
    assert "webhook" in webhook_row["reason"].lower() or "services/webhook.py" in webhook_row["reason"].lower()

    eeg_row = next(r for r in matrix if "eeg" in r["requirement"].lower())
    assert eeg_row["status"] == "MISSING"

    # Assert no banned boilerplate
    for r in matrix:
        for b in _BANNED_BOILERPLATE:
            assert b.lower() not in r["reason"].lower()

    print("[PASS] All 4 services individually detected with evidence and correctly mapped in Gap Matrix.", flush=True)


if __name__ == "__main__":
    test_multi_service_capability_detection()
