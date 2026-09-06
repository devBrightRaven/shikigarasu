import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "codex" / "skills" / "shikigarasu" / "scripts" / "closure_gate.py"
SPEC = importlib.util.spec_from_file_location("closure_gate", SCRIPT)
GATE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(GATE)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ClosureFixture:
    def __init__(self, root: Path):
        self.root = root
        self.spec = root / "spec.md"
        self.spec.write_text("# frozen specification\n\nRequirement A and B.\n", encoding="utf-8")
        member = root / "src" / "main.py"
        member.parent.mkdir(parents=True)
        member.write_text("print('reviewed')\n", encoding="utf-8")
        self.member = member

        evidence = root / "evidence" / "slices"
        evidence.mkdir(parents=True)
        self.write_json(root / "evidence" / "REQ-A.json", self.requirement("REQ-A"))
        self.write_json(root / "evidence" / "REQ-B.json", self.requirement("REQ-B"))
        self.write_json(root / "evidence" / "slices" / "slice-a-red.json", self.receipt(
            "slice-a", "RED", exit_code=1, failures=1, observed=["FAIL expected"]
        ))
        self.write_json(root / "evidence" / "slices" / "slice-a-green.json", self.receipt(
            "slice-a", "GREEN", observed=["PASS"]
        ))
        self.write_json(root / "evidence" / "integration.json", self.checks("integration"))

        artifact_descriptor = root / "artifact.json"
        self.write_json(artifact_descriptor, {"files": {"src/main.py": digest(member)}})
        self.artifact_descriptor = artifact_descriptor

        artifact_sha = digest(artifact_descriptor)
        self.write_json(root / "evidence" / "reviewer-a.json", self.review(
            "reviewer-a", artifact_sha
        ))
        self.write_json(root / "evidence" / "reviewer-b.json", self.review(
            "reviewer-b", artifact_sha
        ))

        self.manifest = {
            "schema_version": "sdd-closure/v1",
            "contract": {
                "requirement_ids": ["REQ-A", "REQ-B"],
                "spec": {"path": "spec.md", "sha256": digest(self.spec)},
                "artifact": {
                    "path": "artifact.json",
                    "sha256": artifact_sha,
                    "files": {"src/main.py": digest(member)},
                },
            },
            "evidence": {
                "requirements": {
                    "REQ-A": {"path": "evidence/REQ-A.json"},
                    "REQ-B": {"path": "evidence/REQ-B.json"},
                },
                "slices": [
                    {
                        "id": "slice-a",
                        "requirement_ids": ["REQ-A", "REQ-B"],
                        "receipts": [
                            {"path": "evidence/slices/slice-a-red.json"},
                            {"path": "evidence/slices/slice-a-green.json"},
                        ],
                    }
                ],
                "integration": {"path": "evidence/integration.json"},
            },
            "producers": ["producer-1"],
            "reviewers": [
                {"id": "reviewer-a", "path": "evidence/reviewer-a.json"},
                {"id": "reviewer-b", "path": "evidence/reviewer-b.json"},
            ],
            "findings": [],
            "collective_fix_rounds": 1,
        }

    @staticmethod
    def write_json(path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def checks(description: str) -> dict:
        return {
            "checks": [
                {
                    "command": f"run {description}",
                    "exit_code": 0,
                    "failures": 0,
                    "observed": ["PASS"],
                }
            ]
        }

    @staticmethod
    def requirement(requirement_id: str) -> dict:
        value = ClosureFixture.checks(f"requirement {requirement_id}")
        value["requirement_id"] = requirement_id
        return value

    @staticmethod
    def receipt(
        slice_id: str,
        phase: str,
        exit_code: int = 0,
        failures: int = 0,
        observed: list[str] | None = None,
    ) -> dict:
        observed = observed or ["PASS"]
        return {
            "slice_id": slice_id,
            "phase": phase,
            "checks": [
                {
                    "command": f"run {slice_id} {phase.lower()}",
                    "exit_code": exit_code,
                    "failures": failures,
                    "observed": observed,
                }
            ],
        }

    @staticmethod
    def review(reviewer_id: str, artifact_sha: str) -> dict:
        value = ClosureFixture.checks(f"review {reviewer_id}")
        value.update({
            "reviewer_id": reviewer_id,
            "independent": True,
            "verdict": "pass",
            "artifact_sha256": artifact_sha,
        })
        return value

    def save_manifest(self, name: str = "manifest.json") -> Path:
        path = self.root / name
        self.write_json(path, self.manifest)
        return path


class ClosureGateTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory, ClosureFixture]:
        temp_dir = tempfile.TemporaryDirectory()
        return temp_dir, ClosureFixture(Path(temp_dir.name))

    def run_fixture(self, fixture: ClosureFixture) -> dict:
        return GATE.run(fixture.save_manifest())

    def test_complete_frozen_contract_is_closable(self):
        temp_dir, fixture = self.fixture()
        try:
            result = self.run_fixture(fixture)
            self.assertEqual("CLOSABLE", result["verdict"])
            self.assertEqual(0, result["exit_code"])
            self.assertEqual([], result["reasons"])
        finally:
            temp_dir.cleanup()

    def test_cli_prints_result_and_returns_closable_exit_code(self):
        temp_dir, fixture = self.fixture()
        try:
            manifest = fixture.save_manifest()
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), str(manifest)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, completed.returncode)
            self.assertEqual("CLOSABLE", json.loads(completed.stdout)["verdict"])
        finally:
            temp_dir.cleanup()

    def test_missing_requirement_evidence_blocks(self):
        temp_dir, fixture = self.fixture()
        try:
            del fixture.manifest["evidence"]["requirements"]["REQ-B"]
            result = self.run_fixture(fixture)
            self.assertEqual("BLOCKED", result["verdict"])
            self.assertEqual(2, result["exit_code"])
            self.assertTrue(any(reason["code"].startswith("requirement.REQ-B") for reason in result["reasons"]))
        finally:
            temp_dir.cleanup()

    def test_requirement_ids_must_be_unique_and_evidence_keys_must_match(self):
        temp_dir, fixture = self.fixture()
        try:
            fixture.manifest["contract"]["requirement_ids"] = ["REQ-A", "REQ-A"]
            result = self.run_fixture(fixture)
            self.assertEqual("BLOCKED", result["verdict"])
            self.assertTrue(any(reason["code"] == "contract.requirement_ids" for reason in result["reasons"]))
        finally:
            temp_dir.cleanup()

    def test_spec_digest_mismatch_blocks(self):
        temp_dir, fixture = self.fixture()
        try:
            fixture.manifest["contract"]["spec"]["sha256"] = "0" * 64
            result = self.run_fixture(fixture)
            self.assertTrue(any(reason["code"] == "contract.spec.hash" for reason in result["reasons"]))
        finally:
            temp_dir.cleanup()

    def test_artifact_inventory_must_match_descriptor(self):
        temp_dir, fixture = self.fixture()
        try:
            fixture.manifest["contract"]["artifact"]["files"]["src/extra.py"] = "0" * 64
            result = self.run_fixture(fixture)
            self.assertTrue(any(reason["code"] == "artifact.inventory" for reason in result["reasons"]))
        finally:
            temp_dir.cleanup()

    def test_artifact_member_hash_mismatch_blocks(self):
        temp_dir, fixture = self.fixture()
        try:
            fixture.member.write_text("tampered\n", encoding="utf-8")
            result = self.run_fixture(fixture)
            self.assertTrue(any(reason["code"] == "artifact.member.hash" for reason in result["reasons"]))
        finally:
            temp_dir.cleanup()

    def test_requirement_receipt_label_and_exit_code_are_checked(self):
        temp_dir, fixture = self.fixture()
        try:
            path = fixture.root / "evidence" / "REQ-A.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["requirement_id"] = "REQ-B"
            value["checks"][0]["exit_code"] = 1
            fixture.write_json(path, value)
            result = self.run_fixture(fixture)
            codes = {reason["code"] for reason in result["reasons"]}
            self.assertIn("requirement.REQ-A.identity", codes)
            self.assertIn("requirement.REQ-A.checks", codes)
        finally:
            temp_dir.cleanup()

    def test_red_green_receipts_are_ordered_and_have_expected_outcomes(self):
        temp_dir, fixture = self.fixture()
        try:
            fixture.manifest["evidence"]["slices"][0]["receipts"].reverse()
            result = self.run_fixture(fixture)
            self.assertTrue(any(reason["code"] == "slice.slice-a.order" for reason in result["reasons"]))
        finally:
            temp_dir.cleanup()

    def test_slice_requirement_mapping_must_cover_frozen_ids_and_reject_unknown_ids(self):
        temp_dir, fixture = self.fixture()
        try:
            fixture.manifest["evidence"]["slices"][0]["requirement_ids"] = ["REQ-A"]
            result = self.run_fixture(fixture)
            self.assertTrue(any(reason["code"] == "evidence.slices.coverage" for reason in result["reasons"]))

            fixture.manifest["evidence"]["slices"][0]["requirement_ids"] = ["REQ-A", "REQ-B", "REQ-UNKNOWN"]
            result = self.run_fixture(fixture)
            self.assertTrue(any(reason["code"] == "slice.slice-a.requirements" for reason in result["reasons"]))
        finally:
            temp_dir.cleanup()

    def test_boolean_exit_codes_and_failures_are_not_integers(self):
        temp_dir, fixture = self.fixture()
        try:
            path = fixture.root / "evidence" / "integration.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["checks"][0]["exit_code"] = False
            value["checks"][0]["failures"] = True
            fixture.write_json(path, value)
            result = self.run_fixture(fixture)
            self.assertTrue(any(reason["code"] == "integration.checks" for reason in result["reasons"]))
        finally:
            temp_dir.cleanup()

    def test_observed_output_must_contain_nonempty_strings(self):
        temp_dir, fixture = self.fixture()
        try:
            path = fixture.root / "evidence" / "integration.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["checks"][0]["observed"] = [None]
            fixture.write_json(path, value)
            result = self.run_fixture(fixture)
            self.assertTrue(any(reason["code"] == "integration.checks" for reason in result["reasons"]))
        finally:
            temp_dir.cleanup()

    def test_integration_must_exit_zero(self):
        temp_dir, fixture = self.fixture()
        try:
            path = fixture.root / "evidence" / "integration.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["checks"][0]["exit_code"] = 1
            value["checks"][0]["failures"] = 1
            fixture.write_json(path, value)
            result = self.run_fixture(fixture)
            self.assertTrue(any(reason["code"] == "integration.checks" for reason in result["reasons"]))
        finally:
            temp_dir.cleanup()

    def test_reviewers_must_be_two_distinct_nonproducers_on_same_artifact(self):
        temp_dir, fixture = self.fixture()
        try:
            fixture.manifest["reviewers"][0]["id"] = "producer-1"
            fixture.manifest["reviewers"][1]["id"] = "producer-1"
            reviewer_a = fixture.root / "evidence" / "reviewer-a.json"
            value = json.loads(reviewer_a.read_text(encoding="utf-8"))
            value["reviewer_id"] = "producer-1"
            fixture.write_json(reviewer_a, value)
            reviewer = fixture.root / "evidence" / "reviewer-b.json"
            value = json.loads(reviewer.read_text(encoding="utf-8"))
            value["reviewer_id"] = "producer-1"
            value["artifact_sha256"] = "0" * 64
            fixture.write_json(reviewer, value)
            result = self.run_fixture(fixture)
            codes = {reason["code"] for reason in result["reasons"]}
            self.assertIn("reviewers.distinct", codes)
            self.assertIn("reviewers.nonproducer", codes)
            self.assertIn("reviewer-2.artifact", codes)
        finally:
            temp_dir.cleanup()

    def test_producers_must_be_nonempty_and_unique(self):
        temp_dir, fixture = self.fixture()
        try:
            fixture.manifest["producers"] = []
            result = self.run_fixture(fixture)
            self.assertTrue(any(reason["code"] == "producers" for reason in result["reasons"]))
            fixture.manifest["producers"] = ["producer-1", "producer-1"]
            result = self.run_fixture(fixture)
            self.assertTrue(any(reason["code"] == "producers" for reason in result["reasons"]))
        finally:
            temp_dir.cleanup()

    def test_unresolved_important_or_critical_and_more_than_two_rounds_block(self):
        temp_dir, fixture = self.fixture()
        try:
            fixture.manifest["findings"] = [{"id": "f-1", "severity": "Critical", "status": "open"}]
            fixture.manifest["collective_fix_rounds"] = 3
            result = self.run_fixture(fixture)
            codes = {reason["code"] for reason in result["reasons"]}
            self.assertIn("findings.unresolved", codes)
            self.assertIn("fix_rounds", codes)
        finally:
            temp_dir.cleanup()

    def test_unknown_finding_severity_or_status_blocks(self):
        temp_dir, fixture = self.fixture()
        try:
            fixture.manifest["findings"] = [{"id": "f-1", "severity": "Severe", "status": "open"}]
            result = self.run_fixture(fixture)
            self.assertTrue(any(reason["code"] == "findings.shape" for reason in result["reasons"]))
        finally:
            temp_dir.cleanup()

    def test_malformed_or_missing_manifest_fails_closed_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing.json"
            result = GATE.run(missing)
            self.assertEqual(("BLOCKED", 2), (result["verdict"], result["exit_code"]))
            malformed = Path(temp_dir) / "malformed.json"
            malformed.write_text("{", encoding="utf-8")
            result = GATE.run(malformed)
            self.assertEqual("BLOCKED", result["verdict"])
            self.assertTrue(result["reasons"])

    def test_result_states_read_only_and_does_not_claim_authenticity_or_full_discovery(self):
        temp_dir, fixture = self.fixture()
        try:
            manifest = fixture.save_manifest()
            before = manifest.read_bytes()
            result = GATE.run(manifest)
            self.assertEqual(before, manifest.read_bytes())
            self.assertEqual(
                {
                    "read_only": True,
                    "queue_mutated": False,
                    "os_enforcement": False,
                    "authenticity_verified": False,
                    "full_repository_discovery": False,
                },
                result["claims"],
            )
        finally:
            temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
