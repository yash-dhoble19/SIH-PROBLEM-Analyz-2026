"""
Regression test for Multi-Repository Isolation, Grounding Citations, and Cross-Repo Cache Contamination Prevention.
"""

import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from platform_core.database.connection import SessionLocal
from platform_core.github.analyzer import RepositoryStaticAnalyzer
from platform_core.agents.understanding_agent import ProjectUnderstandingAgent
from platform_core.agents.matching_agent import SIHMatchingAgent


def test_multi_repo_isolation_and_grounding():
    print("=" * 65, flush=True)
    print("TESTING MULTI-REPOSITORY ISOLATION & GROUNDED CAPABILITIES", flush=True)
    print("=" * 65, flush=True)

    # -------------------------------------------------------------
    # 1. Repo A: Note-Taking / Habit Journal App
    # -------------------------------------------------------------
    repo_a_info = {
        "repo_name": "MindBloom-Journal",
        "owner": "productivity-team",
        "description": "Minimalist markdown note-taking and daily habit tracker app for self-growth.",
        "primary_language": "JavaScript"
    }
    repo_a_tree = [
        {"path": "README.md", "size": 1200, "is_priority": True, "extension": ".md"},
        {"path": "package.json", "size": 400, "is_priority": True, "extension": ".json"},
        {"path": "src/App.js", "size": 1500, "is_priority": True, "extension": ".js"},
    ]
    repo_a_contents = {
        "README.md": """# MindBloom Journal
A personal productivity tool for daily journaling and habit tracking.

## Features
- Markdown note editor with real-time preview
- Daily mood check-in and habit streak logging
- Tag-based personal note organization
- Local storage and JSON export
""",
        "package.json": '{"dependencies": {"react": "^18.2.0", "lucide-react": "^0.263.1"}}',
        "src/App.js": 'import React from "react"; export default function App() { return <div>Notes</div>; }'
    }

    # Analyze Repo A
    static_a = RepositoryStaticAnalyzer.analyze_repository(repo_a_info, repo_a_tree, repo_a_contents)
    understanding_agent = ProjectUnderstandingAgent()
    
    res_a = understanding_agent.run({
        "repo_info": repo_a_info,
        "static_analysis": static_a,
        "file_contents": repo_a_contents,
        "file_tree": repo_a_tree
    })

    print("\n--- Repo A Profile (MindBloom-Journal) ---", flush=True)
    print(f"Summary: {res_a['project_summary']}", flush=True)
    print(f"Domains: {res_a['target_domains']}", flush=True)
    print(f"Capabilities: {[c['capability'] for c in res_a['grounded_capabilities']]}", flush=True)

    # Assert Repo A has note-taking terms and zero supply-chain/GIS terms
    features_a_text = " ".join([c["capability"] for c in res_a["grounded_capabilities"]] + res_a["target_domains"]).lower()
    assert any(k in features_a_text for k in ["note", "habit", "journal", "markdown"]), "Repo A should contain note-taking terms"
    assert "logistics" not in features_a_text, "Repo A must not contain logistics terms"
    assert not re.search(r"\b(gis|geospatial|arcgis|qgis)\b", features_a_text), "Repo A must not contain GIS terms"

    # -------------------------------------------------------------
    # 2. Repo B: Supply Chain & Inventory Management Platform
    # -------------------------------------------------------------
    repo_b_info = {
        "repo_name": "supply-chain-management",
        "owner": "logistics-team",
        "description": "Enterprise supply chain optimization, inventory tracking, demand forecasting, and procurement platform.",
        "primary_language": "Python"
    }
    repo_b_tree = [
        {"path": "README.md", "size": 2500, "is_priority": True, "extension": ".md"},
        {"path": "requirements.txt", "size": 500, "is_priority": True, "extension": ".txt"},
        {"path": "backend/main.py", "size": 3000, "is_priority": True, "extension": ".py"},
        {"path": "backend/models/forecasting.py", "size": 2000, "is_priority": True, "extension": ".py"},
    ]
    repo_b_contents = {
        "README.md": """# Supply Chain Management & Inventory Optimization Platform
An intelligent platform for end-to-end supply chain visibility, multi-warehouse inventory management, and automated supplier procurement.

## Core Features
- Multi-warehouse real-time inventory tracking and stock reordering
- AI-driven demand forecasting and safety stock estimation
- Automated purchase order generation and vendor procurement workflows
- Freight and logistics shipment tracking across multi-modal transit
- Supplier performance analytics and risk scorecards
""",
        "requirements.txt": """fastapi==0.110.0
uvicorn==0.28.0
sqlalchemy==2.0.28
prophet==1.1.5
pandas==2.2.1
numpy==1.26.4
psycopg2-binary==2.9.9
""",
        "backend/main.py": """from fastapi import FastAPI
app = FastAPI(title="Supply Chain Management API")
@app.get("/api/inventory/stock")
def get_stock(): return {"status": "ok"}
@app.get("/api/procurement/orders")
def get_orders(): return {"orders": []}
@app.post("/api/forecast/demand")
def forecast_demand(): return {"forecast": []}
""",
        "backend/models/forecasting.py": """import pandas as pd
from prophet import Prophet
def generate_demand_forecast(df):
    m = Prophet()
    m.fit(df)
    return m.predict(df)
"""
    }

    # Analyze Repo B directly in the same execution session
    static_b = RepositoryStaticAnalyzer.analyze_repository(repo_b_info, repo_b_tree, repo_b_contents)
    res_b = understanding_agent.run({
        "repo_info": repo_b_info,
        "static_analysis": static_b,
        "file_contents": repo_b_contents,
        "file_tree": repo_b_tree
    })

    print("\n--- Repo B Profile (supply-chain-management) ---", flush=True)
    print(f"Summary: {res_b['project_summary']}", flush=True)
    print(f"Domains: {res_b['target_domains']}", flush=True)
    print(f"Capabilities: {[c['capability'] for c in res_b['grounded_capabilities']]}", flush=True)

    caps_b = [c["capability"] for c in res_b["grounded_capabilities"]]
    caps_b_text = (" ".join(caps_b) + " " + res_b["project_summary"] + " " + " ".join(res_b["target_domains"])).lower()

    # Assert Grounding & Zero Contamination
    assert any(k in caps_b_text for k in ["supply", "inventory", "procurement", "forecasting", "logistics"]), "Repo B must contain supply chain terms"
    assert not re.search(r"\b(gis|geospatial|arcgis|qgis)\b", caps_b_text), "CRITICAL: Repo B must NOT contain GIS or geospatial terms"
    assert "note" not in caps_b_text, "Repo B must NOT contain terms from Repo A (zero cross-repo contamination)"
    assert "habit" not in caps_b_text, "Repo B must NOT contain terms from Repo A"

    print("\n[PASS] Repo B successfully extracted supply chain capabilities with zero GIS/note-taking contamination.", flush=True)

    # -------------------------------------------------------------
    # 3. Test Intent Alignment Guard for Repo B against SIH Problem Statements
    # -------------------------------------------------------------
    matcher = SIHMatchingAgent()

    # Unrelated Cybercrime / Threat Auditing Statement
    cybercrime_ps = {
        "id": "SIH26184",
        "title": "Automated Cybercrime Intelligence and Threat Signature Analysis Platform",
        "theme": "Blockchain & Cybersecurity",
        "organization": "National Cyber Crime Threat Analytics Unit",
        "background": "Detecting zero-day ransomware signatures, packet anomalies, and dark-web extortion campaigns.",
        "description": "Develop a forensic packet inspector and cybercrime threat hunting framework for national CERT teams.",
        "expected_solution": "Real-time SIEM log parser, firewall policy auditor, and automated malware sandbox dispatch."
    }

    # Relevant Smart Logistics / Supply Chain Statement
    logistics_ps = {
        "id": "SIH26002",
        "title": "AI-Based Smart Logistics and Accessibility Intelligence Platform for North Eastern Region (NER)",
        "theme": "Transportation & Logistics",
        "organization": "Ministry of Development of North Eastern Region (MDoNER)",
        "background": "Complex multi-modal freight routes require intelligent route planning, freight consignment tracking, and warehouse inventory optimization.",
        "description": "Create an end-to-end logistics platform that optimizes multimodal supply chains, inventory replenishment, and freight transit under disrupted weather conditions.",
        "expected_solution": "A centralized logistics dashboard with demand forecasting, freight fleet tracking, and supplier inventory reordering."
    }

    repo_b_profile = {
        "repo_name": repo_b_info["repo_name"],
        "project_summary": res_b["project_summary"],
        "description": repo_b_info["description"],
        "core_features": caps_b,
        "detected_features": caps_b,
        "target_domains": res_b["target_domains"],
        "technical_capabilities": ["FastAPI REST Services", "Prophet Time-Series Forecasting", "PostgreSQL Storage"]
    }

    # Evaluate Intent Alignment against Cybercrime PS
    cyber_intent = matcher.assess_intent_alignment(repo_b_profile, cybercrime_ps)
    print(f"\nCybercrime PS Intent Result: domain_match={cyber_intent['domain_match']}, aim_score={cyber_intent['aim_alignment_score']}%", flush=True)
    print(f"Reasoning: {cyber_intent['reasoning']}", flush=True)
    assert cyber_intent["domain_match"] is False, "Supply chain repo must NOT match cybercrime domain"
    assert cyber_intent["aim_alignment_score"] < 40.0, "Aim alignment score for cybercrime must be < 40%"

    # Evaluate Intent Alignment against Logistics PS
    logistics_intent = matcher.assess_intent_alignment(repo_b_profile, logistics_ps)
    print(f"\nLogistics PS Intent Result: domain_match={logistics_intent['domain_match']}, aim_score={logistics_intent['aim_alignment_score']}%", flush=True)
    print(f"Reasoning: {logistics_intent['reasoning']}", flush=True)
    assert logistics_intent["domain_match"] is True, "Supply chain repo MUST match logistics domain"
    assert logistics_intent["aim_alignment_score"] >= 80.0, "Aim alignment score for logistics must be >= 80%"

    print("\n" + "=" * 65, flush=True)
    print("MULTI-REPO ISOLATION & GROUNDING TEST PASSED (0% CONTAMINATION)", flush=True)
    print("=" * 65, flush=True)


if __name__ == "__main__":
    test_multi_repo_isolation_and_grounding()
