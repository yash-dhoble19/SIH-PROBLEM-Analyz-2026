"""
Utility functions for text cleaning, section extraction, and formatting.
"""

import re
import html as html_lib
import logging
from typing import Optional, Tuple, Any
from urllib.parse import urlparse
from bs4 import BeautifulSoup, Comment


def clean_html_to_markdown(html_content: str) -> str:
    """
    Clean raw HTML into structured Markdown text.
    Preserves:
    - Headings
    - Bullet points & numbered lists
    - Bold markers
    - Paragraph and line breaks
    Removes:
    - HTML tags, comments, script tags
    - Superfluous whitespaces and repeated linebreaks
    """
    if not html_content:
        return ""
        
    # Unescape HTML entities first
    text = html_lib.unescape(html_content)
    
    # Pre-process HTML entities like bullet &#8226;
    text = text.replace("&#8226;", "• ")
    text = text.replace("&bull;", "• ")
    text = text.replace("&nbsp;", " ")
    
    # Replace breaks and list elements
    text = re.sub(r'<\s*br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</\s*p\s*>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<\s*p[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<\s*li[^>]*>', '\n• ', text, flags=re.IGNORECASE)
    text = re.sub(r'</\s*li\s*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<\s*tr[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<\s*td[^>]*>', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'<\s*div[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</\s*div\s*>', '\n', text, flags=re.IGNORECASE)
    
    # Bold headers
    text = re.sub(r'<\s*b[^>]*>(.*?)</\s*b\s*>', r'**\1**', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<\s*strong[^>]*>(.*?)</\s*strong\s*>', r'**\1**', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Section headings (h1 - h6)
    text = re.sub(r'<\s*h[1-6][^>]*>(.*?)</\s*h[1-6]\s*>', r'\n\n### \1\n', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Strip any remaining HTML tags and comments
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Normalize inline spaces while preserving newlines
    lines = []
    for line in text.split('\n'):
        cleaned_line = re.sub(r'[\t ]+', ' ', line).strip()
        lines.append(cleaned_line)
        
    normalized = '\n'.join(lines)
    # Collapse 3 or more consecutive newlines into 2
    normalized = re.sub(r'\n{3,}', '\n\n', normalized)
    return normalized.strip()


def split_sections(text: str) -> Tuple[Optional[str], str, Optional[str]]:
    """
    Intelligently extracts:
    - background
    - description
    - expected_solution
    from unstructured or semi-structured problem statement text.
    Guarantees description is never empty if input text has content.
    """
    if not text:
        return None, "", None
        
    bg: Optional[str] = None
    desc: Optional[str] = None
    sol: Optional[str] = None
    
    # Regex patterns that match section headers
    # e.g., "**Background:**", "Background:", "• Background:", "1. Background", "### Background"
    bg_pattern = r'(?:^|\n)\s*(?:[*#•\-\s]*)(?:background|problem\s+background)\s*[:\-]?(.*?)(?=(?:^|\n)\s*(?:[*#•\-\s]*)(?:description|problem\s+description|problem\s+statement|expected\s+solution|solution|objective|key\s+deliverables)\s*[:\-]|\Z)'
    desc_pattern = r'(?:^|\n)\s*(?:[*#•\-\s]*)(?:description|problem\s+description|problem\s+statement|detailed\s+description)\s*[:\-]?(.*?)(?=(?:^|\n)\s*(?:[*#•\-\s]*)(?:expected\s+solution|solution|outcomes|deliverables|key\s+deliverables)\s*[:\-]|\Z)'
    sol_pattern = r'(?:^|\n)\s*(?:[*#•\-\s]*)(?:expected\s+solution|solution\s+approach|desired\s+outcome|expected\s+outcome|solution)\s*[:\-]?(.*)'
    
    bg_match = re.search(bg_pattern, text, re.IGNORECASE | re.DOTALL)
    desc_match = re.search(desc_pattern, text, re.IGNORECASE | re.DOTALL)
    sol_match = re.search(sol_pattern, text, re.IGNORECASE | re.DOTALL)
    
    def _clean_section_val(val: Optional[str]) -> Optional[str]:
        if not val:
            return None
        # Remove leading/trailing bold formatting artifact remnants like '**' or colons
        cleaned = re.sub(r'^\s*[*_~:\-]+\s*', '', val)
        cleaned = cleaned.strip()
        return cleaned if cleaned else None

    if bg_match:
        bg = _clean_section_val(bg_match.group(1))
        
    if desc_match:
        desc = _clean_section_val(desc_match.group(1))
        
    if sol_match:
        sol = _clean_section_val(sol_match.group(1))
        
    # If no explicit "Description:" header was found but background / solution exist
    if not desc:
        if bg or sol:
            # Whole text is preserved as description if specific subsection missing
            desc = text
        else:
            desc = text
            
    return bg, desc, sol


def extract_valid_url_or_text(soup_element: Any) -> Optional[str]:
    """
    Extracts a valid URL or clean text string from a BeautifulSoup cell/element.
    Returns None for empty placeholders, '#' links, or whitespace.
    """
    if not soup_element:
        return None
        
    # Look for <a> tags first
    a_tags = soup_element.find_all('a')
    for a in a_tags:
        href = a.get('href', '').strip()
        if href and href not in ('#', 'javascript:;', 'javascript:void(0);', 'about:blank'):
            parsed = urlparse(href)
            if parsed.scheme in ('http', 'https', 'mailto') or '@' in href:
                return href
            # Check text inside <a>
            a_text = a.get_text(strip=True)
            if a_text.startswith('http://') or a_text.startswith('https://') or '@' in a_text:
                return a_text

    # Check raw text in the element
    text = soup_element.get_text(separator=' ', strip=True)
    if not text:
        return None
        
    # Clean text
    text = text.replace('', '').strip()
    if not text or text.lower() in ('na', 'n/a', 'none', 'null', '-', '--'):
        return None
        
    # Check if text contains a URL
    url_match = re.search(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text)
    if url_match:
        found_url = url_match.group(0).rstrip('.,;)')
        if found_url.startswith('www.'):
            found_url = 'https://' + found_url
        return found_url
        
    # If email
    email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    if email_match:
        return email_match.group(0)
        
    return text


def setup_logger(name: str = "sih_scraper", level: int = logging.INFO) -> logging.Logger:
    """Configures and returns a structured logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
