import sys
import numpy as np
from platform_core.database.connection import SessionLocal
from platform_core.agents.matching_agent import SIHMatchingAgent
from platform_core.ai.providers import HeuristicAIProvider
from platform_core.database.models import ProblemStatement

def run_audit():
    db = SessionLocal()
    matcher = SIHMatchingAgent(ai_provider=HeuristicAIProvider())
    
    # --------------------------------------------------------------------------
    # REPO 1: ChainMind
    # --------------------------------------------------------------------------
    chainmind_analysis = {
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

    # --------------------------------------------------------------------------
    # REPO 2: NeuroDetect
    # --------------------------------------------------------------------------
    neurodetect_analysis = {
        "repo_name": "NeuroDetect",
        "project_summary": "AI-Powered EEG Brainwave Analysis for Early Alzheimer's Detection and Cognitive Health Monitoring",
        "description": "AI-Powered EEG Brainwave Analysis for Early Alzheimer's Detection and Cognitive Health Monitoring",
        "project_type": "Biomedical Signal Processing & Deep Learning Platform",
        "detected_languages": ["Python"],
        "target_domains": ["MedTech / BioTech / HealthTech", "Smart Automation"],
        "domain_signals": ["healthcare", "biomedical", "medtech / biotech / healthtech", "api"],
        "core_features": [
            "Multi-channel EEG signal preprocessing and bandpass filtering (Delta, Theta, Alpha, Beta)",
            "Wavelet transform and spectral power density feature extraction",
            "XGBoost and 1D-CNN neural network classification for neurodegenerative biomarker detection",
            "Clinical reporting dashboard with patient cognitive impairment severity scores"
        ],
        "technical_capabilities": ["Biomedical Signal Processing", "EEG Feature Extraction", "Neuro Classifier", "REST API Service Layer"],
        "capability_manifest": {
            "tech_stack": ["Python", "PyTorch", "MNE-Python", "scikit-learn", "FastAPI", "XGBoost"],
            "capabilities": [
                {"name": "Biomedical Signal Processing", "evidence": ["EEGFilter in /preprocessing/filter.py", "bandpass()"]},
                {"name": "Spectral Feature Extraction", "evidence": ["WaveletExtractor in /features/extract.py"]},
                {"name": "Neural Network Diagnostic Classifier", "evidence": ["CNN1DClassifier in /models/network.py"]},
                {"name": "REST API Service Layer", "evidence": ["FastAPI app in /api/server.py", "POST /api/v1/diagnose"]}
            ],
            "endpoints": [
                {"method": "POST", "path": "/api/v1/diagnose/eeg"},
                {"method": "GET", "path": "/api/v1/patient/{id}/report"}
            ],
            "data_models": [
                {"model_name": "PatientRecord", "columns": ["id", "age", "eeg_recording_id", "severity_score"]},
                {"model_name": "DiagnosticSession", "columns": ["id", "timestamp", "predicted_class"]}
            ],
            "domain_signals": ["healthcare", "biomedical", "medtech / biotech / healthtech", "api"]
        }
    }

    repos = [("ChainMind", chainmind_analysis), ("NeuroDetect", neurodetect_analysis)]

    for repo_name, repo_data in repos:
        print(f"\n{'='*80}")
        print(f"RUNNING MATCHING AUDIT FOR: {repo_name}")
        print(f"{'='*80}")
        
        context = {
            "db": db,
            "analysis_data": repo_data,
            "repo_info": {"repo_name": repo_name, "description": repo_data["description"]}
        }
        
        result = matcher.run(context)
        
        # Collect candidates evaluated
        top_matches = result["top_matches"]
        
        # Let's inspect all scored candidates
        # Re-score all unioned candidates to get full distribution stats
        candidates = matcher._retrieve_candidates(
            db, result["repo_embedding"], repo_data, 
            {"repo_name": repo_name, "project_summary": repo_data["project_summary"], "target_domains": repo_data["target_domains"], "domain_signals": repo_data["domain_signals"], "capability_manifest": repo_data["capability_manifest"]},
            repo_data["capability_manifest"]
        )
        
        all_scored = []
        tech_scores = []
        semantic_scores = []
        aim_scores = []
        domain_scores = []
        overall_scores = []
        
        for ps in candidates:
            intent_res = matcher.assess_intent_alignment(
                {"repo_name": repo_name, "project_summary": repo_data["project_summary"], "target_domains": repo_data["target_domains"], "domain_signals": repo_data["domain_signals"]},
                ps
            )
            score_data = matcher._score_match(ps, repo_data, result["repo_embedding"], intent_res, repo_data["capability_manifest"], {"repo_name": repo_name})
            all_scored.append(score_data)
            tech_scores.append(score_data["tech_capability_score"])
            semantic_scores.append(score_data["semantic_similarity"])
            aim_scores.append(score_data["aim_alignment_score"])
            domain_scores.append(score_data["domain_alignment"])
            overall_scores.append(score_data["overall_match_score"])

        print(f"\n[STATISTICAL DISTRIBUTIONS ACROSS ALL {len(all_scored)} CANDIDATES]")
        print(f"  • Tech Capability Scores:   Min={np.min(tech_scores):.1f}% | Max={np.max(tech_scores):.1f}% | Mean={np.mean(tech_scores):.1f}% | StdDev={np.std(tech_scores):.2f}")
        print(f"  • Semantic Similarity:      Min={np.min(semantic_scores):.1f}% | Max={np.max(semantic_scores):.1f}% | Mean={np.mean(semantic_scores):.1f}% | StdDev={np.std(semantic_scores):.2f}")
        print(f"  • Aim/Intent Scores:        Min={np.min(aim_scores):.1f}% | Max={np.max(aim_scores):.1f}% | Mean={np.mean(aim_scores):.1f}% | StdDev={np.std(aim_scores):.2f}")
        print(f"  • Domain Alignment:         Min={np.min(domain_scores):.1f}% | Max={np.max(domain_scores):.1f}% | Mean={np.mean(domain_scores):.1f}% | StdDev={np.std(domain_scores):.2f}")
        print(f"  • Overall Match Scores:     Min={np.min(overall_scores):.1f}% | Max={np.max(overall_scores):.1f}% | Mean={np.mean(overall_scores):.1f}% | StdDev={np.std(overall_scores):.2f}")

        print(f"\n[RAW TECH CAPABILITY SCORES FOR 15 REPRESENTATIVE CANDIDATES ({repo_name})]")
        print(f"{'PS ID':<10} | {'Category':<10} | {'Tech Score':<11} | {'Aim Score':<10} | {'Overall':<8} | {'Title'}")
        print(f"{'-'*10}-|-{'-'*10}-|-{'-'*11}-|-{'-'*10}-|-{'-'*8}-|-{'-'*40}")
        for item in all_scored[:15]:
            print(f"{item['problem_statement_id']:<10} | {item['category']:<10} | {item['tech_capability_score']:>9.1f}% | {item['aim_alignment_score']:>8.1f}% | {item['overall_match_score']:>6.1f}% | {item['title'][:45]}")

        # Check guardrail triggering
        low_tech_items = [item for item in all_scored if item["tech_capability_score"] < 55.0]
        print(f"\n[GUARDRAIL CHECK] Candidates with tech_capability_score < 55%: {len(low_tech_items)} candidates.")
        for item in low_tech_items[:5]:
            print(f"  - {item['problem_statement_id']} ({item['category']}): Tech={item['tech_capability_score']:.1f}%, Aim={item['aim_alignment_score']:.1f}% -> '{item['title'][:55]}'")

        print(f"\n[TOP 5 RANKED MATCHES FOR {repo_name}]")
        for i, match in enumerate(top_matches[:5], 1):
            print(f"  #{i} {match['problem_statement_id']} ({match['overall_match_score']:.1f}%): Tech={match['tech_capability_score']:.1f}%, Aim={match['aim_alignment_score']:.1f}%, Sem={match['semantic_similarity']:.1f}%, Feat={match['feature_alignment']:.1f}%, Dom={match['domain_alignment']:.1f}% | {match['title'][:50]}")

    db.close()

if __name__ == "__main__":
    run_audit()
