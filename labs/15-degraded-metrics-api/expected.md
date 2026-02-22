# 15-degraded-metrics-api

## Intent

Simulate degraded runtime metrics availability during triage.

## Expected behavior

- Engine remains read-only and bounded.
- If metrics are unavailable, report explains uncertainty and asks for minimal next data.
- No command spam when observability surface is reduced.
