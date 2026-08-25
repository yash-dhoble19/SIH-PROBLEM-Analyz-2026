from platform_core.database.connection import SessionLocal
from platform_core.agents.matching_agent import SIHMatchingAgent

db = SessionLocal()
# Initialize matcher with default live AI provider (Groq)
matcher = SIHMatchingAgent()

neurodetect_analysis = {
    "repo_name": "NeuroDetect",
    "project_summary": "AI-Powered EEG Brainwave Analysis for Early Alzheimer Detection and Cognitive Health Monitoring",
    "description": "AI-Powered EEG Brainwave Analysis for Early Alzheimer Detection",
    "project_type": "Biomedical Signal Processing & Deep Learning Platform",
    "detected_languages": ["Python"],
    "target_domains": ["MedTech / BioTech / HealthTech", "Smart Automation"],
    "domain_signals": ["healthcare", "biomedical", "medtech / biotech / healthtech", "api"],
    "core_features": [
        "Multi-channel EEG signal preprocessing and bandpass filtering",
        "Wavelet transform and spectral power density feature extraction",
        "XGBoost and 1D-CNN neural network classification for neurodegenerative biomarker detection"
    ],
    "capability_manifest": {
        "tech_stack": ["Python", "PyTorch", "MNE-Python", "scikit-learn", "FastAPI"],
        "capabilities": [
            {"name": "Biomedical Signal Processing", "evidence": ["EEGFilter in /preprocessing/filter.py"]},
            {"name": "Neural Network Diagnostic Classifier", "evidence": ["CNN1D in /models/network.py"]}
        ],
        "endpoints": [{"method": "POST", "path": "/api/v1/diagnose/eeg"}],
        "data_models": [{"model_name": "PatientRecord", "columns": ["id", "age"]}],
        "domain_signals": ["healthcare", "biomedical", "medtech / biotech / healthtech", "api"]
    }
}

res = matcher.run({
    "db": db,
    "analysis_data": neurodetect_analysis,
    "repo_info": {"repo_name": "NeuroDetect"}
})

print("=" * 80)
print("FRESH END-TO-END GROQ-POWERED ANALYSIS RESULTS FOR NeuroDetect")
print("=" * 80)
print(f"Provider in use: {type(matcher.ai_provider).__name__}")
print(f"Total candidates evaluated: {len(res['top_matches']) + len(res['vetoed_matches'])}")
print(f"Total matches qualified: {len(res['top_matches'])}")
print(f"Total matches vetoed: {len(res['vetoed_matches'])}")

print("\n--- TOP RANKED MATCHES ---")
for i, m in enumerate(res["top_matches"], 1):
    print(f"Rank #{i}: [{m['problem_statement_id']}] {m['title'][:65]} | Score: {m['overall_match_score']}% (Aim: {m['aim_alignment_score']}%, Tech: {m['tech_capability_score']}%, Dom: {m['domain_alignment']}%)")

print("\n--- STATUS OF SIH26179 (Retail Shopper Analytics) ---")
in_top_179 = [m for m in res["top_matches"] if m["problem_statement_id"] == "SIH26179"]
in_veto_179 = [v for v in res["vetoed_matches"] if v["problem_statement_id"] == "SIH26179"]
if in_top_179:
    print(f"STATUS: In Top Matches (Score: {in_top_179[0]['overall_match_score']}%)")
elif in_veto_179:
    print(f"STATUS: VETOED BY INTENT GUARD")
    print(f"  - Aim Score: {in_veto_179[0]['aim_alignment_score']}%")
    print(f"  - Reason: {in_veto_179[0]['reasoning']}")
else:
    print("STATUS: Filtered out during candidate retrieval.")

print("\n--- STATUS OF SIH26099 (Material Codes for CPSEs) ---")
in_top_099 = [m for m in res["top_matches"] if m["problem_statement_id"] == "SIH26099"]
in_veto_099 = [v for v in res["vetoed_matches"] if v["problem_statement_id"] == "SIH26099"]
if in_top_099:
    print(f"STATUS: In Top Matches (Score: {in_top_099[0]['overall_match_score']}%)")
elif in_veto_099:
    print(f"STATUS: VETOED BY INTENT GUARD")
    print(f"  - Aim Score: {in_veto_099[0]['aim_alignment_score']}%")
    print(f"  - Reason: {in_veto_099[0]['reasoning']}")
else:
    print("STATUS: Filtered out during candidate retrieval.")

db.close()
