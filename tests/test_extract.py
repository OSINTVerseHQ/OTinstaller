"""Extract tests."""

from otinstaller.extract import extract_from_files, extract_indicators

SAMPLE_TEXT = """
Here is a test email: user@example.com and another one: admin@test.org
Domain test: example.com and sub.domain.org
Also an IP: 192.168.1.1 and another: 10.0.0.1
URLs: https://example.com/path and http://test.org/api
Noise that shouldn't match: 999.999.999.999 and not-an-ip and random.text.here
Duplicate email: user@example.com appears again
"""


def test_extract_indicators_basic():
    """extract_indicators finds emails, domains, IPs, URLs correctly."""
    result = extract_indicators(SAMPLE_TEXT)

    assert "user@example.com" in result["emails"]
    assert "admin@test.org" in result["emails"]
    assert len(result["emails"]) == 2  # deduplicated

    assert "example.com" in result["domains"]
    assert "sub.domain.org" in result["domains"]
    # test.org appears in URL http://test.org/api so it's also extracted as a domain
    assert "test.org" in result["domains"]
    assert "random.text.here" not in result["domains"]

    assert "192.168.1.1" in result["ips"]
    assert "10.0.0.1" in result["ips"]
    assert "999.999.999.999" not in result["ips"]  # invalid IP

    assert "https://example.com/path" in result["urls"]
    assert "http://test.org/api" in result["urls"]
    assert len(result["urls"]) == 2


def test_extract_indicators_deduplication():
    """Same indicator appearing multiple times appears once in output."""
    text = "email@test.com email@test.com email@test.com"
    result = extract_indicators(text)
    assert result["emails"] == ["email@test.com"]


def test_extract_indicators_no_matches():
    """Empty/no matches returns empty lists cleanly."""
    result = extract_indicators("no indicators here just text")
    assert result == {"emails": [], "domains": [], "ips": [], "urls": []}


def test_extract_from_files_multiple_files(tmp_path):
    """extract_from_files merges across multiple files correctly."""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("email1@test.com")
    file2.write_text("email2@test.com")

    result = extract_from_files([file1, file2])
    assert "email1@test.com" in result["emails"]
    assert "email2@test.com" in result["emails"]


def test_extract_from_files_skips_non_txt(tmp_path):
    """extract_from_files skips non-.txt files."""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.log"
    file1.write_text("email@test.com")
    file2.write_text("email2@test.com")

    result = extract_from_files([file1, file2])
    assert "email@test.com" in result["emails"]
    assert "email2@test.com" not in result["emails"]


def test_extract_from_files_skips_unreadable(tmp_path):
    """extract_from_files skips unreadable files without crashing."""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("email@test.com")
    file2.write_text("email2@test.com")

    # Make file2 unreadable
    file2.chmod(0o000)

    try:
        result = extract_from_files([file1, file2])
        assert "email@test.com" in result["emails"]
    finally:
        # Restore permissions so cleanup works
        file2.chmod(0o644)


def test_extract_from_files_empty():
    """extract_from_files with no files returns empty lists."""
    result = extract_from_files([])
    assert result == {"emails": [], "domains": [], "ips": [], "urls": []}
