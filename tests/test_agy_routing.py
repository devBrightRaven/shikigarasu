import importlib.util
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "codex" / "skills" / "shikigarasu" / "scripts" / "agy_adapter.py"
ROUTING = ROOT / "codex" / "skills" / "shikigarasu" / "references" / "agy-routing.md"
WORKFLOW = ROOT / "codex" / "skills" / "shikigarasu" / "references" / "final-artifact-review.md"
SPEC = importlib.util.spec_from_file_location("agy_adapter", MODULE_PATH)
AGY = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(AGY)


class FakeRunner:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append(args)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def completed(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(["agy"], returncode, stdout, stderr)


class AgyRoutingTests(unittest.TestCase):
    def test_task_type_model_routing_uses_discovered_models(self):
        models = ["gemini-x-flash-low", "gemini-x-flash-medium", "gemini-x-flash-high", "gemini-x-pro-high"]
        self.assertEqual("gemini-x-flash-low", AGY.route_task("source_extract", models)["model"])
        self.assertEqual("gemini-x-pro-high", AGY.route_task("visual_review", models)["model"])

    def test_high_risk_tasks_remain_with_codex(self):
        for task in ("scope", "canonical_source", "commit", "push", "publish", "final_completion"):
            with self.subTest(task=task):
                self.assertEqual("codex", AGY.route_task(task, ["gemini-x-flash-high"])["owner"])

    def test_requested_reported_mismatch_degrades_vision(self):
        result = AGY.evaluate_vision_gate(
            {
                "vision_verified": True,
                "model_reported": "Gemini 3.1 Pro (Low)",
                "filename": "gate.png",
                "largest_title": "TITLE",
                "position_relation": "blue is left of orange",
            },
            "gemini-3.6-flash-high",
            "gate.png",
            "TITLE",
            "blue is left",
        )
        self.assertEqual("degraded", result["status"])
        self.assertFalse(result["vision_checks"]["model_match"])

    def test_visual_fact_failure_degrades_review(self):
        result = AGY.evaluate_vision_gate(
            {
                "vision_verified": True,
                "model_reported": "Gemini 3.6 Flash (High)",
                "filename": "gate.png",
                "largest_title": "",
                "position_relation": "blue is left of orange",
            },
            "gemini-3.6-flash-high",
            "gate.png",
            "TITLE",
            "blue is left",
        )
        self.assertEqual("degraded", result["status"])
        self.assertFalse(result["vision_verified"])

    def test_spatial_relation_allows_connector_words(self):
        result = AGY.evaluate_vision_gate(
            {
                "vision_verified": True,
                "model_reported": "Gemini 3.6 Flash (High)",
                "filename": "gate.png",
                "largest_title": "TITLE",
                "position_relation": "The blue square is positioned to the left of the orange circle",
            },
            "gemini-3.6-flash-high",
            "gate.png",
            "TITLE",
            "blue square is to the left",
        )
        self.assertTrue(result["vision_checks"]["relation_match"])

    def test_invalid_json_gets_exactly_one_repair(self):
        calls = []

        def repair(raw):
            calls.append(raw)
            return '{"ok": true}'

        payload, repaired = AGY.parse_json_with_one_repair("not json", repair)
        self.assertEqual({"ok": True}, payload)
        self.assertTrue(repaired)
        self.assertEqual(1, len(calls))

    def test_invalid_json_after_one_repair_fails(self):
        calls = []

        def repair(raw):
            calls.append(raw)
            return "still not json"

        with self.assertRaises(json.JSONDecodeError):
            AGY.parse_json_with_one_repair("not json", repair)
        self.assertEqual(1, len(calls))

    def test_timeout_retry_is_bounded(self):
        timeout = subprocess.TimeoutExpired("agy", 1)
        runner = FakeRunner([timeout, timeout])
        result = AGY.run_bounded("prompt", "gemini-x-flash-low", timeout_sec=1, retry_limit=1, runner=runner)
        self.assertEqual(("failed", 2), (result["status"], result["attempts"]))

    def test_fallback_is_single_and_degraded(self):
        timeout = subprocess.TimeoutExpired("agy", 1)
        runner = FakeRunner([timeout, completed('{"ok": true}')])
        result = AGY.run_bounded(
            "prompt", "gemini-primary", timeout_sec=1, retry_limit=0,
            fallback_model="gemini-fallback", runner=runner,
        )
        self.assertEqual(("degraded", "gemini-fallback", 2), (result["status"], result["model_used"], result["attempts"]))

    def test_safety_refusal_is_not_retried(self):
        runner = FakeRunner([completed("I cannot assist because of a safety policy.")])
        result = AGY.run_bounded("prompt", "gemini-primary", fallback_model="gemini-fallback", runner=runner)
        self.assertEqual(("refused", 1), (result["status"], len(runner.calls)))

    def test_heterogeneous_review_degradation_is_disclosed(self):
        result = AGY.assess_heterogeneous_review(
            [
                {
                    "model_requested": "gemini-3.1-pro-high",
                    "model_reported": "Gemini 3.1 Pro (High)",
                    "artifact_verified": True,
                },
                {
                    "model_requested": "gemini-3.1-pro-high",
                    "model_reported": "Gemini 3.1 Pro (High)",
                    "artifact_verified": True,
                },
            ]
        )
        self.assertEqual("degraded", result["status"])
        self.assertFalse(result["model_diversity_verified"])

    def test_policy_and_final_review_boundaries_are_present(self):
        routing = ROUTING.read_text(encoding="utf-8")
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for action in ("commit", "push", "publish", "final completion"):
            self.assertIn(action, routing)
        self.assertIn("one-review/one-revision", workflow)
        self.assertIn("Do not run a second free-form art review", workflow)
        self.assertIn("Codex retains final scope, brand, content, revision, and completion authority", workflow)
        for cap in ("5 blocking", "8 recommended", "5 optional"):
            self.assertIn(cap, workflow)


if __name__ == "__main__":
    unittest.main()
