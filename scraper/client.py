"""
HTTP client for fetching SIH problem statement web pages with retry and SSL handling.
"""

import time
import logging
from typing import Optional, Dict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# Suppress insecure request warnings if SSL verification fallback is used
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("sih_scraper.client")


class SIHWebClient:
    """
    Robust HTTP client tailored for SIH portal extraction.
    Features:
    - Connection pooling & session persistence
    - Automatic exponential backoff retries on transient errors (5xx, 429)
    - Configurable timeouts and custom browser User-Agent
    - SSL verification with automatic graceful fallback
    """

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        headers: Optional[Dict[str, str]] = None,
        verify_ssl: bool = True,
        rate_limit_delay: float = 0.5,
    ):
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        
        # Merge headers
        req_headers = dict(self.DEFAULT_HEADERS)
        if headers:
            req_headers.update(headers)
        self.session.headers.update(req_headers)
        
        # Configure retry strategy
        retries = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def fetch_html(self, url: str) -> str:
        """
        Fetch HTML content from the specified URL with retries and SSL fallback.
        """
        logger.info(f"Fetching URL: {url}")
        
        try:
            response = self.session.get(url, timeout=self.timeout, verify=self.verify_ssl)
            response.raise_for_status()
            # Respect rate limit
            time.sleep(self.rate_limit_delay)
            # Ensure correct encoding (detect utf-8 or response.apparent_encoding)
            response.encoding = response.encoding or "utf-8"
            return response.text
        except requests.exceptions.SSLError as ssl_err:
            logger.warning(f"SSL verification failed ({ssl_err}), retrying without SSL verification...")
            response = self.session.get(url, timeout=self.timeout, verify=False)
            response.raise_for_status()
            time.sleep(self.rate_limit_delay)
            response.encoding = response.encoding or "utf-8"
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise

    def close(self):
        """Close the underlying session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
