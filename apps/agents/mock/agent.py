import asyncio
import hashlib
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from securescope_schemas.agent_interface import (
    AgentFinding,
    AgentMetadata,
    AnalysisContext,
    AnalysisResult,
    BaseAgent,
    LogEvent,
    LogLevel,
    Severity,
)

MOCK_FINDINGS = [
    AgentFinding(
        fingerprint=hashlib.sha256(b"sql-injection-users").hexdigest()[:16],
        file_path="src/api/users.py",
        line_start=42,
        line_end=45,
        severity=Severity.CRITICAL,
        category="SQL Injection",
        title="Unsanitized user input in SQL query",
        description="User-supplied 'username' parameter is concatenated directly into SQL query without parameterization.",
        code_snippet='query = f"SELECT * FROM users WHERE name = \'{username}\'"',
        suggested_fix="Use parameterized queries: cursor.execute('SELECT * FROM users WHERE name = %s', (username,))",
        confidence=0.95,
    ),
    AgentFinding(
        fingerprint=hashlib.sha256(b"xss-template").hexdigest()[:16],
        file_path="src/views/profile.html",
        line_start=18,
        line_end=18,
        severity=Severity.HIGH,
        category="XSS",
        title="Unescaped user content in template",
        description="User display name rendered without HTML escaping, allowing script injection.",
        code_snippet="<span>{{ user.display_name | safe }}</span>",
        suggested_fix="Remove '| safe' filter: {{ user.display_name }}",
        confidence=0.90,
    ),
    AgentFinding(
        fingerprint=hashlib.sha256(b"hardcoded-secret").hexdigest()[:16],
        file_path="src/config.py",
        line_start=7,
        line_end=7,
        severity=Severity.HIGH,
        category="Hardcoded Secret",
        title="API key hardcoded in source",
        description="AWS access key is hardcoded in configuration file.",
        code_snippet='AWS_KEY = "AKIA..."',
        suggested_fix="Use environment variables or a secrets manager.",
        confidence=0.99,
    ),
    AgentFinding(
        fingerprint=hashlib.sha256(b"path-traversal").hexdigest()[:16],
        file_path="src/api/files.py",
        line_start=31,
        line_end=34,
        severity=Severity.MEDIUM,
        category="Path Traversal",
        title="Unsanitized file path from user input",
        description="User-supplied filename used in os.path.join without validation, enabling directory traversal.",
        code_snippet='path = os.path.join(UPLOAD_DIR, request.params["filename"])',
        suggested_fix="Validate filename against a whitelist or use secure_filename().",
        confidence=0.85,
    ),
    AgentFinding(
        fingerprint=hashlib.sha256(b"weak-hash").hexdigest()[:16],
        file_path="src/auth/password.py",
        line_start=12,
        line_end=12,
        severity=Severity.LOW,
        category="Weak Cryptography",
        title="MD5 used for password hashing",
        description="MD5 is cryptographically broken and should not be used for password storage.",
        code_snippet="hashed = hashlib.md5(password.encode()).hexdigest()",
        suggested_fix="Use bcrypt or argon2 for password hashing.",
        confidence=0.98,
    ),
]


class MockAgent(BaseAgent):
    @classmethod
    def describe(cls) -> AgentMetadata:
        return AgentMetadata(
            name="mock",
            version="0.1.0",
            supported_languages=["python", "javascript", "typescript", "java"],
            max_input_size_bytes=100_000_000,
            cost_profile={"per_1k_input_tokens": 0.0, "per_1k_output_tokens": 0.0},
            description="Deterministic mock agent for testing. Returns 5 predefined findings.",
        )

    async def prepare(self, context: AnalysisContext) -> None:
        pass

    async def analyze(
        self, context: AnalysisContext
    ) -> AsyncIterator[LogEvent | AnalysisResult]:
        yield LogEvent(
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            message="MockAgent starting analysis",
            progress=0.0,
        )

        for i, finding in enumerate(MOCK_FINDINGS):
            await asyncio.sleep(0.1)
            yield LogEvent(
                timestamp=datetime.now(timezone.utc),
                level=LogLevel.INFO,
                message=f"Found: {finding.title}",
                progress=(i + 1) / len(MOCK_FINDINGS),
                tokens_used=(i + 1) * 500,
            )

        yield AnalysisResult(
            findings=MOCK_FINDINGS,
            tokens_used=2500,
            cost_usd=0.0,
            raw_output="MockAgent deterministic output",
        )

    async def terminate(self) -> None:
        pass
