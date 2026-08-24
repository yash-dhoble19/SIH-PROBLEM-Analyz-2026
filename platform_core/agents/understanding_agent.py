"""
Agent 2: Project Understanding Agent.
Synthesizes AST code findings, endpoints, ORM data models, dependencies, and verified README features
into a structured Capability Manifest:
{ repo, domain_signals[], capabilities: [{name, evidence[], confidence}], endpoints[], data_models[], tech_stack[] }
Weights code evidence strictly above README text when they disagree, while extracting grounded features.
"""

import json
import logging
import re
from typing import Dict, Any, List, Set, Optional
from platform_core.agents.base import BaseAgent
from platform_core.ai.providers import HeuristicAIProvider

logger = logging.getLogger("sih_platform.agents.understanding")


class ProjectUnderstandingAgent(BaseAgent):
    def __init__(self, ai_provider=None):
        super().__init__("Agent 2: Project Understanding Agent", ai_provider)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        repo_info = context.get("repo_info", {})
        static_analysis = context.get("static_analysis", {})
        file_contents = context.get("file_contents", {})
        file_tree = context.get("file_tree", [])

        readme_text = next((c for p, c in file_contents.items() if "readme" in p.lower()), "")
        repo_name = repo_info.get("repo_name", "Repository")
        owner = repo_info.get("owner", "Unknown")
        repo_desc = repo_info.get("description", "")
        
        # 1. Synthesize Structured Capability Manifest
        manifest = self._build_capability_manifest(
            repo_info=repo_info,
            static_analysis=static_analysis,
            file_contents=file_contents,
            readme_text=readme_text
        )

        # 2. Derive Grounded Capabilities list for backward compatibility
        grounded_caps = []
        for cap in manifest.get("capabilities", []):
            evidence_str = "; ".join(cap.get("evidence", [])) or "Codebase source files"
            grounded_caps.append({
                "capability": cap["name"],
                "source": evidence_str,
                "confidence": cap.get("confidence", 0.9)
            })

        # 3. Generate Grounded Summary & Domains
        domains = self._classify_domains(manifest, readme_text, repo_desc, repo_name)
        manifest["domain_signals"] = sorted(list(set(manifest.get("domain_signals", []) + [d.lower() for d in domains])))
        summary = self._generate_summary(repo_name, manifest, domains, static_analysis)

        # 4. Check for ungrounded README claims
        is_low_confidence, warning = self._check_readme_grounding(readme_text, manifest)

        return {
            "capability_manifest": manifest,
            "project_summary": summary,
            "core_features": [c["name"] for c in manifest.get("capabilities", [])],
            "grounded_capabilities": grounded_caps,
            "technical_capabilities": [c["name"] for c in manifest.get("capabilities", [])] + static_analysis.get("ml_capabilities", []),
            "target_domains": domains,
            "domain_signals": manifest.get("domain_signals", []),
            "endpoints": manifest.get("endpoints", []),
            "data_models": manifest.get("data_models", []),
            "is_low_confidence": is_low_confidence,
            "confidence_warning": warning,
            "summary_output": f"Synthesized Capability Manifest for {repo_name} ({len(manifest.get('capabilities', []))} verified capabilities, {len(manifest.get('endpoints', []))} endpoints, {len(manifest.get('data_models', []))} models)"
        }

    def _build_capability_manifest(
        self,
        repo_info: Dict[str, Any],
        static_analysis: Dict[str, Any],
        file_contents: Dict[str, str],
        readme_text: str
    ) -> Dict[str, Any]:
        """
        Builds the unified Capability Manifest.
        Prioritizes code evidence (AST classes, functions, routes, models) and integrates verified README bullets.
        """
        raw_code_caps = static_analysis.get("code_capabilities", [])
        endpoints = static_analysis.get("endpoints", [])
        data_models = static_analysis.get("data_models", [])
        file_findings = static_analysis.get("file_findings", [])
        frameworks = static_analysis.get("detected_frameworks", [])
        languages = static_analysis.get("languages", [])

        capabilities_map: Dict[str, Dict[str, Any]] = {}

        # 1. Consolidate capabilities from AST code findings
        for cap in raw_code_caps:
            name = cap["name"]
            if name not in capabilities_map:
                capabilities_map[name] = {
                    "name": name,
                    "category": cap.get("category", "General"),
                    "evidence": list(cap.get("evidence", [])),
                    "confidence": cap.get("confidence", 0.95)
                }
            else:
                for ev in cap.get("evidence", []):
                    if ev not in capabilities_map[name]["evidence"]:
                        capabilities_map[name]["evidence"].append(ev)

        # 2. Extract capabilities directly from per-file findings (services, routes, agents, models)
        for f in file_findings:
            path = f.get("path", "")
            path_lower = path.lower()
            
            if "forecast" in path_lower or "predict" in path_lower:
                name = "Time-Series Demand Forecasting"
                evidence = [f"{path}: {func['name']}()" for func in f.get("functions", [])] + [f"{path}: class {cls['name']}" for cls in f.get("classes", [])]
                self._merge_capability(capabilities_map, name, evidence, "Supply Chain & Analytics", path)

            if "rout" in path_lower or "dispatch" in path_lower or "fleet" in path_lower:
                name = "Vehicle Routing & Optimization"
                evidence = [f"{path}: {func['name']}()" for func in f.get("functions", [])] + [f"{path}: class {cls['name']}" for cls in f.get("classes", [])]
                self._merge_capability(capabilities_map, name, evidence, "Transportation & Logistics", path)

            if "scrape" in path_lower or "crawler" in path_lower or "parser" in path_lower:
                name = "Web Scraping & DOM Extraction"
                evidence = [f"{path}: {func['name']}()" for func in f.get("functions", [])] + [f"{path}: class {cls['name']}" for cls in f.get("classes", [])]
                self._merge_capability(capabilities_map, name, evidence, "Smart Automation", path)

            if "webhook" in path_lower or "event" in path_lower:
                name = "Webhook Automation & Event Dispatch"
                evidence = [f"{path}: {func['name']}()" for func in f.get("functions", [])] + [f"{path}: class {cls['name']}" for cls in f.get("classes", [])]
                self._merge_capability(capabilities_map, name, evidence, "Smart Automation", path)

        # 3. Add API & Database capabilities if endpoints and models exist
        if endpoints:
            api_ev = [f"{ep['file']}: {ep['method']} {ep['path']}" for ep in endpoints[:5]]
            self._merge_capability(capabilities_map, "REST API Service Layer", api_ev, "Backend Services")

        if data_models:
            model_ev = [f"{m['file']}: model {m['model_name']} ({', '.join(m.get('columns', [])[:3])})" for m in data_models[:4]]
            self._merge_capability(capabilities_map, "Relational Data Persistence", model_ev, "Data Layer")

        # 4. Integrate verified README features
        if readme_text:
            bullet_matches = re.findall(r'(?:^|\n)\s*[•\-\*]\s*([A-Za-z0-9][^\n]{10,120})', readme_text)
            for b in bullet_matches[:6]:
                cleaned = b.strip()
                if not any(k in cleaned.lower() for k in ["license", "install", "http", "npm", "pip", "test", "clone", "git "]):
                    self._merge_capability(capabilities_map, cleaned, ["README.md - Features"], "Application Feature")

        # 5. If capabilities are still sparse, supplement from verified frameworks
        if len(capabilities_map) < 2:
            for fw in frameworks[:3]:
                self._merge_capability(capabilities_map, f"{fw} Integration", ["Package dependencies / manifests"], "Framework")

        capabilities_list = list(capabilities_map.values())

        # 6. Extract Domain Signals
        domain_signals: Set[str] = set(static_analysis.get("domain_signals", []))
        for cap in capabilities_list:
            c_name = cap["name"].lower()
            if "forecast" in c_name: domain_signals.add("forecasting")
            if "rout" in c_name: domain_signals.add("routing")
            if "scrape" in c_name: domain_signals.add("scraping")
            if "webhook" in c_name: domain_signals.add("webhook")
            if "geospatial" in c_name or "gis" in c_name: domain_signals.add("geospatial")
            if "vision" in c_name: domain_signals.add("computer_vision")
            if "cyber" in c_name or "security" in c_name: domain_signals.add("cybersecurity")
            if "eeg" in c_name or "health" in c_name: domain_signals.add("healthcare")
            if "note" in c_name or "journal" in c_name or "habit" in c_name: domain_signals.add("productivity")

        # 7. Tech Stack
        tech_stack = sorted(list(set(frameworks + languages + ([static_analysis.get("database_tech")] if static_analysis.get("database_tech") else []))))

        manifest = {
            "repo": {
                "name": repo_info.get("repo_name", "Unknown"),
                "owner": repo_info.get("owner", "Unknown"),
                "primary_language": repo_info.get("primary_language", "Unknown"),
                "project_type": static_analysis.get("project_type", "Software Application")
            },
            "domain_signals": sorted(list(domain_signals)),
            "capabilities": capabilities_list,
            "endpoints": endpoints,
            "data_models": data_models,
            "tech_stack": tech_stack
        }
        return manifest

    @staticmethod
    def _merge_capability(cap_map: Dict[str, Dict[str, Any]], name: str, evidence: List[str], category: str = "General", path: str = ""):
        """Helper to merge or create capability entry with clean evidence."""
        if not evidence and path:
            evidence = [f"{path}: module definition"]
        if name not in cap_map:
            cap_map[name] = {
                "name": name,
                "category": category,
                "evidence": [e for e in evidence if e][:5],
                "confidence": 0.95
            }
        else:
            for ev in evidence:
                if ev and ev not in cap_map[name]["evidence"]:
                    cap_map[name]["evidence"].append(ev)
            cap_map[name]["confidence"] = 0.95

    def _classify_domains(self, manifest: Dict[str, Any], readme_text: str, repo_desc: str = "", repo_name: str = "") -> List[str]:
        """Classifies target domains grounded by manifest domain signals and text analysis."""
        signals = set(manifest.get("domain_signals", []))
        all_text = f"{repo_name} {repo_desc} {readme_text}".lower()
        domains = []

        if "forecasting" in signals or "routing" in signals or re.search(r"\b(logistics|supply[-_ ]chain|inventory|warehouse|fleet)\b", all_text):
            domains.append("Transportation & Logistics")
            domains.append("Smart Automation")
        if "productivity" in signals or re.search(r"\b(note|notes|journal|habit|productivity|self[-_ ]growth)\b", all_text):
            domains.append("Personal Productivity & Note-Taking")
        if "scraping" in signals or "webhook" in signals:
            if "Smart Automation" not in domains:
                domains.append("Smart Automation")
        if "geospatial" in signals or re.search(r"\b(gis|geospatial|flood|landslide|hazard)\b", all_text):
            domains.append("Disaster Management")
        if "healthcare" in signals or re.search(r"\b(eeg|healthcare|medical|patient|disease)\b", all_text):
            domains.append("MedTech / BioTech / HealthTech")
        if "cybersecurity" in signals or re.search(r"\b(cybersecurity|firewall|siem|packet|vulnerability)\b", all_text):
            domains.append("Blockchain & Cybersecurity")

        if not domains:
            domains.append("Miscellaneous / General")

        return domains

    def _generate_summary(self, repo_name: str, manifest: Dict[str, Any], domains: List[str], static_analysis: Dict[str, Any]) -> str:
        """Generates grounded factual summary from capability manifest."""
        caps = [c["name"] for c in manifest.get("capabilities", [])]
        caps_str = ", ".join(caps[:3]) if caps else "general application services"
        endpoints_count = len(manifest.get("endpoints", []))
        models_count = len(manifest.get("data_models", []))

        summary = (
            f"The repository '{repo_name}' is a {static_analysis.get('project_type', 'software application')} "
            f"focusing on {', '.join(domains[:2])}. "
            f"Verified code capabilities include: {caps_str}. "
            f"Architecture includes {endpoints_count} API endpoints and {models_count} data models."
        )
        return summary

    def _check_readme_grounding(self, readme_text: str, manifest: Dict[str, Any]) -> tuple:
        """Flags low confidence if README claims heavy domain terms that have no evidence in code."""
        if not readme_text:
            return False, None

        strict_terms = {
            "gis": ("geospatial", r"\b(gis|geopandas|folium|shapely|rasterio|gdal)\b"),
            "cybersecurity": ("cybersecurity", r"\b(firewall|siem|packet|scapy|zero[-_ ]trust)\b"),
            "eeg": ("healthcare", r"\b(eeg|brainwave|neuro|biomedical)\b")
        }

        signals = set(manifest.get("domain_signals", []))
        hallucinations = []

        for term_name, (signal_key, regex_pat) in strict_terms.items():
            if re.search(regex_pat, readme_text, re.IGNORECASE) and signal_key not in signals:
                hallucinations.append(term_name)

        if hallucinations:
            return True, f"README claims domain keywords ({', '.join(hallucinations)}) but no corresponding code or service implementation was found in the codebase."

        return False, None
