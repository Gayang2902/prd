"""Built-in presets for SecureScope.

Call seed_builtin_presets() at startup to ensure the 3 default presets exist.
"""

BUILTIN_PRESETS = [
    {
        "name": "표준 보안 검수",
        "version_sha": "builtin-v1",
        "prompt_template": (
            "Perform a comprehensive security review of the provided codebase. "
            "Identify vulnerabilities including but not limited to: SQL injection, XSS, "
            "CSRF, authentication/authorization flaws, insecure deserialization, "
            "hardcoded secrets, path traversal, and cryptographic weaknesses. "
            "For each finding, provide severity, affected code location, and remediation guidance."
        ),
        "ruleset": {
            "categories": [
                "SQL Injection",
                "XSS",
                "CSRF",
                "Authentication",
                "Authorization",
                "Hardcoded Secret",
                "Path Traversal",
                "Weak Cryptography",
                "Insecure Deserialization",
                "Information Disclosure",
            ],
            "min_confidence": 0.7,
        },
        "timeout_seconds": 1800,
        "max_retries": 3,
        "is_shared": True,
    },
    {
        "name": "Quick Diff Scan",
        "version_sha": "builtin-v1",
        "prompt_template": (
            "Review only the changed lines (diff) for security issues. "
            "Focus on newly introduced vulnerabilities. "
            "Be concise — skip unchanged code."
        ),
        "ruleset": {
            "categories": [
                "SQL Injection",
                "XSS",
                "Hardcoded Secret",
                "Authentication",
                "Authorization",
            ],
            "min_confidence": 0.8,
            "diff_only": True,
        },
        "timeout_seconds": 600,
        "max_retries": 2,
        "is_shared": True,
    },
    {
        "name": "PII 집중 스캔",
        "version_sha": "builtin-v1",
        "prompt_template": (
            "Scan the codebase for personally identifiable information (PII) exposure risks. "
            "Look for: logging of sensitive data, unmasked PII in responses, "
            "PII stored without encryption, PII in URLs or query parameters, "
            "and missing data retention controls."
        ),
        "ruleset": {
            "categories": [
                "PII Exposure",
                "Logging Sensitive Data",
                "Unencrypted PII Storage",
                "Data Retention",
                "Information Disclosure",
            ],
            "min_confidence": 0.75,
        },
        "timeout_seconds": 1200,
        "max_retries": 3,
        "is_shared": True,
    },
]
