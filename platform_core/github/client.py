"""
GitHub REST Client for repository metadata, tree indexing, and selective content extraction.
"""

import logging
import base64
import httpx
from typing import Dict, Any, List, Optional
from platform_core.config import settings
from platform_core.github.security import GitHubSecurityValidator

logger = logging.getLogger("sih_platform.github")


class GitHubClient:
    """Client for securely reading public GitHub repositories."""

    IGNORED_DIRS = {
        ".git", "node_modules", "venv", ".venv", "env", "__pycache__",
        "dist", "build", ".next", ".nuxt", "coverage", ".idea", ".vscode",
        "target", "vendor", "bin", "obj", "tests", "test", "migrations",
        "fixture", "fixtures", "__snapshots__"
    }

    IGNORED_EXTS = {
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".mp4",
        ".mp3", ".wav", ".zip", ".tar", ".gz", ".7z", ".pdf", ".exe",
        ".dll", ".so", ".dylib", ".class", ".pyc", ".bin", ".iso", ".lock",
        ".min.js", ".min.css", ".map"
    }

    PRIORITY_FILENAMES = {
        "readme.md", "readme", "package.json", "requirements.txt",
        "pyproject.toml", "pom.xml", "build.gradle", "dockerfile",
        "docker-compose.yml", "docker-compose.yaml", "main.py", "app.py",
        "server.js", "index.js", "app.js", "schema.prisma", "models.py"
    }

    SOURCE_DIR_PREFIXES = (
        "api/", "routes/", "services/", "agents/", "core/", "src/",
        "app/", "models/", "schemas/", "controllers/", "pipeline/", "lib/"
    )

    SOURCE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rs", ".cpp", ".sql"}

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.GITHUB_TOKEN
        self.headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "SIH-Intelligence-Platform/1.0",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def fetch_repository_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch general repository metadata."""
        url = f"https://api.github.com/repos/{owner}/{repo}"
        with httpx.Client(timeout=15.0, headers=self.headers) as client:
            resp = client.get(url)
            if resp.status_code == 404:
                raise ValueError(f"GitHub repository '{owner}/{repo}' not found or is private.")
            if resp.status_code == 403:
                raise ValueError("GitHub API rate limit exceeded or access forbidden.")
            resp.raise_for_status()
            data = resp.json()
            return {
                "owner": owner,
                "repo_name": repo,
                "default_branch": data.get("default_branch", "main"),
                "description": data.get("description") or "",
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "open_issues": data.get("open_issues_count", 0),
                "primary_language": data.get("language") or "Unknown",
                "visibility": "public" if not data.get("private") else "private",
            }

    def fetch_file_tree(self, owner: str, repo: str, branch: str = "main") -> List[Dict[str, Any]]:
        """Fetch repository file tree recursively (up to 1,000 files) prioritizing key source code."""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        with httpx.Client(timeout=20.0, headers=self.headers) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                # Fallback to fetching root contents
                return self._fetch_contents_fallback(client, owner, repo, "")
            
            data = resp.json()
            raw_tree = data.get("tree", [])
            filtered_files = []

            for item in raw_tree:
                if item.get("type") != "blob":
                    continue
                path = item.get("path", "")
                parts = path.split("/")

                # Skip ignored directories anywhere in path
                if any(p.lower() in self.IGNORED_DIRS for p in parts[:-1]):
                    continue

                filename = parts[-1].lower()
                ext = "." + filename.split(".")[-1] if "." in filename else ""

                if ext in self.IGNORED_EXTS:
                    continue

                size = item.get("size", 0)

                # Identify if this is a priority source file for deep content extraction
                is_manifest_or_doc = filename in self.PRIORITY_FILENAMES
                is_source_dir = any(path.lower().startswith(prefix) for prefix in self.SOURCE_DIR_PREFIXES) and ext in self.SOURCE_EXTENSIONS
                is_top_level_source = len(parts) == 1 and ext in self.SOURCE_EXTENSIONS
                is_shallow_source = len(parts) <= 3 and ext in self.SOURCE_EXTENSIONS and not any(p.lower() in self.IGNORED_DIRS for p in parts)

                is_priority = is_manifest_or_doc or is_source_dir or is_top_level_source or is_shallow_source

                filtered_files.append({
                    "path": path,
                    "size": size,
                    "sha": item.get("sha"),
                    "is_priority": is_priority,
                    "extension": ext
                })

            return filtered_files

    def fetch_file_content(self, owner: str, repo: str, path: str, branch: str = "main") -> Optional[str]:
        """Fetch and decode textual content of a single file."""
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        try:
            with httpx.Client(timeout=10.0, headers=self.headers) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    sanitized = GitHubSecurityValidator.sanitize_content(resp.text)
                    # Limit length to 25KB per file
                    return sanitized[:25000]
        except Exception as e:
            logger.warning(f"Failed to fetch content for {path}: {e}")
        return None

    def _fetch_contents_fallback(self, client: httpx.Client, owner: str, repo: str, path: str) -> List[Dict[str, Any]]:
        """Fallback to /contents API."""
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        try:
            resp = client.get(url)
            if resp.status_code == 200:
                items = resp.json()
                results = []
                for it in items:
                    if it.get("type") == "file":
                        results.append({
                            "path": it.get("path"),
                            "size": it.get("size", 0),
                            "sha": it.get("sha"),
                            "is_priority": True,
                            "extension": "." + it.get("name").split(".")[-1] if "." in it.get("name") else ""
                        })
                return results
        except Exception:
            pass
        return []
