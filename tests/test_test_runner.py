import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "codex" / "skills" / "shikigarasu" / "scripts" / "test_runner.py"
SPEC = importlib.util.spec_from_file_location("shikigarasu_test_runner", MODULE_PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(RUNNER)


def child_code(source: str) -> list[str]:
    return [sys.executable, "-c", source]


def wait_for_terminal(handle: Path, timeout: float = 8.0) -> dict:
    deadline = time.monotonic() + timeout
    latest = {}
    while time.monotonic() < deadline:
        latest = RUNNER.status_run(handle)
        if latest.get("terminal"):
            supervisor_pid = latest.get("supervisor_pid")
            supervisor_deadline = time.monotonic() + 2
            while supervisor_pid and time.monotonic() < supervisor_deadline:
                if RUNNER._process_identity(supervisor_pid) is None:
                    break
                time.sleep(0.02)
            return latest
        time.sleep(0.03)
    raise AssertionError(f"run did not reach a terminal result: {latest}")


class DurableTestRunnerTests(unittest.TestCase):
    def test_success_captures_stdout_and_persists_terminal_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            started = RUNNER.start_run(
                child_code("print('runner-ok')"),
                cwd=root,
                evidence_root=root / "evidence",
                timeout=3,
            )

            self.assertEqual("started", started["status"])
            result = wait_for_terminal(Path(started["run_handle"]))

            self.assertEqual("passed", result["status"])
            self.assertEqual(0, result["exit_status"])
            self.assertTrue(result["success"])
            run_dir = Path(started["run_handle"])
            self.assertEqual("runner-ok\n", (run_dir / "stdout.txt").read_text())
            metadata = json.loads((run_dir / "metadata.json").read_text())
            self.assertEqual(0, metadata["exit_status"])
            self.assertEqual(sys.executable, metadata["command"])
            self.assertEqual(len(child_code("print('runner-ok')")), metadata["argv_count"])
            self.assertNotIn("env", metadata)

    def test_nonzero_exit_captures_stderr_and_is_not_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            started = RUNNER.start_run(
                child_code("import sys; print('bad', file=sys.stderr); sys.exit(7)"),
                cwd=root,
                evidence_root=root / "evidence",
                timeout=3,
            )

            result = wait_for_terminal(Path(started["run_handle"]))

            self.assertEqual("failed", result["status"])
            self.assertEqual(7, result["exit_status"])
            self.assertFalse(result["success"])
            run_dir = Path(started["run_handle"])
            self.assertEqual("bad\n", (run_dir / "stderr.txt").read_text())

    def test_start_returns_before_delayed_child_finishes_and_status_polls_same_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            release = root / "release-child"
            started = RUNNER.start_run(
                child_code(
                    "import pathlib, time; "
                    f"release = pathlib.Path({str(release)!r})\n"
                    "while not release.exists(): time.sleep(0.02)\n"
                    "print('later')"
                ),
                cwd=root,
                evidence_root=root / "evidence",
                timeout=10,
            )
            handle = Path(started["run_handle"])
            try:
                # The child cannot finish until this caller releases it. This
                # tests ordering, not machine-dependent Python startup speed.
                self.assertEqual("started", started["status"])
                first = RUNNER.status_run(handle)
                self.assertFalse(first["terminal"])
                self.assertEqual("running", first["status"])
            finally:
                # Drain the same run even when an assertion fails, before the
                # temporary directory tries to remove its open log files.
                release.touch()
                result = wait_for_terminal(handle, timeout=15)
            self.assertEqual("passed", result["status"])
            self.assertEqual("later\n", (handle / "stdout.txt").read_text())

    def test_existing_run_directory_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            evidence = root / "evidence"
            evidence.mkdir()
            collision = evidence / "fixed-run"
            collision.mkdir()
            marker = collision / "marker.txt"
            marker.write_text("keep")

            with self.assertRaises(RUNNER.RunnerError):
                RUNNER.start_run(
                    child_code("print('must not run')"),
                    cwd=root,
                    evidence_root=evidence,
                    run_dir=collision,
                    timeout=3,
                )

            self.assertEqual("keep", marker.read_text())
            self.assertFalse((collision / "metadata.json").exists())

    def test_timeout_is_bounded_and_persisted_as_non_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            started = RUNNER.start_run(
                child_code("import time; time.sleep(30)"),
                cwd=root,
                evidence_root=root / "evidence",
                timeout=0.2,
            )
            result = wait_for_terminal(Path(started["run_handle"]), timeout=4)

            self.assertEqual("timed_out", result["status"])
            self.assertFalse(result["success"])
            self.assertTrue(result["timed_out"])
            self.assertLess(result["duration_seconds"], 3)

    def test_missing_result_with_dead_supervisor_is_uncertain(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "run"
            run_dir.mkdir()
            metadata = {
                "schema_version": 1,
                "run_id": "uncertain-run",
                "run_handle": str(run_dir),
                "status": "running",
                "terminal": False,
                "supervisor_pid": os.getpid(),
                "supervisor_identity": "not-this-process",
                "pid": os.getpid(),
                "pid_identity": "not-this-process",
                "result_path": str(run_dir / "result.json"),
            }
            (run_dir / "metadata.json").write_text(json.dumps(metadata))

            result = RUNNER.status_run(run_dir)

            self.assertEqual("uncertain", result["status"])
            self.assertFalse(result["success"])
            self.assertIn("supervisor", result["reason"])

    def test_corrupt_passed_result_is_uncertain_not_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "run"
            run_dir.mkdir()
            metadata = {
                "schema_version": 1,
                "run_id": run_dir.name,
                "run_handle": str(run_dir),
                "status": "running",
                "terminal": False,
                "supervisor_pid": os.getpid(),
                "supervisor_identity": RUNNER._process_identity(os.getpid()),
            }
            (run_dir / "metadata.json").write_text(json.dumps(metadata))
            (run_dir / "result.json").write_text(
                json.dumps({"status": "passed", "terminal": True})
            )

            result = RUNNER.status_run(run_dir)

            self.assertEqual("uncertain", result["status"])
            self.assertIsNone(result["success"])

    def test_exit_code_alias_mismatch_is_uncertain(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            started = RUNNER.start_run(
                child_code("print('valid')"),
                cwd=root,
                evidence_root=root / "evidence",
                timeout=3,
            )
            handle = Path(started["run_handle"])
            result = wait_for_terminal(handle)
            result_payload = json.loads((handle / "result.json").read_text())
            result_payload["exit_code"] = 99
            (handle / "result.json").write_text(json.dumps(result_payload))

            state = RUNNER.status_run(handle)

            self.assertEqual("uncertain", state["status"])
            self.assertIsNone(state["success"])

    def test_supervisor_start_failure_returns_allocated_handle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with mock.patch.object(
                RUNNER.subprocess, "Popen", side_effect=OSError("supervisor unavailable")
            ):
                started = RUNNER.start_run(
                    child_code("print('must not run')"),
                    cwd=root,
                    evidence_root=root / "evidence",
                    timeout=3,
                )

            self.assertEqual("uncertain", started["status"])
            self.assertIn("supervisor", started["reason"])
            self.assertTrue(Path(started["run_handle"]).is_dir())
            self.assertIn("unavailable", started["error"])

    def test_supervisor_watcher_reaps_launcher_process(self):
        waited = threading.Event()
        supervisor = mock.Mock()
        supervisor.wait.side_effect = lambda: waited.set()

        RUNNER._watch_supervisor(supervisor)

        self.assertTrue(waited.wait(1))
        supervisor.wait.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
