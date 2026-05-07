from app.services.fingerprint import compute_fingerprint, normalize_code


def test_normalize_removes_comments_and_whitespace() -> None:
    code = """
    x = 1  # comment
    y = 2   // another
    z =   3
    """
    result = normalize_code(code)
    assert result == "x = 1\ny = 2\nz = 3"


def test_fingerprint_deterministic() -> None:
    fp1 = compute_fingerprint("src/app.py", "x = 1", "SQL Injection")
    fp2 = compute_fingerprint("src/app.py", "x = 1", "SQL Injection")
    assert fp1 == fp2
    assert len(fp1) == 16


def test_fingerprint_differs_on_category() -> None:
    fp1 = compute_fingerprint("src/app.py", "x = 1", "SQL Injection")
    fp2 = compute_fingerprint("src/app.py", "x = 1", "XSS")
    assert fp1 != fp2


def test_fingerprint_ignores_whitespace() -> None:
    fp1 = compute_fingerprint("src/app.py", "  x = 1  ", "SQL Injection")
    fp2 = compute_fingerprint("src/app.py", "x = 1", "SQL Injection")
    assert fp1 == fp2
