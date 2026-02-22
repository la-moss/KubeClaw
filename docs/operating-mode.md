# Prompt 0: Operating Mode (Pinned)

This repo follows a strict implementation workflow:

This file is the canonical source of truth for engineering process.

1. Write a plan first (no code changes yet).
2. Ensure the plan is complete and internally consistent.
3. Create a TODO list derived from the plan.
4. Implement in small diffs with tests.
5. After each implementation step:
   - run tests
   - update the plan if reality differs
6. Keep persistent artifacts updated:
   - `docs/research.md`
   - `docs/plan.md`
   - `docs/todo.md`
   - `docs/decisions.md`
   - `docs/lessons.md`

Hard constraints:

- Read-only Kubernetes access only
- No raw shell execution exposed to the model
- Tool allowlist only
- Must refuse wrong kube context (only `kind-kubeclaw`)
- Must redact secrets and limit outputs
- Must support record + replay snapshots

Diff-first discipline (prepend to implementation requests):

1. Summarize intended diff in 5 bullets.
2. List files to change.
3. State how it will be tested.
4. Apply smallest possible steps.
5. After changes, update `docs/plan.md` if implementation deviated.
