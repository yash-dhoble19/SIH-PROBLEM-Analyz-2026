"""
Security and URL validation filters for GitHub repository ingestion.
"""

import re
from urllib.parse import urlparse
from typing import Tuple, Optional


class GitHubSecurityValidator:
    """Validates GitHub URLs and sanitizes repository content to prevent SSRF and secret leakage."""

    GITHUB_URL_REGEX = re.compile(
        r"^https?://(?:www\.)?github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+?)(?:\.git|/)?$"
    )

    SECRET_PATTERNS = [
        re.compile(r'(?i)(?:api_key|apikey|secret|password|token|auth_token|bearer)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{12,})["\']?'),
        re.compile(r'(?i)(?:postgres|postgresql|mysql|mongodb|redis)://[^\s"\']+'),
        re.compile(r'ghp_[a-zA-Z0-9]{36}'),
        re.compile(r'sk-[a-zA-Z0-9]{32,}'),
        re.compile(r'AIza[0-9A-Za-z-_]{35}'),
    ]

    @classmethod
    def parse_and_validate_url(cls, url: str) -> Tuple[bool, Optional[str], Optional[str], str]:
        """
        Validates whether the provided URL is a valid public GitHub repository URL.
        Returns: (is_valid, owner, repo_name, normalized_url_or_error)
        """
        if not url or not isinstance(url, str):
            return False, None, None, "Repository URL cannot be empty."

        url = url.strip()
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return False, None, None, "Invalid URL scheme. Must use http or https."

        if parsed.netloc.lower() not in ("github.com", "www.github.com"):
            return False, None, None, "Only public github.com repositories are supported."

        match = cls.GITHUB_URL_REGEX.match(url)
        if not match:
            return False, None, None, "Invalid GitHub repository URL format. Expected: https://github.com/owner/repo"

        owner, repo = match.groups()
        repo = repo.rstrip("/")
        if repo.endswith(".git"):
            repo = repo[:-4]

        # Prevent directory traversal
        if ".." in owner or ".." in repo:
            return False, None, None, "Invalid characters in repository name."

        normalized = f"https://github.com/{owner}/{repo}"
        return True, owner, repo, normalized

    @classmethod
    def sanitize_content(cls, content: str) -> str:
        """Masks detected secrets, credentials, and API tokens in text before LLM forwarding."""
        if not content:
            return ""

        sanitized = content
        for pattern in cls.SECRET_PATTERNS:
            sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)

        return sanitized
