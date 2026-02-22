"""Render safe text-only suggested fix diffs and rollback notes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SuggestedFix:
    patch_text: str
    rollback_steps: str
    blast_radius: str


def render_suggested_fix(incident: str) -> SuggestedFix:
    if incident == "service_unreachable":
        return SuggestedFix(
            patch_text=(
                "Suggested YAML patch (text only, do not apply automatically):\n"
                "spec:\n"
                "  selector:\n"
                "    app: web-wrong\n"
                "Validation: kubectl get ep web-svc -n demo -o yaml"
            ),
            rollback_steps=(
                "Rollback: restore previous Service selector, then verify endpoints and service reachability."
            ),
            blast_radius="Blast radius: service routing behavior for pods behind this Service.",
        )
    if incident == "pending":
        return SuggestedFix(
            patch_text=(
                "Suggested YAML patch (text only, do not apply automatically):\n"
                "spec:\n"
                "  containers:\n"
                "  - resources:\n"
                "      requests:\n"
                "        cpu: \"250m\""
            ),
            rollback_steps="Rollback: revert CPU request to prior value if workload SLO degrades.",
            blast_radius="Blast radius: scheduling/placement behavior for the target pod.",
        )
    if incident == "imagepull":
        return SuggestedFix(
            patch_text=(
                "Suggested YAML patch (text only, do not apply automatically):\n"
                "spec:\n"
                "  containers:\n"
                "  - image: nginx:1.27"
            ),
            rollback_steps="Rollback: restore previous image tag if startup regressions appear.",
            blast_radius="Blast radius: deployment rollout for selected workload only.",
        )
    if incident == "oom":
        return SuggestedFix(
            patch_text=(
                "Suggested YAML patch (text only, do not apply automatically):\n"
                "resources:\n"
                "  limits:\n"
                "    memory: \"256Mi\""
            ),
            rollback_steps="Rollback: restore previous memory limit and monitor restart count.",
            blast_radius="Blast radius: memory allocation policy for the target pod/container.",
        )
    if incident == "crashloop":
        return SuggestedFix(
            patch_text=(
                "Suggested YAML patch (text only, do not apply automatically):\n"
                "env:\n"
                "  - name: DATABASE_URL\n"
                "    valueFrom:\n"
                "      secretKeyRef:\n"
                "        name: app-secret\n"
                "        key: DATABASE_URL"
            ),
            rollback_steps=(
                "Rollback: restore previous environment configuration and verify pod startup events."
            ),
            blast_radius="Blast radius: startup configuration for the target deployment.",
        )

    return SuggestedFix(
        patch_text="Insufficient evidence for a safe config patch recommendation.",
        rollback_steps="No rollback required; no changes proposed.",
        blast_radius="Blast radius: none (advisory only).",
    )
