"""Target type detection for auto mode."""

from __future__ import annotations

import re
from pathlib import Path

# Regex patterns for target type detection
URL_RE = re.compile(r"^https?://", re.IGNORECASE)

IPV4_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _load_tlds() -> set[str]:
    """Load official IANA TLD list from data file."""
    tld_file = Path(__file__).parent / "data" / "tlds.txt"
    if not tld_file.exists():
        # Fallback to common TLDs if data file missing
        return {
            "com",
            "org",
            "net",
            "edu",
            "gov",
            "mil",
            "int",
            "info",
            "biz",
            "name",
            "pro",
            "museum",
            "coop",
            "aero",
            "io",
            "ai",
            "co",
            "me",
            "tv",
            "cc",
            "ws",
            "xyz",
            "online",
            "site",
            "tech",
            "dev",
            "app",
            "blog",
            "shop",
            "uk",
            "us",
            "ca",
            "de",
            "fr",
            "jp",
            "cn",
            "au",
            "ru",
            "br",
            "in",
            "nl",
            "it",
            "es",
            "pl",
            "se",
            "no",
            "fi",
            "dk",
            "cz",
            "eu",
            "asia",
            "africa",
            "lat",
            "gay",
            "lgbt",
            "kim",
            "wiki",
            "news",
            "media",
            "digital",
            "cloud",
            "space",
            "web",
            "store",
            "mail",
            "email",
            "chat",
            "social",
            "video",
            "photo",
            "pics",
            "pictures",
            "gallery",
            "graphics",
            "design",
            "art",
            "studio",
            "agency",
            "group",
            "company",
            "enterprises",
            "solutions",
            "services",
            "systems",
            "network",
            "technology",
            "software",
            "computer",
            "engineering",
            "consulting",
            "management",
            "marketing",
            "advertising",
            "entertainment",
            "events",
            "education",
            "academy",
            "university",
            "college",
            "school",
            "institute",
            "research",
            "laboratory",
            "health",
            "medical",
            "clinic",
            "hospital",
            "dental",
            "vet",
            "pharmacy",
            "fitness",
            "legal",
            "law",
            "attorney",
            "lawyer",
            "court",
            "justice",
            "tax",
            "accounting",
            "finance",
            "bank",
            "insurance",
            "investment",
            "capital",
            "fund",
            "trust",
            "estate",
            "property",
            "realestate",
            "construction",
            "build",
            "contractors",
            "plumbing",
            "electrician",
            "cleaning",
            "repair",
            "maintenance",
            "automotive",
            "auto",
            "car",
            "bike",
            "motorcycle",
            "food",
            "restaurant",
            "cafe",
            "bar",
            "pub",
            "hotel",
            "travel",
            "vacation",
            "flights",
            "cruise",
            "tours",
            "guide",
            "tickets",
            "theater",
            "music",
            "library",
            "archive",
            "foundation",
            "charity",
            "nonprofit",
            "ngo",
            "community",
            "support",
            "help",
            "care",
            "expert",
            "guru",
            "ninja",
            "specialist",
            "consultant",
            "advisor",
            "counselor",
            "therapist",
            "doctor",
            "physician",
            "surgeon",
            "dentist",
            "pharmacist",
            "nurse",
            "paramedic",
            "engineer",
            "architect",
            "designer",
            "developer",
            "programmer",
            "coder",
            "hacker",
            "admin",
            "ops",
            "sysadmin",
            "security",
            "cyber",
            "data",
            "analytics",
            "ml",
            "blockchain",
            "crypto",
            "bitcoin",
            "ethereum",
            "defi",
            "nft",
            "web3",
            "metaverse",
            "vr",
            "ar",
            "gg",
            "ly",
            "to",
            "pk",
            "bd",
            "nz",
        }
    with tld_file.open() as f:
        return {line.strip().lower() for line in f if line.strip()}


_IANA_TLDS = _load_tlds()

# Domain: at least one dot, valid TLD from IANA list, no spaces, no @
_DOMAIN_LABEL_RE = r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
_TLD_PATTERN = "|".join(sorted(_IANA_TLDS, key=len, reverse=True))
DOMAIN_RE = re.compile(rf"^(?:{_DOMAIN_LABEL_RE}\.)+(?:{_TLD_PATTERN})$", re.IGNORECASE)


def detect_target_type(target: str) -> str:
    """Detect the type of a target string.

    Detection order (first match wins):
    1. Starts with http:// or https:// -> "url"
    2. Matches IPv4 pattern -> "ip"
    3. Contains @ and looks like email -> "email"
    4. Looks like a domain (valid IANA TLD) -> "domain"
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
