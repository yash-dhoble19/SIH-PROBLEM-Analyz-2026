"""
Agent 1: Repository Explorer.
Explores project structure, directory layout, language distributions, and primary entrypoints.
"""

from typing import Dict, Any
from platform_core.agents.base import BaseAgent


class RepositoryExplorerAgent(BaseAgent):
    def __init__(self, ai_provider=None):
        super().__init__("Agent 1: Repository Explorer", ai_provider)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        repo_info = context.get("repo_info", {})
        static_analysis = context.get("static_analysis", {})
        file_tree = context.get("file_tree", [])

        # Structure analysis
        top_dirs = sorted(list({f["path"].split("/")[0] for f in file_tree if "/" in f["path"]}))
        
        output = {
            "project_name": repo_info.get("repo_name", "Unknown"),
            "owner": repo_info.get("owner", "Unknown"),
            "primary_language": repo_info.get("primary_language", "Unknown"),
            "detected_languages": static_analysis.get("languages", []),
            "top_level_directories": top_dirs[:12],
            "total_indexed_files": len(file_tree),
            "project_type": static_analysis.get("project_type", "Software Application"),
            "summary_output": f"Explored {repo_info.get('repo_name')} - Detected {static_analysis.get('project_type')}"
        }
        return output
