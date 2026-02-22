# 13-degraded-logs-empty

## Intent

Simulate crash/restart behavior with sparse or empty log signal.

## Expected behavior

- Engine degrades gracefully without over-collecting commands.
- Report may stop with insufficient evidence if logs are not useful.
- Next best diagnostic asks for the minimum additional workload detail.
