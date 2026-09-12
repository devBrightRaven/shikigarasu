"""Static routing contracts and a reusable native-host acceptance fixture.

The static checks below validate source boundaries only.  They deliberately do
not pretend that a phrase or regex proves Claude selected an agent.  The JSON
fixture is for a separate native-host run that records actual Agent/tool calls
and availability disclosures.
"""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "axis-routing-host-acceptance.json"
DISPATCH = ROOT / "rules" / "common" / "shikigarasu-dispatch.md"

AXIS_FILES = {
    "shuen": [ROOT / "agents" / "shuen.md", ROOT / "commands" / "shuen.md", ROOT / "skills" / "shuen.md"],
    "seiran": [ROOT / "agents" / "seiran.md", ROOT / "commands" / "seiran.md", ROOT / "skills" / "seiran.md"],
    "genen": [ROOT / "agents" / "genen.md", ROOT / "commands" / "genen.md", ROOT / "skills" / "genen.md"],
    "hakuso": [ROOT / "agents" / "hakuso.md", ROOT / "commands" / "hakuso.md", ROOT / "skills" / "hakuso.md"],
}

ROLE_AGENT_FILES = {
    "kishi": [ROOT / "agents" / "kishi.md"],
    "soen": [ROOT / "agents" / "soen.md"],
}

ROUTABLE_ROLES = {**AXIS_FILES, **ROLE_AGENT_FILES}


class StaticAxisRoutingContractTests(unittest.TestCase):
    """Static source checks; these are not automatic-routing evidence."""

    def test_each_agent_command_and_skill_surface_states_its_boundary(self):
        required = {
            "shuen": ("concrete", "consequential", "blind spot"),
            "seiran": ("existing", "viable", "material tradeoff"),
            "genen": ("authorized", "acceptance", "diagnosis-only"),
            "hakuso": ("available artifact", "requirements", "trivial"),
        }
        for axis, paths in AXIS_FILES.items():
            for path in paths:
                text = path.read_text(encoding="utf-8").lower()
                missing = [anchor for anchor in required[axis] if anchor not in text]
                with self.subTest(axis=axis, surface=path.name):
                    self.assertEqual([], missing, f"{path}: missing semantic anchors {missing}")

    def test_role_mention_alone_is_not_activation(self):
        for axis, paths in AXIS_FILES.items():
            for path in paths:
                flat = " ".join(path.read_text(encoding="utf-8").lower().split())
                with self.subTest(axis=axis, surface=path.name):
                    self.assertNotIn("or explicitly mentions", flat)
        seiran_skill = " ".join((ROOT / "skills" / "seiran.md").read_text(encoding="utf-8").lower().split())
        self.assertIn("bare mention of a role name or of shikigarasu is not activation", seiran_skill)

    def test_worker_handoffs_are_conditional_and_coordinator_owned(self):
        for axis, paths in AXIS_FILES.items():
            text = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()
            with self.subTest(axis=axis):
                self.assertIn("coordinator", text)
                self.assertIn("do not dispatch", text)
                self.assertNotIn("mandatory audit handoff", text)
                self.assertNotIn("default handoff", text)

    def test_kishi_and_soen_source_contracts_are_outcome_shaped(self):
        kishi = ROLE_AGENT_FILES["kishi"][0].read_text(encoding="utf-8").lower()
        for anchor in (
            "authorized outcome",
            "multiple substantive roles",
            "magic keyword",
            "six-axis procession",
            "explicitly asks to",
            "agent tool",
            "shikigarasu-common",
            "two independent review passes",
            "including when the first pass is clean",
            "gate 0 authorization",
            "raw evidence",
            "human-owned material choice",
            "new cost",
        ):
            with self.subTest(role="kishi", anchor=anchor):
                self.assertIn(anchor, kishi)
        self.assertNotIn("a clean first pass on low-risk local work closes", kishi)

        soen = ROLE_AGENT_FILES["soen"][0].read_text(encoding="utf-8").lower()
        for anchor in (
            "authorized outcome",
            "empirical evidence",
            "plain factual lookup",
            "domain curiosity",
            "document-only analysis",
            "perfect hypothesis",
            "pass/fail",
            "time/resource bound",
            "stop condition",
            "production data",
            "gate 0 authorization",
            "open-ended exploration",
            "never delete raw research evidence automatically",
            "another routine confirmation turn",
            "raw evidence is retained",
        ):
            with self.subTest(role="soen", anchor=anchor):
                self.assertIn(anchor, soen)
        self.assertNotIn('triggers on "research"', soen)
        self.assertNotIn("document every experiment in 實驗設計 as a **proof of life (pol) probe**", soen)
        self.assertNotIn("dispose all fit the declared timeline", soen)

    def test_dispatch_guard_is_per_axis_and_does_not_fake_unavailable_calls(self):
        text = DISPATCH.read_text(encoding="utf-8")
        self.assertNotIn("active only if kishi is installed", text.lower())
        for anchor in (
            "single axis",
            "selected axis",
            "do not simulate a call",
            "An absent Kishi must not disable an available single axis",
            "outcome-shaped",
            "keyword/persona requirement",
            "does not by itself require a subagent or the coordinator",
            "stated observable acceptance criterion",
            "routes to genen even when it looks small",
            "explicit user override, not an inferred",
            "explicitly inline",
            "interactive main session applies the",
            "no fixed six-axis sequence",
            "plain factual lookup",
            "Domain curiosity",
            "document-only analysis",
            "pass/fail",
            "stop condition",
            "diagnosis-only",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, text)


class HostBehavioralAcceptanceFixtureTests(unittest.TestCase):
    """Validate coverage and separation, not native host routing behavior."""

    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.inputs = {case["id"]: case for case in cls.fixture["inputs"]}
        cls.expected = cls.fixture["expected_observable_calls"]

    def test_fixture_is_explicitly_for_native_host_observation(self):
        self.assertEqual("native-host-routing-acceptance", self.fixture["kind"])
        self.assertEqual("static-only", self.fixture["source_acceptance_scope"])
        self.assertFalse(self.fixture["executable_in_this_repo"])
        self.assertTrue(any("explicitly load" in item for item in self.fixture["host_preconditions"]))
        self.assertIn("native Claude host", self.fixture["verification"]["runner"])
        self.assertIn("regular-expression checks", self.fixture["verification"]["not_proven_by"])
        self.assertEqual(set(self.inputs), set(self.expected))

    def test_each_axis_has_positive_and_negative_case_without_answer_in_input(self):
        for axis in ROUTABLE_ROLES:
            cases = [case for case in self.inputs.values() if case["role_under_test"] == axis]
            self.assertTrue(any(case["kind"] == "positive" for case in cases), axis)
            self.assertTrue(any(case["kind"] == "negative" for case in cases), axis)
            for case in cases:
                calls = self.expected[case["id"]]["dispatch"]
                if case["kind"] == "negative":
                    self.assertNotIn(axis, calls, case["id"])
                self.assertNotIn(f"{axis} agent", case["prompt"].lower())

    def test_kishi_host_mode_is_explicit_and_soen_positive_has_real_setup(self):
        kishi = self.inputs["kishi-positive-multi-axis-no-keyword"]
        kishi_expected = self.expected[kishi["id"]]
        self.assertEqual("interactive_main", kishi["host_mode"])
        self.assertTrue(kishi["host_setup"]["required"])
        self.assertEqual("host-provided", kishi["host_setup"]["status"])
        self.assertNotEqual("", kishi["host_setup"]["precondition"])
        self.assertNotEqual("", kishi["host_setup"]["human_checkpoint"])
        self.assertEqual(
            ["interactive_main"],
            kishi_expected["coordinator"]["acceptable_modes"],
        )
        self.assertEqual("interactive_main", kishi_expected["coordinator"]["host_mode"])
        self.assertEqual([], kishi_expected["coordinator"]["nested_coordinator_calls"])
        self.assertEqual(
            {"shuen", "soen", "seiran"},
            set(kishi_expected["coordinator"]["worker_calls"]),
        )
        self.assertIn("not a fixed six-axis sequence", kishi_expected["coordinator"]["worker_order"])
        self.assertIn("before any Genen dispatch", kishi_expected["coordinator"]["human_checkpoint"])

        kishi_negative = self.inputs["kishi-negative-single-axis-inline"]
        self.assertEqual([], self.expected[kishi_negative["id"]]["dispatch"])
        self.assertFalse(self.expected[kishi_negative["id"]]["coordinator"]["required"])
        self.assertEqual([], self.expected[kishi_negative["id"]]["coordinator"]["nested_coordinator_calls"])

        soen = self.inputs["soen-positive-empirical-without-keyword"]
        self.assertTrue(soen["host_setup"]["required"])
        self.assertEqual("host-provided", soen["host_setup"]["status"])
        self.assertNotEqual("", soen["host_setup"]["precondition"])
        self.assertNotEqual("", soen["host_setup"]["human_checkpoint"])
        self.assertIn("preflight", soen["host_setup"]["human_checkpoint"])
        self.assertIn("No additional user confirmation", soen["host_setup"]["human_checkpoint"])
        self.assertEqual(["soen"], self.expected[soen["id"]]["dispatch"])
        self.assertNotIn("benchmark", soen["prompt"].lower())
        self.assertNotIn("experiment", soen["prompt"].lower())

    def test_cross_axis_and_no_agent_controls_are_present(self):
        cross = self.inputs["cross-explicit-investigate-test-decide-build"]
        cross_expected = self.expected[cross["id"]]
        self.assertTrue(any(case["kind"] == "cross" for case in self.inputs.values()))
        self.assertEqual(
            ["interactive_main", "kishi_agent"],
            cross_expected["coordinator"]["acceptable_modes"],
        )
        self.assertEqual(
            {"shuen", "soen", "seiran"},
            set(cross_expected["coordinator"]["worker_calls"]),
        )
        self.assertIn("not a fixed six-axis sequence", cross_expected["coordinator"]["worker_order"])
        self.assertIn("human_checkpoint", cross_expected["coordinator"])
        self.assertIn("before any Genen dispatch", cross_expected["coordinator"]["human_checkpoint"])
        stubs = cross["host_setup"]["stub_outputs"]
        self.assertEqual({"shuen", "soen", "seiran"}, set(stubs))
        self.assertIsNone(stubs["seiran"]["selected_provider"])
        self.assertTrue(any(case["kind"] == "control" for case in self.inputs.values()))
        trivial = self.inputs["trivial-no-agent"]
        self.assertEqual([], self.expected[trivial["id"]]["dispatch"])

    def test_availability_cases_separate_missing_agent_disclosure_from_dispatch(self):
        no_kishi = self.inputs["single-axis-without-kishi"]
        self.assertFalse(no_kishi["kishi_available"])
        self.assertEqual(["seiran"], self.expected[no_kishi["id"]]["dispatch"])

        unavailable = self.inputs["unavailable-selected-soen"]
        self.assertNotIn("soen", unavailable["available_axes"])
        expected = self.expected[unavailable["id"]]
        self.assertEqual([], expected["dispatch"])
        self.assertEqual(["soen"], expected["disclose_unavailable"])

    def test_artifact_roles_state_host_setup_prerequisites(self):
        for case_id in (
            "genen-positive-authorized-goal",
            "hakuso-positive-artifact-review",
            "hakuso-negative-trivial-edit",
            "kishi-positive-multi-axis-no-keyword",
            "kishi-negative-single-axis-inline",
            "soen-positive-empirical-without-keyword",
        ):
            case = self.inputs[case_id]
            self.assertTrue(case["host_setup"]["required"])
            self.assertEqual("host-provided", case["host_setup"]["status"])
            self.assertNotEqual("", case["host_setup"]["precondition"])

        trivial_expected = self.expected["hakuso-negative-trivial-edit"]
        self.assertEqual([], trivial_expected["dispatch"])
        self.assertNotIn("hakuso", trivial_expected["dispatch"])


if __name__ == "__main__":
    unittest.main()
