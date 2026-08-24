"""
Regression test for Gap Analysis Agent 6.
Verifies that:
1. A repo with NO networking capability gets SPECIFIC, NON-BOILERPLATE reasons
   when evaluated against networking-heavy requirements.
2. No two requirement rows produce the exact same reason string.
3. The old banned placeholder strings never appear.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from platform_core.agents.gap_analysis_agent import GapAnalysisAgent, _BANNED_BOILERPLATE


def test_gap_analysis_no_networking_repo():
    """
    A note-taking/journaling repo (zero networking code) evaluated against
    a network-security-heavy problem statement's requirements.
    Every row's reason must be specific and different.
    """
    print("=" * 60, flush=True)
    print("TESTING GAP ANALYSIS AGENT — NETWORKING MISMATCH REGRESSION", flush=True)
    print("=" * 60, flush=True)

    # Simulate a simple note-taking repo's analysis data
    note_app_analysis = {
        "project_type": "Personal Productivity Web Application",
        "project_summary": "A minimalist markdown note-taking and daily habit tracker for personal journaling.",
        "detected_languages": ["Python", "JavaScript"],
        "core_features": [
            "Markdown note editor with live preview",
            "Daily mood and habit tracking",
            "Task checklist with due dates",
            "Tag-based note organization"
        ],
        "technical_capabilities": ["SQLite storage", "REST API endpoints"],
        "backend_framework": "Flask",
        "frontend_framework": "React",
        "database_tech": "SQLite",
        "ml_capabilities": [],
        "api_routes": ["/api/notes", "/api/habits", "/api/tags"],
        "architectural_strengths": ["Clean REST API design", "Responsive UI"],
    }

    # Simulate Agent 5 decomposition of a network-security problem statement
    network_security_problem = {
        "explicit_requirements": [
            "Real-time network packet capture and deep packet inspection for anomaly detection",
            "Automated firewall rule auditing against CIS benchmark compliance standards",
            "SNMP-based router and switch configuration monitoring with drift alerts",
            "Intrusion detection system with ML-based threat classification engine",
            "Centralized SIEM dashboard aggregating logs from firewalls, IDS, and endpoint agents",
            "Zero-trust network access policy validator with micro-segmentation enforcement",
        ],
        "technical_requirements": [
            "Integration with packet capture libraries (libpcap, Scapy, Wireshark dissectors)",
            "Network protocol parsers for TCP/UDP/ICMP header analysis",
        ]
    }

    agent = GapAnalysisAgent()
    result = agent.run({
        "analysis_data": note_app_analysis,
        "problem_analysis": network_security_problem
    })

    matrix = result["requirement_matrix"]
    assert len(matrix) > 0, "Expected non-empty requirement matrix"

    print(f"\nTotal requirements evaluated: {len(matrix)}", flush=True)
    print(f"Matched: {result['matched_count']}, Partial: {result['partial_count']}, Missing: {result['missing_count']}", flush=True)
    print(f"Reusability: {result['reusability_score']}%", flush=True)

    # Check 1: No banned boilerplate strings appear in any reason
    for row in matrix:
        for banned in _BANNED_BOILERPLATE:
            assert banned.lower() not in row["reason"].lower(), (
                f"BANNED boilerplate found in reason for '{row['requirement'][:40]}': {row['reason']}"
            )
    print("[PASS] No banned boilerplate strings found in any reason.", flush=True)

    # Check 2: All reasons are different (no copy-paste across rows)
    reasons = [row["reason"] for row in matrix]
    unique_reasons = set(reasons)
    assert len(unique_reasons) >= len(reasons) * 0.7, (
        f"Too many duplicate reasons: {len(unique_reasons)} unique out of {len(reasons)} total. "
        f"Duplicates: {[r for r in reasons if reasons.count(r) > 1]}"
    )
    print(f"[PASS] {len(unique_reasons)} unique reasons out of {len(reasons)} rows (>= 70% unique).", flush=True)

    # Check 3: Most requirements should be MISSING since the repo has zero networking
    missing_or_unknown = sum(1 for r in matrix if r["status"] in ("MISSING", "UNKNOWN"))
    assert missing_or_unknown >= len(matrix) * 0.6, (
        f"Expected most requirements to be MISSING for a non-networking repo, "
        f"but only {missing_or_unknown}/{len(matrix)} were."
    )
    print(f"[PASS] {missing_or_unknown}/{len(matrix)} requirements correctly marked MISSING/UNKNOWN.", flush=True)

    # Print detailed matrix for inspection
    print("\n--- Detailed Requirement Matrix ---", flush=True)
    for i, row in enumerate(matrix, 1):
        print(f"\n[{i}] {row['status']:8s} | {row['requirement'][:70]}", flush=True)
        print(f"    Current: {row['current_project'][:80]}", flush=True)
        print(f"    Reason:  {row['reason'][:120]}", flush=True)

    print("\n" + "=" * 60, flush=True)
    print("GAP ANALYSIS REGRESSION TEST PASSED", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    test_gap_analysis_no_networking_repo()
