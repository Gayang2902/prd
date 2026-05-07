import hashlib
import re


def normalize_code(snippet: str) -> str:
    """공백·주석 제거 후 정규화. AST 기반 정규화는 향후 옵션으로 추가."""
    lines = snippet.strip().splitlines()
    normalized = []
    for line in lines:
        line = line.strip()
        line = re.sub(r"#.*$", "", line)
        line = re.sub(r"//.*$", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            normalized.append(line)
    return "\n".join(normalized)


def compute_fingerprint(file_path: str, code_snippet: str, category: str) -> str:
    """PRD §B.2: hash(file_path + 정규화된 코드 스니펫 + vulnerability_type)"""
    normalized = normalize_code(code_snippet)
    payload = f"{file_path}:{normalized}:{category}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
