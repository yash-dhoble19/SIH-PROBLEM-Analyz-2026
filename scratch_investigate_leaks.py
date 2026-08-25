from platform_core.database.connection import SessionLocal
from platform_core.database.models import ProblemStatement
from platform_core.agents.matching_agent import SIHMatchingAgent
from platform_core.ai.providers import HeuristicAIProvider
import json

db = SessionLocal()

# 1. Inspect SIH26179 and SIH26157 raw data
ps_179 = db.query(ProblemStatement).filter_by(id="SIH26179").first()
ps_157 = db.query(ProblemStatement).filter_by(id="SIH26157").first()

print("="*80)
print("INSPECTING SIH26179:")
print("="*80)
if ps_179:
    print(f"ID: {ps_179.id}")
    print(f"Title: {ps_179.title}")
    print(f"Theme: {ps_179.theme}")
    print(f"Org: {ps_179.organization}")
    print(f"Category: {ps_179.category}")
    print(f"Description:\n{ps_179.description}")
    print(f"Expected Solution:\n{ps_179.expected_solution}")

print("\n" + "="*80)
print("INSPECTING SIH26157:")
print("="*80)
if ps_157:
    print(f"ID: {ps_157.id}")
    print(f"Title: {ps_157.title}")
    print(f"Theme: {ps_157.theme}")
    print(f"Org: {ps_157.organization}")
    print(f"Category: {ps_157.category}")
    print(f"Description:\n{ps_157.description}")
    print(f"Expected Solution:\n{ps_157.expected_solution}")

# 2. Check Groq reasoning text for ChainMind x SIH26179
print("\n" + "="*80)
print("GROQ INTENT REASONING FOR ChainMind x SIH26179:")
print("="*80)
matcher = SIHMatchingAgent() # Live Groq provider
chainmind_profile = {
    "repo_name": "ChainMind",
    "project_summary": "Adaptive Supply Chain & Logistics Engine with Demand Forecasting and Vehicle Route Optimization",
    "description": "Adaptive Supply Chain & Logistics Engine with Demand Forecasting and Vehicle Route Optimization",
    "target_domains": ["Transportation & Logistics", "Smart Automation"],
    "domain_signals": ["forecasting", "routing", "logistics", "database", "api"],
    "core_features": ["Time-series demand forecasting", "Multi-depot vehicle routing (VRP) optimization", "Warehouse inventory rebalancing"],
    "capability_manifest": {
        "tech_stack": ["Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "Prophet"],
        "capabilities": [{"name": "Time-Series Demand Forecasting"}, {"name": "Vehicle Routing & Fleet Dispatch"}]
    }
}

if ps_179:
    groq_res_179 = matcher.assess_intent_alignment(chainmind_profile, ps_179)
    print("Groq Intent Result for ChainMind x SIH26179:")
    print(json.dumps(groq_res_179, indent=2))

# 3. Check cross-repo repeats across all 4 repos
print("\n" + "="*80)
print("CROSS-REPO REPEAT ANALYSIS ACROSS ALL 4 REPOS:")
print("="*80)

repos = [
    {
        "name": "SIH-Platform",
        "summary": "AI-Powered Repository Analyzer and Hackathon Problem Statement Matching Platform",
        "domains": ["Smart Automation", "Smart Education"],
        "signals": ["software", "api", "database", "scraping", "matching"],
        "features": ["AST parsing", "Problem triage", "Architecture blueprint"]
    },
    {
        "name": "ChainMind",
        "summary": "Adaptive Supply Chain & Logistics Engine with Demand Forecasting and Vehicle Route Optimization",
        "domains": ["Transportation & Logistics", "Smart Automation"],
        "signals": ["forecasting", "routing", "logistics", "database", "api"],
        "features": ["Demand forecasting", "Vehicle routing", "Consignment tracking"]
    },
    {
        "name": "GrowthOS",
        "summary": "AI-Powered Self-Growth and Career Coaching Platform with Habit Tracking and Skill Roadmaps",
        "domains": ["Smart Education", "Smart Automation"],
        "signals": ["education", "learning", "skill", "habits", "api"],
        "features": ["Learning roadmaps", "Skill gap assessment", "Habit tracking"]
    },
    {
        "name": "NeuroDetect",
        "summary": "AI-Powered EEG Brainwave Analysis for Early Alzheimer Detection and Cognitive Health Monitoring",
        "domains": ["MedTech / BioTech / HealthTech"],
        "signals": ["healthcare", "biomedical", "medtech / biotech / healthtech", "api"],
        "features": ["EEG preprocessing", "Feature extraction", "CNN classification"]
    }
]

repo_qualified_map = {}
h_matcher = SIHMatchingAgent(ai_provider=HeuristicAIProvider())

for r in repos:
    analysis_data = {
        "repo_name": r["name"],
        "project_summary": r["summary"],
        "description": r["summary"],
        "target_domains": r["domains"],
        "domain_signals": r["signals"],
        "core_features": r["features"],
        "capability_manifest": {"capabilities": [{"name": f} for f in r["features"]], "tech_stack": ["Python"]}
    }
    res = h_matcher.run({"db": db, "analysis_data": analysis_data, "repo_info": {"repo_name": r["name"], "description": r["summary"]}})
    qualified_ids = [m["problem_statement_id"] for m in res["top_matches"]]
    repo_qualified_map[r["name"]] = qualified_ids
    print(f"Repo {r['name']} qualified {len(qualified_ids)} matches: {qualified_ids}")

# Count statement frequency across repos
from collections import Counter
all_pids = []
for pids in repo_qualified_map.values():
    all_pids.extend(pids)

counts = Counter(all_pids)
print("\nStatements appearing across multiple repos:")
for pid, c in counts.most_common():
    if c >= 2:
        ps_obj = db.query(ProblemStatement).filter_by(id=pid).first()
        title = ps_obj.title if ps_obj else ""
        theme = ps_obj.theme if ps_obj else ""
        matched_in = [r for r, ids in repo_qualified_map.items() if pid in ids]
        print(f"  - [{pid}] appears in {c}/4 repos ({', '.join(matched_in)}) | Theme: {theme} | Title: {title[:60]}")

db.close()
