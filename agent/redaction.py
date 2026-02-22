"""Output redaction utilities for reports and tool output."""

from __future__ import annotations

import re

MAX_OUTPUT_CHARS = 20_000
TRUNCATION_MARKER = "[TRUNCATED]"

# These patterns target common secret-like fields in YAML or plain text output.
KEY_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(token:\s*)(\S+)"),
    re.compile(r"(?i)(password:\s*)(\S+)"),
    re.compile(r"(?i)(client-secret:\s*)(\S+)"),
)

BEARER_TOKEN_PATTERN = re.compile(
    r"(?i)\b(Bearer)\s+([A-Za-z0-9\-._~+/]+=*)"
)
JWT_LIKE_PATTERN = re.compile(
    r"\beyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"
)
PEM_BLOCK_PATTERN = re.compile(
    r"-----BEGIN [A-Z0-9 ]+-----[\s\S]*?-----END [A-Z0-9 ]+-----"
)


def _remove_secret_yaml_blocks(text: str) -> str:
    """Remove Secret YAML `data`/`stringData` blocks entirely."""
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        block_match = re.match(r"^(\s*)(data|stringData):\s*$", line)
        if block_match:
            indent = len(block_match.group(1))
            key = block_match.group(2)
            out.append(f"{' ' * indent}{key}: [REDACTED]")
            i += 1
            while i < len(lines):
                next_line = lines[i]
                stripped = next_line.strip()
                if not stripped:
                    i += 1
                    continue
                next_indent = len(next_line) - len(next_line.lstrip(" "))
                if next_indent <= indent:
                    break
                i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def _truncate(text: str) -> str:
    """Apply a hard output-size limit with explicit marker."""
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    keep = max(0, MAX_OUTPUT_CHARS - len(TRUNCATION_MARKER))
    return text[:keep] + TRUNCATION_MARKER


def redact_text(text: str) -> str:
    """Run redaction pipeline and enforce output-size limits."""
    redacted = text
    redacted = _remove_secret_yaml_blocks(redacted)

    for pattern in KEY_VALUE_PATTERNS:
        redacted = pattern.sub(r"\1[REDACTED]", redacted)
    redacted = BEARER_TOKEN_PATTERN.sub(r"\1 [REDACTED]", redacted)
    redacted = JWT_LIKE_PATTERN.sub("[REDACTED_JWT]", redacted)
    redacted = PEM_BLOCK_PATTERN.sub("[REDACTED_PEM]", redacted)

    redacted = _truncate(redacted)
    return redacted
