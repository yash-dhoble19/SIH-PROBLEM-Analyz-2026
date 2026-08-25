"""Fresh ChainMind matching run with per-stage latency telemetry."""

import json
import logging
import time

from platform_core.database.connection import SessionLocal
from platform_core.agents.matching_agent import SIHMatchingAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")

CHAINMIND_ANALYSIS = {
    "repo_name": "ChainMind",
    "project_summary": "Adaptive Supply Chain & Logistics Engine with Demand Forecasting and Vehicle Route Optimization",
    "description": "Adaptive Supply Chain & Logistics Engine with Demand Forecasting and Vehicle Route Optimization",
    "project_type": "Data Analytics & ML Pipeline",
    "detected_languages": ["Python"],
    "target_domains": ["Transportation & Logistics", "Smart Automation"],
    "domain_signals": ["forecasting", "routing", "logistics", "database", "api"],
    "core_features": [
        "Time-series demand forecasting with automated ARIMA / Prophet models",
        "Multi-depot vehicle routing problem (VRP) optimization engine",
        "Warehouse inventory rebalancing and safety stock calculation",
        "FastAPI REST endpoints for consignment tracking and dispatch"
    ],
    "technical_capabilities": ["REST API Service Layer", "Time Series Forecasting", "Route Optimization Engine"],
    "capability_manifest": {
        "tech_stack": ["Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "Prophet", "NumPy", "Pandas"],
        "capabilities": [
            {"name": "Time-Series Demand Forecasting", "evidence": ["ProphetModel in /models/forecast.py", "predict_demand()"]},
            {"name": "Vehicle Routing & Fleet Dispatch", "evidence": ["VRPDispatcher in /routing/engine.py", "optimize_routes()"]},
            {"name": "REST API Service Layer", "evidence": ["FastAPI app in /main.py", "POST /api/v1/dispatch"]},
            {"name": "Relational Data Persistence", "evidence": ["SQLAlchemy models", "Consignment, Fleet, Warehouse tables"]}
        ],
        "endpoints": [
            {"method": "POST", "path": "/api/v1/forecast/demand"},
            {"method": "POST", "path": "/api/v1/routing/optimize"},
            {"method": "GET", "path": "/api/v1/shipments/{id}"}
        ],
        "data_models": [
            {"model_name": "Consignment", "columns": ["id", "origin", "destination", "weight", "status"]},
            {"model_name": "FleetVehicle", "columns": ["id", "capacity", "assigned_route_id"]}
        ],
        "domain_signals": ["forecasting", "routing", "logistics", "database", "api"]
    }
}


def main():
    db = SessionLocal()
    matcher = SIHMatchingAgent()
    print(f"AI provider backend: {type(matcher.ai_provider).__name__}", flush=True)

    context = {
        "db": db,
        "analysis_data": CHAINMIND_ANALYSIS,
        "repo_info": {
            "repo_name": "ChainMind",
            "description": CHAINMIND_ANALYSIS["description"],
        },
    }

    wall_started = time.perf_counter()
    result = matcher.run(context)
    wall_ms = round((time.perf_counter() - wall_started) * 1000, 1)

    print("\n" + "=" * 80)
    print("CHAINMIND FRESH RUN — PER-STAGE TIMING")
    print("=" * 80)
    print(json.dumps(result["timing_breakdown_ms"], indent=2))
    print(f"\nembedding_backend={result['embedding_backend']} requested={result['embedding_provider_requested']} fallback_active={result['embedding_fallback_active']}")
    vetoed = result["vetoed_matches"]
    print(f"\nMATCH COUNT: {len(result['top_matches'])} scored matches ({len(vetoed)} vetoed by intent guard)")
    for i, m in enumerate(result["top_matches"], 1):
        print(
            f"  #{i} {m['problem_statement_id']} ({m['overall_match_score']}%) "
            f"aim={m['aim_alignment_score']} sem={m['semantic_similarity']} | {m['title'][:60]}"
        )
    print(f"\nWALL CLOCK TOTAL: {wall_ms} ms ({round(wall_ms / 1000, 1)}s)")
    db.close()


if __name__ == "__main__":
    main()
