"""Indicator extraction from result files."""

from __future__ import annotations

import re
from pathlib import Path

# Regex patterns for indicator extraction
EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")

# Domain pattern: hostname-like, at least one dot, valid TLD-like ending
# Avoids matching IP-like dotted quads or random numbers
# TLD must be from known list; labels 1-63 chars, alphanumeric + hyphen
# Common TLDs list (covers most real-world cases)
COMMON_TLDS = (
    "com|org|net|edu|gov|mil|int|info|biz|name|pro|museum|coop|aero|"
    "io|ai|co|me|tv|cc|ws|xyz|online|site|tech|dev|app|blog|shop|"
    "uk|us|ca|de|fr|jp|cn|au|ru|br|in|nl|it|es|pl|se|no|fi|dk|cz|"
    "eu|asia|africa|lat|gay|lgbt|kim|wiki|news|media|digital|cloud|"
    "space|web|online|store|blog|news|mail|email|chat|social|video|"
    "photo|pics|pictures|gallery|graphics|design|art|studio|agency|"
    "group|company|enterprises|solutions|services|systems|network|"
    "technology|software|computer|engineering|consulting|management|"
    "marketing|advertising|media|entertainment|events|education|"
    "academy|university|college|school|institute|research|laboratory|"
    "health|medical|clinic|hospital|dental|vet|pharmacy|fitness|"
    "legal|law|attorney|lawyer|court|justice|tax|accounting|finance|"
    "bank|insurance|investment|capital|fund|trust|estate|property|"
    "realestate|construction|build|contractors|plumbing|electrician|"
    "cleaning|repair|maintenance|automotive|auto|car|bike|motorcycle|"
    "food|restaurant|cafe|bar|pub|hotel|travel|vacation|flights|"
    "cruise|tours|guide|tickets|events|theater|music|art|gallery|"
    "museum|library|archive|foundation|charity|nonprofit|ngo|community|"
    "support|help|care|service|services|solutions|expert|pro|guru|"
    "ninja|expert|specialist|consultant|advisor|counselor|therapist|"
    "doctor|physician|surgeon|dentist|vet|pharmacist|nurse|paramedic|"
    "engineer|architect|designer|developer|programmer|coder|hacker|"
    "admin|dev|ops|sysadmin|security|cyber|info|data|analytics|ai|ml|"
    "blockchain|crypto|bitcoin|ethereum|defi|nft|web3|metaverse|vr|ar"
)

DOMAIN_RE = re.compile(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:" + COMMON_TLDS + r")\b"
)

IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
)

URL_RE = re.compile(r"\bhttps?://[a-zA-Z0-9._~!$&'()*+,;=:@%/-]+\b")


def _deduplicate_preserve_order(items: list[str]) -> list[str]:
    """Deduplicate list while preserving first-seen order."""
    seen = set()
    result = []
    for item in items:
        lower = item.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(item)
    return result


def extract_indicators(text: str) -> dict[str, list[str]]:
    """Extract indicators from text.

    Returns dict with keys: emails, domains, ips, urls.
    Each list is deduplicated (preserving first-seen order).
    """
    emails = _deduplicate_preserve_order(EMAIL_RE.findall(text))
    domains = _deduplicate_preserve_order(DOMAIN_RE.findall(text))
    ips = _deduplicate_preserve_order(IPV4_RE.findall(text))
    urls = _deduplicate_preserve_order(URL_RE.findall(text))

    # Filter out domains that are actually IPv4 addresses
    domains = [d for d in domains if not IPV4_RE.fullmatch(d)]

    # Filter out domains that are actually emails (unlikely but safety)
    domains = [d for d in domains if "@" not in d]

    return {
        "emails": emails,
        "domains": domains,
        "ips": ips,
        "urls": urls,
    }


def extract_from_files(paths: list[Path]) -> dict[str, list[str]]:
    """Extract indicators from multiple files.

    Skips non-.txt files, skips unreadable files with a warning.
    Returns merged, deduplicated indicators.
    """
    all_emails: list[str] = []
    all_domains: list[str] = []
    all_ips: list[str] = []
    all_urls: list[str] = []

    for path in paths:
        if path.suffix != ".txt":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            # Skip unreadable files silently with warning
            continue

        result = extract_indicators(text)
        all_emails.extend(result["emails"])
        all_domains.extend(result["domains"])
        all_ips.extend(result["ips"])
        all_urls.extend(result["urls"])

    return {
        "emails": _deduplicate_preserve_order(all_emails),
        "domains": _deduplicate_preserve_order(all_domains),
        "ips": _deduplicate_preserve_order(all_ips),
        "urls": _deduplicate_preserve_order(all_urls),
    }
