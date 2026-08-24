"""
Agent 1: Repository Explorer.
Explores project structure, directory layout, language distributions, entrypoints,
and aggregates per-file static code findings.
"""

from typing import Dict, Any, List
from platform_core.agents.base import BaseAgent


class RepositoryExplorerAgent(BaseAgent):
    def __init__(self, ai_provider=None):
        super().__init__("Agent 1: Repository Explorer", ai_provider)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        repo_info = context.get("repo_info", {})
        static_analysis = context.get("static_analysis", {})
        file_tree = context.get("file_tree", [])
        file_findings = static_analysis.get("file_findings", [])
        endpoints = static_analysis.get("endpoints", [])
        data_models = static_analysis.get("data_models", [])

        # Structure analysis
        top_dirs = sorted(list({f["path"].split("/")[0] for f in file_tree if "/" in f["path"]}))
        
        # Summarize per-file code findings
        file_summary_list: List[Dict[str, Any]] = []
        for f in file_findings:
            file_summary_list.append({
                "path": f.get("path"),
                "language": f.get("language"),
                "functions_count": len(f.get("functions", [])),
                "classes_count": len(f.get("classes", [])),
                "routes_count": len(f.get("routes", [])),
                "models_count": len(f.get("models", [])),
                "imports": f.get("imports", [])[:8],
                "inferred_capabilities": [c.get("name") for c in f.get("inferred_capabilities", [])]
            })

        output = {
            "project_name": repo_info.get("repo_name", "Unknown"),
            "owner": repo_info.get("owner", "Unknown"),
            "primary_language": repo_info.get("primary_language", "Unknown"),
            "detected_languages": static_analysis.get("languages", []),
            "top_level_directories": top_dirs[:12],
            "total_indexed_files": len(file_tree),
            "project_type": static_analysis.get("project_type", "Software Application"),
            "file_findings": file_findings,
            "file_summaries": file_summary_list,
            "endpoints_count": len(endpoints),
            "data_models_count": len(data_models),
            "endpoints": endpoints[:20],
            "data_models": data_models[:15],
            "code_modules": [f.get("path") for f in file_findings if f.get("classes") or f.get("functions") or f.get("routes")],
            "summary_output": f"Explored {repo_info.get('repo_name')} - Analyzed {len(file_findings)} source files ({len(endpoints)} endpoints, {len(data_models)} data models)"
        }
        return output
