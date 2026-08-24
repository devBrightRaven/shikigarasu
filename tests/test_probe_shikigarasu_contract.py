import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "codex" / "skills" / "shikigarasu" / "scripts" / "probe_shikigarasu_contract.py"
SPEC = importlib.util.spec_from_file_location("probe_shikigarasu_contract", SCRIPT)
PROBE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(PROBE)


class ShikigarasuContractProbeTests(unittest.TestCase):
    def payload(self, path: Path) -> dict:
        return {
            "source_path": str(path.resolve()),
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "skill_name": "shikigarasu",
            "queue_states": PROBE.QUEUE_STATES,
            "review_passes": 2,
            "reviewers_fresh_context": True,
            "producer_and_reviewers_distinct": True,
            "fix_round_ceiling": 2,
            "fix_round_ceiling_is_collective": True,
            "closure_reviews_final_result": True,
            "closure_requires_no_critical_or_important": True,
            "external_actions_need_authorization": True,
            "scope_expansion_needs_authorization": True,
            "persistence_needs_explicit_authorization": True,
            "protected_actions": PROBE.PROTECTED_ACTIONS,
            "evidence_report_fields": PROBE.EVIDENCE_FIELDS,
        }

    def test_probe_is_bound_to_canonical_plugin_source(self):
        self.assertEqual(
            ROOT / "codex" / "skills" / "shikigarasu" / "SKILL.md",
            PROBE.plugin_skill_path(),
        )

    def test_accepts_complete_source_bound_response(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            skill = Path(temp_dir) / "SKILL.md"
            skill.write_text("plugin contract", encoding="utf-8")
            self.assertEqual(PROBE.validate_probe(0, json.dumps(self.payload(skill)), skill), [])

    def test_prompt_and_schema_do_not_embed_expected_answers(self):
        model_input = PROBE.PROMPT + json.dumps(PROBE.response_schema())
        for answer in PROBE.QUEUE_STATES + PROBE.PROTECTED_ACTIONS + PROBE.EVIDENCE_FIELDS:
            self.assertNotIn(answer, model_input)

    def test_rejects_generic_or_echoed_response(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            skill = Path(temp_dir) / "SKILL.md"
            skill.write_text("plugin contract", encoding="utf-8")
            payload = self.payload(skill)
            payload.update(source_sha256="unknown", queue_states=[], reviewers_fresh_context=False)
            self.assertEqual(
                PROBE.validate_probe(0, json.dumps(payload), skill),
                ["source hash", "queue states", "fresh reviewers"],
            )


if __name__ == "__main__":
    unittest.main()
