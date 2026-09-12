"""Static checks for the Codex-native, outcome-based routing contract.

These tests inspect the source contract only.  They do not run a host, spawn an
agent, or claim that a runtime selected a role.  A real host acceptance run
would need to record native tool events separately.
"""

import unittest
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "codex" / "skills" / "shikigarasu" / "SKILL.md"


class StaticCodexRoutingContractTests(unittest.TestCase):
    """Validate routing boundaries without inventing a source-level router."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL.read_text(encoding="utf-8")
        cls.lower = cls.text.lower()
        cls.normalized = re.sub(r"\s+", " ", cls.lower).strip()
        cls.outcome = cls.text.split("## Outcome-based routing", 1)[1].split(
            "## Run the queue", 1
        )[0]
        cls.outcome_normalized = re.sub(r"\s+", " ", cls.outcome.lower()).strip()
        cls.queue = cls.text.split("## Run the queue", 1)[1].split(
            "## Spec-driven work and test execution", 1
        )[0]
        cls.queue_normalized = re.sub(r"\s+", " ", cls.queue.lower()).strip()

    def test_source_is_explicitly_static_and_codex_native(self):
        self.assertIn("native-only", self.lower)
        self.assertIn("spawn_agent", self.text)
        for forbidden in (
            "claude",
            "TaskCreate",
            "TaskUpdate",
            "TaskOutput",
            "subagent_type=",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden.lower(), self.lower)

    def test_description_keeps_core_routing_context(self):
        description = re.search(r"^description: '(.+)'$", self.text, re.MULTILINE).group(1)
        # Source-content check, not a claim about a host truncation threshold.
        for trigger in ("parallel workstreams", "independent review", "simple single-task"):
            with self.subTest(trigger=trigger):
                self.assertIn(trigger, description.lower())

    def test_independent_review_uses_explicit_fresh_fork(self):
        dispatch = self.text.split("## Dispatch natively", 1)[1].split("## Gate closure", 1)[0]
        self.assertIn('`fork_turns="none"`', dispatch)
        self.assertIn("do not omit", dispatch.lower())

    def test_simple_bounded_work_stays_inline_even_when_contract_is_selected(self):
        for anchor in (
            "simple bounded outcome in the main session",
            "selection never by itself requires a child agent",
            "one bounded task or a purely mechanical check stays in the main session",
            "no independent review is required",
            "if the frozen policy requires an independent reviewer",
            "the user explicitly requests a native worker",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor.lower(), self.normalized)
        for stale in (
            "rather than producing substantive tickets yourself",
            "delegate every substantive ready ticket",
            "always spawn_agent",
            "fixed six-agent/persona procession",
        ):
            with self.subTest(stale=stale):
                self.assertNotIn(stale.lower(), self.normalized)

    def test_spawn_boundary_is_shape_based_and_uses_one_native_mechanism(self):
        for anchor in (
            "multiple substantive disjoint workstreams",
            "dependency handoffs",
            "meaningful fan-out",
            "an independent reviewer required by the frozen policy",
            "Use native `spawn_agent` only when",
            "no fixed six-stage sequence or six-agent/persona requirement",
            "separately authorized read-only external adapter",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor.lower(), self.outcome_normalized)
        self.assertIn("with `spawn_agent`", self.queue_normalized)
        self.assertNotIn("delegate every", self.queue_normalized)

    def test_functional_roles_have_consequential_boundaries(self):
        expected = {
            "explore": (
                "consequential",
                "plain factual lookup",
                "generic domain curiosity",
                "document-only analysis",
            ),
            "experiment": (
                "empirical answer",
                "pass/fail",
                "time/resource",
                "stop condition",
            ),
            "compare": (
                "viable alternatives",
                "material tradeoffs",
                "material human-owned choice",
            ),
            "implement": ("authorized chosen goal", "acceptance criteria", "diagnosis-only"),
            "review": ("available artifact", "frozen tier 0/1/2", "trivial mechanical change"),
        }
        for role, anchors in expected.items():
            for anchor in anchors:
                with self.subTest(role=role, anchor=anchor):
                    self.assertIn(anchor.lower(), self.outcome_normalized)

    def test_experiment_and_authority_boundaries_do_not_grant_external_action(self):
        for anchor in (
            "cost limit",
            "data boundary",
            "do not spend money",
            "production data",
            "paid-model test",
            "explicit authorization",
            "missing setup is a boundary",
            "do not silently select",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor.lower(), self.normalized)

    def test_frozen_review_gate_and_evidence_contract_remain_present(self):
        for anchor in (
            "review_policy",
            "tier `0`",
            "tier `1`",
            "tier `2`",
            "requirements",
            "TDD receipts",
            "fresh-context independent reviewer",
            "two review passes",
            "collective ticket ceiling of two fix rounds",
            "newly introduced findings do not reset it",
            "Never report success",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor.lower(), self.normalized)


if __name__ == "__main__":
    unittest.main()
