"""Redaction utility tests."""

from agent.redaction import MAX_OUTPUT_CHARS, TRUNCATION_MARKER, redact_text


def test_redacts_common_secret_fields() -> None:
    # Ensure sensitive values are masked but keys remain visible.
    source = "token: abc123\npassword: p4ss\nclient-secret: xyz"
    out = redact_text(source)
    assert "abc123" not in out
    assert "p4ss" not in out
    assert "xyz" not in out
    assert out.count("[REDACTED]") == 3


def test_redacts_secret_yaml_data_blocks() -> None:
    source = (
        "apiVersion: v1\n"
        "kind: Secret\n"
        "metadata:\n"
        "  name: app-secret\n"
        "data:\n"
        "  password: c2VjcmV0\n"
        "  token: YWJjMTIz\n"
        "stringData:\n"
        "  apiKey: plain-text-key\n"
        "type: Opaque\n"
    )
    out = redact_text(source)
    assert "c2VjcmV0" not in out
    assert "YWJjMTIz" not in out
    assert "plain-text-key" not in out
    assert "data: [REDACTED]" in out
    assert "stringData: [REDACTED]" in out


def test_redacts_bearer_jwt_and_pem_tokens() -> None:
    source = (
        "Authorization: Bearer abc.DEF-123_456\n"
        "jwt: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature123\n"
        "-----BEGIN PRIVATE KEY-----\n"
        "sensitive-material\n"
        "-----END PRIVATE KEY-----\n"
    )
    out = redact_text(source)
    assert "Bearer abc.DEF-123_456" not in out
    assert "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature123" not in out
    assert "BEGIN PRIVATE KEY" not in out
    assert "sensitive-material" not in out
    assert "Bearer [REDACTED]" in out
    assert "[REDACTED_JWT]" in out
    assert "[REDACTED_PEM]" in out


def test_truncates_output_with_marker() -> None:
    source = "x" * (MAX_OUTPUT_CHARS + 250)
    out = redact_text(source)
    assert len(out) == MAX_OUTPUT_CHARS
    assert out.endswith(TRUNCATION_MARKER)
