#!/usr/bin/env python3
"""Probe a fresh Codex process and bind its Shikigarasu answer to this plugin source."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


QUEUE_STATES = ["READY", "IN_PROGRESS", "REVIEW_1", "REVIEW_2", "FIX", "CLOSED", "BLOCKED"]
PROTECTED_ACTIONS = [
    "redefine scope",
    "negotiate user intent",
    "choose the canonical source",
    "make public commitments",
    "commit",
    "push",
    "publish",
    "declare the overall outcome complete",
]
EVIDENCE_FIELDS = [
    "ticket states",
    "producer/reviewer separation",
    "both review results",
    "acceptance evidence",
    "fix attempts",
    "blocked work",
    "notifications",
    "remaining limitations",
]
TIMEOUT_SECONDS = 180
PROMPT = """Use $shikigarasu. This is a contract inspection, not a goal or workflow.
Locate and read only the exact SKILL.md activated by that explicit invocation. Extract its source
path and SHA-256, queue states, review rules, convergence ceiling, closure rule, authority
boundaries, and evidence fields. Copy labels and phrases verbatim in source order. If a fact is
absent, use false, zero, or an empty list. Do not spawn agents or modify files.
"""


def plugin_skill_path() -> Path:
    return Path(__file__).resolve().parents[1] / "SKILL.md"


def response_schema() -> dict:
    properties = {
        "source_path": {"type": "string"},
        "source_sha256": {"type": "string"},
        "skill_name": {"type": "string"},
        "queue_states": {"type": "array", "items": {"type": "string"}},
        "review_passes": {"type": "integer"},
        "reviewers_fresh_context": {"type": "boolean"},
        "producer_and_reviewers_distinct": {"type": "boolean"},
        "fix_round_ceiling": {"type": "integer"},
        "fix_round_ceiling_is_collective": {"type": "boolean"},
        "closure_reviews_final_result": {"type": "boolean"},
        "closure_requires_no_critical_or_important": {"type": "boolean"},
        "external_actions_need_authorization": {"type": "boolean"},
        "scope_expansion_needs_authorization": {"type": "boolean"},
        "persistence_needs_explicit_authorization": {"type": "boolean"},
        "protected_actions": {"type": "array", "items": {"type": "string"}},
        "evidence_report_fields": {"type": "array", "items": {"type": "string"}},
    }
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def validate_probe(exit_code: int, last_message: str, skill_path: Path) -> list[str]:
    failures = [] if exit_code == 0 else [f"Codex exited with {exit_code}"]
    try:
        payload = json.loads(last_message)
    except json.JSONDecodeError as exc:
        return failures + [f"invalid JSON: {exc}"]
    if not isinstance(payload, dict):
        return failures + ["response is not an object"]

    try:
        reported_path = Path(str(payload.get("source_path", ""))).expanduser().resolve()
    except (OSError, RuntimeError):
        reported_path = None
    checks = {
        "source path": reported_path == skill_path.resolve(),
        "source hash": str(payload.get("source_sha256", "")).casefold()
        == hashlib.sha256(skill_path.read_bytes()).hexdigest(),
        "skill identity": payload.get("skill_name") == "shikigarasu",
        "queue states": payload.get("queue_states") == QUEUE_STATES,
        "two review passes": payload.get("review_passes") == 2,
        "fresh reviewers": payload.get("reviewers_fresh_context") is True,
        "distinct producer and reviewers": payload.get("producer_and_reviewers_distinct") is True,
        "two-fix-round ceiling": payload.get("fix_round_ceiling") == 2,
        "collective fix ceiling": payload.get("fix_round_ceiling_is_collective") is True,
        "final-result reviews": payload.get("closure_reviews_final_result") is True,
        "no important closure findings": payload.get("closure_requires_no_critical_or_important") is True,
        "external action boundary": payload.get("external_actions_need_authorization") is True,
        "scope boundary": payload.get("scope_expansion_needs_authorization") is True,
        "persistence boundary": payload.get("persistence_needs_explicit_authorization") is True,
        "protected actions": payload.get("protected_actions") == PROTECTED_ACTIONS,
        "evidence report": payload.get("evidence_report_fields") == EVIDENCE_FIELDS,
    }
    failures.extend(name for name, passed in checks.items() if not passed)
    return failures


def main() -> int:
    codex = shutil.which("codex")
    skill_path = plugin_skill_path()
    if not codex or not skill_path.is_file():
        print("FAIL: codex or this plugin's Shikigarasu skill was not found", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="codex-shikigarasu-probe-") as temp_dir:
        temp = Path(temp_dir)
        schema_path = temp / "schema.json"
        result_path = temp / "last-message.txt"
        schema_path.write_text(json.dumps(response_schema()), encoding="utf-8")
        try:
            result = subprocess.run(
                [
                    codex,
                    "exec",
                    "--ephemeral",
                    "--skip-git-repo-check",
                    "--color",
                    "never",
                    "-C",
                    temp_dir,
                    "-s",
                    "read-only",
                    "--output-schema",
                    str(schema_path),
                    "-o",
                    str(result_path),
                    PROMPT,
                ],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            print(f"FAIL: fresh Codex probe timed out after {TIMEOUT_SECONDS} seconds", file=sys.stderr)
            return 1
        failures = validate_probe(
            result.returncode,
            result_path.read_text(encoding="utf-8") if result_path.exists() else "",
            skill_path,
        )
        if failures:
            print(f"FAIL: {', '.join(failures)}", file=sys.stderr)
            return 1

    print("PASS: fresh Codex exposed this plugin's complete Shikigarasu contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
