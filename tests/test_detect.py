"""Target type detection tests."""

from otinstaller.detect import detect_target_type


def test_detect_url():
    """URLs are detected correctly."""
    assert detect_target_type("https://example.com") == "url"
    assert detect_target_type("http://example.com/path") == "url"
    assert detect_target_type("HTTPS://EXAMPLE.COM") == "url"


def test_detect_ipv4():
    """IPv4 addresses are detected correctly."""
    assert detect_target_type("192.168.1.1") == "ip"
    assert detect_target_type("10.0.0.1") == "ip"
    assert detect_target_type("8.8.8.8") == "ip"
    # Invalid IPs should not match
    assert detect_target_type("999.999.999.999") != "ip"
    assert detect_target_type("3.14") != "ip"


def test_detect_email():
    """Email addresses are detected correctly."""
    assert detect_target_type("user@example.com") == "email"
    assert detect_target_type("admin@test.org") == "email"
    assert detect_target_type("user.name@sub.domain.com") == "email"


def test_detect_domain():
    """Domains are detected correctly."""
    assert detect_target_type("example.com") == "domain"
    assert detect_target_type("sub.domain.org") == "domain"
    assert detect_target_type("test.co.uk") == "domain"
    # Non-domain-like strings should not match
    assert detect_target_type("random.text.here") != "domain"
    assert detect_target_type("3.14") != "domain"
    assert detect_target_type("not-a-domain") != "domain"


def test_detect_username_fallback():
    """Everything else falls through to username (including phone-like strings)."""
    assert detect_target_type("someuser") == "username"
    assert detect_target_type("john.doe") == "username"
    # Phone-like strings fall through to username (documented limitation)
    assert detect_target_type("+1-555-123-4567") == "username"
    assert detect_target_type("555-123-4567") == "username"
    assert detect_target_type("1234567890") == "username"


def test_detect_detection_order():
    """Detection order is respected: url > ip > email > domain > username."""
    # URL should win over domain
    assert detect_target_type("https://example.com") == "url"
    # IP should win over domain (though IP won't match domain regex)
    assert detect_target_type("192.168.1.1") == "ip"
    # Email should win over domain
    assert detect_target_type("user@example.com") == "email"
    # Domain should win over username
    assert detect_target_type("example.com") == "domain"
