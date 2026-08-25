import sys
from platform_core.database.connection import SessionLocal
from platform_core.agents.matching_agent import SIHMatchingAgent
from platform_core.ai.providers import HeuristicAIProvider

def run_sanity_sweep():
    db = SessionLocal()
    # Use standard matcher
    matcher = SIHMatchingAgent(ai_provider=HeuristicAIProvider())

    # Define the 4 repos for the comprehensive sweep
    repos = [
        {
            "name": "SIH-PROBLEM-Analyz-2026 (SIH Platform)",
            "summary": "AI-Powered Repository Analyzer and Hackathon Problem Statement Matching Platform for SIH 2026",
            "type": "Full-Stack Web Application & AI Agent Orchestration Pipeline",
            "domains": ["Smart Automation", "Smart Education"],
            "signals": ["software", "api", "database", "scraping", "matching"],
            "features": [
                "Automated GitHub AST codebase parsing and capability manifest extraction",
                "Full-corpus AI problem statement triage and multi-dimensional match ranking",
                "Implementation architecture blueprint and solution roadmap generation",
                "Interactive web dashboard with pgvector semantic similarity visualization"
            ],
            "manifest": {
                "tech_stack": ["Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "JavaScript", "HTML5", "CSS3"],
                "capabilities": [
                    {"name": "Codebase AST Analysis", "evidence": ["Analyzer in /platform_core/github/analyzer.py"]},
                    {"name": "AI Multi-Agent Matching Engine", "evidence": ["Orchestrator in /platform_core/agents/orchestrator.py"]},
                    {"name": "REST API Service Layer", "evidence": ["FastAPI in /app.py"]},
                    {"name": "Relational Data Persistence", "evidence": ["SQLAlchemy models in /platform_core/database/models.py"]}
                ]
            }
        },
        {
            "name": "ChainMind (Supply Chain & Logistics)",
            "summary": "Adaptive Supply Chain & Logistics Engine with Demand Forecasting and Vehicle Route Optimization",
            "type": "Data Analytics & ML Pipeline",
            "domains": ["Transportation & Logistics", "Smart Automation"],
            "signals": ["forecasting", "routing", "logistics", "database", "api"],
            "features": [
                "Time-series demand forecasting with automated ARIMA / Prophet models",
                "Multi-depot vehicle routing problem (VRP) optimization engine",
                "Warehouse inventory rebalancing and safety stock calculation",
                "FastAPI REST endpoints for consignment tracking and dispatch"
            ],
            "manifest": {
                "tech_stack": ["Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "Prophet", "NumPy", "Pandas"],
                "capabilities": [
                    {"name": "Time-Series Demand Forecasting", "evidence": ["ProphetModel in /models/forecast.py"]},
                    {"name": "Vehicle Routing & Fleet Dispatch", "evidence": ["VRPDispatcher in /routing/engine.py"]},
                    {"name": "REST API Service Layer", "evidence": ["FastAPI app in /main.py"]},
                    {"name": "Relational Data Persistence", "evidence": ["SQLAlchemy models"]}
                ]
            }
        },
        {
            "name": "GrowthOS (Self-Growth & Education Platform)",
            "summary": "AI-Powered Self-Growth and Career Coaching Platform with Habit Tracking, Skill Gap Analysis, and Interactive Learning Roadmaps",
            "type": "Web Application & Educational Platform",
            "domains": ["Smart Education", "Smart Automation"],
            "signals": ["education", "learning", "skill", "habits", "api", "database"],
            "features": [
                "Personalized learning curriculum and career roadmap generation",
                "Skill competency gap assessment and quiz generation",
                "Daily habit tracking and behavioral feedback loops",
                "RESTful backend services and progress visualization dashboard"
            ],
            "manifest": {
                "tech_stack": ["TypeScript", "Next.js", "Python", "FastAPI", "PostgreSQL", "TailwindCSS"],
                "capabilities": [
                    {"name": "Adaptive Learning Roadmaps", "evidence": ["RoadmapGenerator in /services/curriculum.py"]},
                    {"name": "Skill Gap Assessment Engine", "evidence": ["SkillAnalyzer in /services/competency.py"]},
                    {"name": "Habit Tracking & Daily Analytics", "evidence": ["HabitTracker in /services/tracker.py"]},
                    {"name": "REST API Service Layer", "evidence": ["FastAPI app in /main.py"]}
                ]
            }
        },
        {
            "name": "NeuroDetect (Biomedical EEG Platform)",
            "summary": "AI-Powered EEG Brainwave Analysis for Early Alzheimer Detection and Cognitive Health Monitoring",
            "type": "Biomedical Signal Processing & Deep Learning Platform",
            "domains": ["MedTech / BioTech / HealthTech"],
            "signals": ["healthcare", "biomedical", "medtech / biotech / healthtech", "api"],
            "features": [
                "Multi-channel EEG signal preprocessing and bandpass filtering",
                "Wavelet transform and spectral power density feature extraction",
                "XGBoost and 1D-CNN neural network classification for neurodegenerative biomarker detection",
                "Clinical reporting dashboard with patient cognitive impairment severity scores"
            ],
            "manifest": {
                "tech_stack": ["Python", "PyTorch", "MNE-Python", "scikit-learn", "FastAPI"],
                "capabilities": [
                    {"name": "Biomedical Signal Processing", "evidence": ["EEGFilter in /preprocessing/filter.py"]},
                    {"name": "Neural Network Diagnostic Classifier", "evidence": ["CNN1D in /models/network.py"]},
                    {"name": "REST API Service Layer", "evidence": ["FastAPI app in /api/server.py"]}
                ]
            }
        }
    ]

    print("=" * 85)
    print("FOUR-REPOSITORY SANITY SWEEP: TOP-6 AIM/INTENT QUALITY AUDIT")
    print("=" * 85)

    any_low_aim_leak = False

    for repo in repos:
        repo_name = repo["name"]
        print(f"\n[AUDITING REPO]: {repo_name}")
        print(f"  Stated Goal: {repo['summary']}")
        print(f"  Target Domains: {', '.join(repo['domains'])}")
        
        analysis_data = {
            "repo_name": repo_name,
            "project_summary": repo["summary"],
            "description": repo["summary"],
            "project_type": repo["type"],
            "detected_languages": ["Python"],
            "target_domains": repo["domains"],
            "domain_signals": repo["signals"],
            "core_features": repo["features"],
            "capability_manifest": repo["manifest"]
        }
        
        res = matcher.run({
            "db": db,
            "analysis_data": analysis_data,
            "repo_info": {"repo_name": repo_name, "description": repo["summary"]}
        })
        
        top_matches = res["top_matches"]
        print(f"  Qualified Top Matches: {len(top_matches)} | Vetoed Candidates: {len(res['vetoed_matches'])}")
        print(f"  {'Rank':<5} | {'PS ID':<10} | {'Aim':<7} | {'Tech':<7} | {'Sem':<7} | {'Dom':<7} | {'Overall':<8} | {'Title'}")
        print(f"  {'-'*5}-|-{'-'*10}-|-{'-'*7}-|-{'-'*7}-|-{'-'*7}-|-{'-'*7}-|-{'-'*8}-|-{'-'*35}")
        
        for i, m in enumerate(top_matches[:6], 1):
            aim = m["aim_alignment_score"]
            flag = " [LEAK! AIM < 55%]" if aim < 55.0 else ""
            if aim < 55.0:
                any_low_aim_leak = True
            print(f"  #{i:<4} | {m['problem_statement_id']:<10} | {aim:>5.1f}% | {m['tech_capability_score']:>5.1f}% | {m['semantic_similarity']:>5.1f}% | {m['domain_alignment']:>5.1f}% | {m['overall_match_score']:>6.1f}% | {m['title'][:40]}{flag}")

    print("\n" + "=" * 85)
    if any_low_aim_leak:
        print("AUDIT RESULT: FAIL - At least one candidate with Aim < 55% surfaced in Top-6 rankings.")
    else:
        print("AUDIT RESULT: PASS - ZERO candidates with Aim < 55% surfaced across all 4 benchmark repos.")
    print("=" * 85)

    db.close()

if __name__ == "__main__":
    run_sanity_sweep()
