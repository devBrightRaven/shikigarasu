#!/usr/bin/env python3
"""Check a frozen spec-driven closure contract without mutating project state.

The checker validates declared evidence and hashes only.  It does not execute
commands, discover repository files, verify receipt authenticity, enforce an
operating-system policy, or update a queue.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


SCHEMA_VERSION = "sdd-closure/v1"
EXIT_CLOSABLE = 0
EXIT_BLOCKED = 2
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
FINDING_SEVERITIES = {"Critical", "Important", "Minor", "Info"}
FINDING_STATUSES = {"open", "resolved", "closed"}


def sha256(path: Path) -> str | None:
    """Return a file's SHA-256, or ``None`` when it cannot be read."""

    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except (OSError, TypeError):
        return None


def valid_digest(value: object) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


class Gate:
    def __init__(self, manifest_path: str | Path):
        self.manifest_path = Path(manifest_path).expanduser().resolve()
        self.base = self.manifest_path.parent
        self.checks: list[dict[str, object]] = []
        self.reasons: list[dict[str, str]] = []

    def check(self, code: str, passed: bool, detail: str) -> bool:
        passed = bool(passed)
        self.checks.append({"name": code, "passed": passed, "detail": detail})
        if not passed:
            self.reasons.append({"code": code, "detail": detail})
        return passed

    def path(self, value: object, label: str) -> Path | None:
        if not isinstance(value, str) or not value.strip():
            self.check(label + ".path", False, "a non-empty path is required")
            return None
        try:
            candidate = Path(value).expanduser()
            if not candidate.is_absolute():
                candidate = self.base / candidate
            return candidate.resolve()
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            self.check(label + ".path", False, f"invalid path: {exc}")
            return None

    def read_json(self, path: Path | None, label: str) -> object | None:
        if path is None or not path.is_file():
            self.check(label + ".file", False, f"missing evidence file: {path}")
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.check(label + ".json", False, f"invalid JSON: {exc}")
            return None

    def referenced_json(self, reference: object, label: str) -> object | None:
        if isinstance(reference, dict):
            reference = reference.get("path")
        return self.read_json(self.path(reference, label), label)

    def receipt_checks(
        self,
        value: object,
        label: str,
        *,
        expect_zero: bool,
        expect_failure: bool = False,
    ) -> bool:
        """Validate the small raw command receipt shape.

        ``expect_failure`` is used only for a RED receipt.  A RED receipt must
        show at least one non-zero exit or positive failure count; GREEN and
        acceptance receipts must show zero for both fields.
        """

        if not isinstance(value, dict) or not isinstance(value.get("checks"), list) or not value["checks"]:
            return self.check(label + ".checks", False, "evidence needs a non-empty checks array")

        problems: list[str] = []
        saw_failure = False
        for number, item in enumerate(value["checks"], 1):
            if not isinstance(item, dict):
                problems.append(f"check {number} is not an object")
                continue
            command = item.get("command")
            if not isinstance(command, str) or not command.strip():
                problems.append(f"check {number} has no command")

            observed = item.get("observed")
            if not isinstance(observed, list) or not observed:
                problems.append(f"check {number} has no observed output")
            elif not all(isinstance(output, str) and output.strip() for output in observed):
                problems.append(f"check {number} observed output must be non-empty strings")

            failures = item.get("failures")
            if not isinstance(failures, int) or isinstance(failures, bool) or failures < 0:
                problems.append(f"check {number} has no non-negative integer failures")
            elif failures:
                saw_failure = True

            exit_code = item.get("exit_code")
            if not isinstance(exit_code, int) or isinstance(exit_code, bool):
                problems.append(f"check {number} has no integer exit_code")
            else:
                if exit_code:
                    saw_failure = True
                if expect_zero and exit_code != 0:
                    problems.append(f"check {number} returned exit_code {exit_code}, expected 0")

        if expect_zero:
            for number, item in enumerate(value["checks"], 1):
                if isinstance(item, dict):
                    failures = item.get("failures")
                    if isinstance(failures, int) and not isinstance(failures, bool) and failures != 0:
                        problems.append(f"check {number} reports failures={failures!r}, expected 0")
        elif expect_failure and not saw_failure:
            problems.append("RED evidence must show a non-zero exit_code or positive failures")

        return self.check(
            label + ".checks",
            not problems,
            "all evidence checks passed" if not problems else "; ".join(problems),
        )

    def finish(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "manifest": str(self.manifest_path),
            "checks": self.checks,
            "reasons": self.reasons,
            "verdict": "BLOCKED" if self.reasons else "CLOSABLE",
            "exit_code": EXIT_BLOCKED if self.reasons else EXIT_CLOSABLE,
            "claims": {
                "read_only": True,
                "queue_mutated": False,
                "os_enforcement": False,
                "authenticity_verified": False,
                "full_repository_discovery": False,
            },
        }


def _valid_id_list(gate: Gate, value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        gate.check(label, False, "a non-empty list of requirement IDs is required")
        return []
    ids = [item for item in value if isinstance(item, str) and item.strip()]
    valid = len(ids) == len(value) and len(set(ids)) == len(ids)
    gate.check(label, valid, "requirement IDs must be non-empty strings and unique")
    return ids if valid else []


def _check_frozen_contract(gate: Gate, manifest: dict[str, object]) -> tuple[list[str], Path | None, str | None, dict[str, str]]:
    contract = manifest.get("contract")
    if not isinstance(contract, dict):
        gate.check("contract.shape", False, "contract object is required")
        return [], None, None, {}

    requirement_ids = _valid_id_list(gate, contract.get("requirement_ids"), "contract.requirement_ids")

    spec = contract.get("spec")
    if not isinstance(spec, dict):
        gate.check("contract.spec.shape", False, "spec object with path and sha256 is required")
    else:
        spec_path = gate.path(spec.get("path"), "contract.spec")
        expected = spec.get("sha256")
        valid_expected = gate.check("contract.spec.digest", valid_digest(expected), "spec sha256 must be 64 hexadecimal characters")
        actual = sha256(spec_path) if spec_path is not None and spec_path.is_file() else None
        gate.check("contract.spec.hash", valid_expected and actual == expected.lower(), "spec hash matches frozen contract")

    artifact = contract.get("artifact")
    if not isinstance(artifact, dict):
        gate.check("contract.artifact.shape", False, "artifact object with path, sha256, and files is required")
        return requirement_ids, None, None, {}

    artifact_path = gate.path(artifact.get("path"), "contract.artifact")
    expected_artifact = artifact.get("sha256")
    valid_expected_artifact = gate.check(
        "contract.artifact.digest",
        valid_digest(expected_artifact),
        "artifact sha256 must be 64 hexadecimal characters",
    )
    actual_artifact = sha256(artifact_path) if artifact_path is not None and artifact_path.is_file() else None
    gate.check(
        "contract.artifact.hash",
        valid_expected_artifact and actual_artifact == expected_artifact.lower(),
        "artifact hash matches frozen contract",
    )

    files = artifact.get("files")
    files_ok = isinstance(files, dict) and bool(files)
    if files_ok:
        files_ok = all(
            isinstance(reference, str)
            and bool(reference.strip())
            and valid_digest(expected)
            for reference, expected in files.items()
        )
    gate.check(
        "contract.artifact.inventory",
        files_ok,
        "artifact files must be a non-empty path-to-sha256 map",
    )
    return requirement_ids, artifact_path, actual_artifact, files if files_ok else {}


def _check_artifact(gate: Gate, artifact_path: Path | None, declared: dict[str, str]) -> None:
    artifact_data = gate.read_json(artifact_path, "artifact")
    embedded = artifact_data.get("files") if isinstance(artifact_data, dict) else None
    equal = isinstance(embedded, dict) and embedded == declared
    gate.check(
        "artifact.inventory",
        equal,
        "artifact descriptor files must equal the frozen declared inventory",
    )
    if not equal:
        return
    for reference, expected in declared.items():
        path = gate.path(reference, "artifact.member")
        actual = sha256(path) if path is not None and path.is_file() else None
        gate.check(
            "artifact.member.hash",
            valid_digest(expected) and actual == expected.lower(),
            f"artifact member hash matches: {reference}",
        )


def _check_requirements(gate: Gate, manifest: dict[str, object], requirement_ids: list[str]) -> None:
    evidence = manifest.get("evidence")
    if not isinstance(evidence, dict):
        gate.check("evidence.shape", False, "evidence object is required")
        return
    requirements = evidence.get("requirements")
    keys = set(requirements) if isinstance(requirements, dict) else set()
    gate.check(
        "evidence.requirements",
        isinstance(requirements, dict) and keys == set(requirement_ids),
        "requirement evidence keys must equal frozen requirement IDs",
    )
    if not isinstance(requirements, dict):
        return
    for requirement_id in requirement_ids:
        label = f"requirement.{requirement_id}"
        data = gate.referenced_json(requirements.get(requirement_id), label)
        identity = isinstance(data, dict) and data.get("requirement_id") == requirement_id
        gate.check(label + ".identity", identity, "evidence is labelled for the required requirement")
        gate.receipt_checks(data, label, expect_zero=True)


def _check_slices(gate: Gate, evidence: dict[str, object], requirement_ids: list[str]) -> None:
    slices = evidence.get("slices")
    if not isinstance(slices, list) or not slices:
        gate.check("evidence.slices", False, "a non-empty ordered slice list is required")
        return
    ids: list[str] = []
    covered: set[str] = set()
    for index, item in enumerate(slices, 1):
        if not isinstance(item, dict):
            gate.check(f"slice.{index}.shape", False, "slice must be an object")
            continue
        slice_id = item.get("id")
        valid_id = isinstance(slice_id, str) and bool(slice_id.strip())
        gate.check(f"slice.{index}.id", valid_id, "slice id must be a non-empty string")
        if not valid_id:
            continue
        ids.append(slice_id)
        mapped = item.get("requirement_ids")
        mapped_ok = (
            isinstance(mapped, list)
            and bool(mapped)
            and all(isinstance(requirement_id, str) and requirement_id.strip() for requirement_id in mapped)
            and len(set(mapped)) == len(mapped)
            and set(mapped).issubset(set(requirement_ids))
        )
        gate.check(
            f"slice.{slice_id}.requirements",
            mapped_ok,
            "slice requirement_ids must be unique frozen requirement IDs",
        )
        if mapped_ok:
            covered.update(mapped)
        receipts = item.get("receipts")
        valid_receipts = isinstance(receipts, list) and len(receipts) == 2
        gate.check(
            f"slice.{slice_id}.shape",
            valid_receipts,
            "slice must have exactly two receipts in RED then GREEN order",
        )
        if not valid_receipts:
            continue
        phases = ("RED", "GREEN")
        observed_phases: list[object] = []
        for expected_phase, reference in zip(phases, receipts):
            label = f"slice.{slice_id}.{expected_phase.lower()}"
            data = gate.referenced_json(reference, label)
            observed_phases.append(data.get("phase") if isinstance(data, dict) else None)
            identity = isinstance(data, dict) and data.get("slice_id") == slice_id
            phase = isinstance(data, dict) and data.get("phase") == expected_phase
            gate.check(label + ".identity", identity, "receipt is labelled for the slice")
            gate.check(label + ".phase", phase, f"receipt phase is {expected_phase}")
            gate.receipt_checks(
                data,
                label,
                expect_zero=expected_phase == "GREEN",
                expect_failure=expected_phase == "RED",
            )
        gate.check(
            f"slice.{slice_id}.order",
            observed_phases == list(phases),
            "slice receipts must be ordered RED then GREEN",
        )
    gate.check("evidence.slices.unique", len(ids) == len(set(ids)), "slice IDs must be unique")
    gate.check(
        "evidence.slices.coverage",
        covered == set(requirement_ids),
        "slice requirement_ids must cover every frozen requirement ID",
    )


def _check_integration(gate: Gate, evidence: dict[str, object]) -> None:
    data = gate.referenced_json(evidence.get("integration"), "integration")
    gate.receipt_checks(data, "integration", expect_zero=True)


def _check_reviewers(
    gate: Gate,
    manifest: dict[str, object],
    producers: list[str],
    artifact_digest: str | None,
) -> None:
    reviewers = manifest.get("reviewers")
    if not isinstance(reviewers, list) or len(reviewers) != 2:
        gate.check("reviewers.count", False, "exactly two reviewers are required")
        return
    reviewer_ids: list[str] = []
    for number, entry in enumerate(reviewers, 1):
        label = f"reviewer-{number}"
        if not isinstance(entry, dict):
            gate.check(label + ".shape", False, "reviewer must be an object")
            continue
        reviewer_id = entry.get("id")
        valid_id = isinstance(reviewer_id, str) and bool(reviewer_id.strip())
        gate.check(label + ".id", valid_id, "reviewer id must be a non-empty string")
        if valid_id:
            reviewer_ids.append(reviewer_id)
        data = gate.referenced_json(entry.get("path"), label)
        identity = valid_id and isinstance(data, dict) and data.get("reviewer_id") == reviewer_id
        gate.check(label + ".identity", identity, "reviewer id matches evidence")
        gate.receipt_checks(data, label, expect_zero=True)
        independent = isinstance(data, dict) and data.get("independent") is True and data.get("verdict") == "pass"
        gate.check(label + ".independent", independent, "reviewer is independent and passed")
        same_artifact = isinstance(data, dict) and isinstance(artifact_digest, str) and data.get("artifact_sha256") == artifact_digest
        gate.check(label + ".artifact", same_artifact, "reviewer evidence binds to the frozen artifact")
    gate.check(
        "reviewers.distinct",
        len(reviewer_ids) == 2 and len(set(reviewer_ids)) == 2,
        "reviewer IDs must be distinct",
    )
    gate.check(
        "reviewers.nonproducer",
        len(reviewer_ids) == 2 and all(reviewer_id not in producers for reviewer_id in reviewer_ids),
        "neither reviewer may be a producer",
    )


def _check_findings_and_rounds(gate: Gate, manifest: dict[str, object]) -> None:
    findings = manifest.get("findings")
    unresolved: list[str] = []
    malformed = False
    if not isinstance(findings, list):
        malformed = True
    else:
        for index, finding in enumerate(findings, 1):
            if not isinstance(finding, dict) or not isinstance(finding.get("severity"), str) or not isinstance(finding.get("status"), str):
                malformed = True
                continue
            if finding["severity"] not in FINDING_SEVERITIES or finding["status"] not in FINDING_STATUSES:
                malformed = True
                continue
            if finding["severity"] in {"Important", "Critical"} and finding["status"] not in {"resolved", "closed"}:
                unresolved.append(f"finding {index}")
    gate.check("findings.shape", not malformed, "findings must be a list of objects with severity and status")
    gate.check("findings.unresolved", not unresolved, "no unresolved Important/Critical findings")

    rounds = manifest.get("collective_fix_rounds")
    valid_rounds = isinstance(rounds, int) and not isinstance(rounds, bool) and 0 <= rounds <= 2
    gate.check("fix_rounds", valid_rounds, "collective fix rounds must be an integer from 0 through 2")


def run(manifest_path: str | Path) -> dict[str, object]:
    gate = Gate(manifest_path)
    try:
        manifest = gate.read_json(gate.manifest_path, "manifest")
        if not isinstance(manifest, dict):
            gate.check("manifest.shape", False, "manifest must be a JSON object")
            return gate.finish()
        gate.check("schema_version", manifest.get("schema_version") == SCHEMA_VERSION, f"schema_version must be {SCHEMA_VERSION}")

        requirement_ids, artifact_path, artifact_digest, inventory = _check_frozen_contract(gate, manifest)
        _check_artifact(gate, artifact_path, inventory)
        _check_requirements(gate, manifest, requirement_ids)

        evidence = manifest.get("evidence")
        if isinstance(evidence, dict):
            _check_slices(gate, evidence, requirement_ids)
            _check_integration(gate, evidence)
        producers = manifest.get("producers")
        valid_producers = (
            isinstance(producers, list)
            and bool(producers)
            and all(isinstance(item, str) and item.strip() for item in producers)
            and len(set(producers)) == len(producers)
        )
        gate.check("producers", valid_producers, "producers must be a list of non-empty IDs")
        _check_reviewers(gate, manifest, producers if valid_producers else [], artifact_digest)
        _check_findings_and_rounds(gate, manifest)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        gate.check("gate.input", False, f"malformed or unreadable closure input: {exc}")
    except Exception as exc:  # fail closed for unexpected malformed shapes
        gate.check("gate.internal", False, f"checker could not validate input: {exc}")
    return gate.finish()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate declared SDD closure evidence without mutating a queue.")
    parser.add_argument("manifest", type=Path, help="frozen closure manifest JSON")
    args = parser.parse_args(argv)
    result = run(args.manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
