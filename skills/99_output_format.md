# Output Format Template

Use this strict section order:

1. Objective
2. Observed facts (direct evidence only)
3. Interpretation
4. Hypotheses (ranked 1-3 with evidence)
5. Next best diagnostic (exact tool call)
6. Proposed fix (text only)
7. Rollback plan (text only)
8. Safety notes (read-only scope, redactions, truncations)

Formatting rules:
- Markdown and plain-text variants must contain the same sections.
- No markdown tables.
- Keep facts separated from inference.
