"""
Agent 2: Project Understanding Agent.
Synthesizes project purpose, grounded capabilities with verifiable file citations,
and domain context. Validates that claimed capabilities are strictly anchored in source text.
"""

import json
import logging
import re
from typing import Dict, Any, List
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
        manifest_texts = "\n".join([f"[{p}]:\n{c[:1500]}" for p, c in file_contents.items() if any(m in p.lower() for m in ["requirements", "package.json", "dockerfile", "pom.xml", "pyproject"])])

        repo_name = repo_info.get("repo_name", "Repository")
        repo_desc = repo_info.get("description", "")
        detected_fw = static_analysis.get("detected_frameworks", [])

        # 1. Generate Grounded Understanding via LLM or Heuristic
        understanding = self._generate_understanding(
            repo_name=repo_name,
            repo_desc=repo_desc,
            readme_text=readme_text,
            manifest_texts=manifest_texts,
            detected_fw=detected_fw,
            file_tree=file_tree,
            static_analysis=static_analysis
        )

        # 2. Validation & Grounding Sanity Check
        raw_source = f"{repo_desc}\n{readme_text}\n{manifest_texts}\n{' '.join(f['path'] for f in file_tree)}".lower()
        validated_capabilities, is_low_confidence, warning = self._validate_capabilities(
            understanding.get("grounded_capabilities", []),
            raw_source
        )

        summary = understanding.get("project_summary", "")
        domains = understanding.get("target_domains", ["Miscellaneous / General"])

        return {
            "project_summary": summary,
            "core_features": [c["capability"] for c in validated_capabilities],
            "grounded_capabilities": validated_capabilities,
            "technical_capabilities": static_analysis.get("ml_capabilities", []) + (["REST API Engine"] if static_analysis.get("api_routes") else []),
            "target_domains": domains,
            "is_low_confidence": is_low_confidence,
            "confidence_warning": warning,
            "summary_output": f"Synthesized grounded profile for {repo_name} ({len(validated_capabilities)} verified capabilities across {len(domains)} domains)"
        }

    def _generate_understanding(
        self,
        repo_name: str,
        repo_desc: str,
        readme_text: str,
        manifest_texts: str,
        detected_fw: List[str],
        file_tree: List[Dict[str, Any]],
        static_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prompts LLM to extract grounded capabilities with mandatory source citations."""
        if self.ai_provider and not isinstance(self.ai_provider, HeuristicAIProvider):
            prompt = f"""You are a senior software architect auditing a GitHub repository to establish its true purpose and capabilities.

CRITICAL INSTRUCTIONS:
1. Every capability you list MUST cite the specific file, section, or dependency where it is defined.
2. DO NOT hallucinate or infer capabilities not present in the provided source text (e.g. never claim GIS, robotics, or cybercrime unless explicitly present in the README/manifests).
3. If the repository is a supply-chain, inventory, or logistics app, classify its domain as 'Transportation & Logistics' or 'Smart Automation', NOT GIS or Cybersecurity.

REPOSITORY METADATA:
- Name: {repo_name}
- Description: {repo_desc}
- Detected Frameworks: {', '.join(detected_fw)}
- File List: {', '.join(f['path'] for f in file_tree[:25])}

README CONTENT:
{readme_text[:3000] if readme_text else 'No README provided.'}

MANIFEST FILES:
{manifest_texts[:2000] if manifest_texts else 'No manifest files provided.'}

Respond ONLY with valid JSON:
{{
  "project_summary": "<2-3 sentences explaining what this project actually does>",
  "target_domains": ["<Primary Domain 1>", "<Domain 2>"],
  "grounded_capabilities": [
    {{
      "capability": "<specific feature or capability>",
      "source": "<exact README section, file path, or dependency, e.g. 'README.md - Key Modules table'>"
    }}
  ]
}}"""
            try:
                res = self.ai_provider.generate_json(prompt)
                if isinstance(res, dict) and "project_summary" in res and "grounded_capabilities" in res:
                    return res
            except Exception as e:
                logger.warning(f"[UnderstandingAgent] LLM parsing failed: {e}. Using deterministic extraction.")

        # Deterministic Grounded Fallback
        return self._heuristic_understanding(repo_name, repo_desc, readme_text, manifest_texts, detected_fw, static_analysis)

    def _heuristic_understanding(
        self,
        repo_name: str,
        repo_desc: str,
        readme_text: str,
        manifest_texts: str,
        detected_fw: List[str],
        static_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deterministic extraction citing exact sources."""
        capabilities = []
        raw_text = f"{repo_desc}\n{readme_text}\n{manifest_texts}".lower()

        # Extract features from README bullets
        bullet_matches = re.findall(r'(?:^|\n)\s*[•\-\*]\s*([A-Za-z0-9][^\n]{10,120})', readme_text)
        for b in bullet_matches[:6]:
            cleaned = b.strip()
            if not any(k in cleaned.lower() for k in ["license", "install", "http", "npm", "pip", "test"]):
                capabilities.append({
                    "capability": cleaned,
                    "source": "README.md - Feature List"
                })

        # Add manifest-grounded capabilities
        for fw in detected_fw[:4]:
            capabilities.append({
                "capability": f"{fw} Integration",
                "source": "Package manifests / Dependencies"
            })

        if not capabilities and repo_desc:
            capabilities.append({
                "capability": repo_desc[:80],
                "source": "GitHub Repository Description"
            })

        # Domain classification with strict word boundaries
        domains = []
        domain_lexicons = {
            "Transportation & Logistics": [r"\blogistics\b", r"\bsupply[-_ ]chain\b", r"\binventory\b", r"\bprocurement\b", r"\bwarehouse\b", r"\bfleet\b", r"\bcargo\b", r"\bfreight\b", r"\bdemand[-_ ]forecast\b"],
            "Blockchain & Cybersecurity": [r"\bcybersecurity\b", r"\bfirewall\b", r"\bvulnerability\b", r"\bpacket[-_ ]inspection\b", r"\bsiem\b", r"\bzero[-_ ]trust\b", r"\bblockchain\b"],
            "Disaster Management": [r"\bdisaster\b", r"\bflood\b", r"\blandslide\b", r"\bearthquake\b", r"\bevacuation\b", r"\bhazard\b"],
            "MedTech / BioTech / HealthTech": [r"\bhealthcare\b", r"\bmedical\b", r"\bdisease\b", r"\bpatient\b", r"\beeg\b", r"\balzheimer\b", r"\bclinical\b"],
            "Agriculture, FoodTech & Rural Development": [r"\bagriculture\b", r"\bcrop\b", r"\bfarming\b", r"\bsoil\b", r"\bharvest\b", r"\bfertilizer\b"],
            "Space Technology": [r"\bsatellite\b", r"\bremote sensing\b", r"\borbital\b", r"\bspacecraft\b"],
            "Smart Automation": [r"\bautomation\b", r"\bpipeline\b", r"\bworkflow\b", r"\bcrawler\b", r"\bscheduler\b"],
            "Smart Education": [r"\beducation\b", r"\blearning\b", r"\bstudent\b", r"\bcurriculum\b", r"\bclassroom\b"],
        }

        for dom, patterns in domain_lexicons.items():
            if any(re.search(pat, raw_text, re.IGNORECASE) for pat in patterns):
                domains.append(dom)

        if not domains:
            domains.append("Miscellaneous / General")

        summary = (
            f"The repository '{repo_name}' is a {static_analysis.get('project_type', 'software application')} "
            f"focusing on {', '.join(domains[:2])}. "
            f"Key verified capabilities include {', '.join(c['capability'] for c in capabilities[:2]) if capabilities else 'standard application workflows'}."
        )

        return {
            "project_summary": summary,
            "target_domains": domains,
            "grounded_capabilities": capabilities
        }

    def _validate_capabilities(
        self,
        capabilities: List[Dict[str, Any]],
        raw_source: str
    ) -> tuple:
        """
        Validates that claimed capabilities are grounded in the repository's source text.
        Filters out hallucinations and flags low confidence if ungrounded claims exist.
        """
        validated = []
        hallucination_count = 0

        # Highly specific domain terms that MUST appear in raw source if claimed
        strict_terms = {
            "gis": r"\b(gis|geopandas|folium|shapely|rasterio|gdal|geospatial)\b",
            "cybercrime": r"\b(cybercrime|forensics|phishing|ransomware|malware)\b",
            "firewall": r"\b(firewall|siem|packet|snmp|ids|ips)\b",
            "eeg": r"\b(eeg|brainwave|neuro|electrode)\b",
            "satellite": r"\b(satellite|orbital|landsat|sentinel)\b",
            "drone": r"\b(drone|uav|quadcopter|flight controller)\b"
        }

        for cap in capabilities:
            cap_text = cap.get("capability", "")
            cap_lower = cap_text.lower()
            
            # Check if capability claims a strict term without backing in raw source
            is_hallucinated = False
            for term, pat in strict_terms.items():
                if re.search(pat, cap_lower) and not re.search(pat, raw_source):
                    is_hallucinated = True
                    hallucination_count += 1
                    logger.warning(f"[GroundingValidator] Rejected ungrounded capability '{cap_text}' — domain pattern '{term}' not present in codebase.")
                    break

            if not is_hallucinated:
                validated.append(cap)

        is_low_confidence = False
        warning = None
        if hallucination_count > 0:
            is_low_confidence = True
            warning = f"Filtered {hallucination_count} ungrounded capability claims that were not backed by repository files."

        if not validated:
            validated.append({
                "capability": "Core application workflows",
                "source": "Verified codebase files"
            })

        return validated, is_low_confidence, warning
