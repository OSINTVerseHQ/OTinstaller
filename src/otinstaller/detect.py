"""Target type detection for auto mode."""

from __future__ import annotations

import re

# Regex patterns for target type detection
URL_RE = re.compile(r"^https?://", re.IGNORECASE)

IPV4_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Domain: at least one dot, valid TLD-like ending, no spaces, no @
# Uses common TLD list similar to extract.py
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
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:" + COMMON_TLDS + r")$", re.IGNORECASE
)


def detect_target_type(target: str) -> str:
    """Detect the type of a target string.

    Detection order (first match wins):
    1. Starts with http:// or https:// -> "url"
    2. Matches IPv4 pattern -> "ip"
    3. Contains @ and looks like email -> "email"
    4. Looks like a domain -> "domain"
    5. Otherwise -> "username" (fallback, includes phone-like strings)

    Phone numbers are not auto-detected due to international format variation.
    They fall through to "username" as a documented limitation.
    """
    target = target.strip()

    # 1. URL
    if URL_RE.match(target):
        return "url"

    # 2. IPv4
    if IPV4_RE.match(target):
        return "ip"

    # 3. Email
    if EMAIL_RE.match(target):
        return "email"

    # 4. Domain
    if DOMAIN_RE.match(target):
        return "domain"

    # 5. Fallback to username
    return "username"
