#!/usr/bin/env python3
"""Run one explicitly supplied test command with durable status evidence.

``start`` creates an exclusive run directory and returns after a supervisor
has acknowledged the child process.  ``status`` only reads that same run
directory; it never starts another process.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import datetime as _datetime
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = 1
DEFAULT_TIMEOUT_SECONDS = 300.0
DEFAULT_STARTUP_TIMEOUT_SECONDS = 5.0
MAX_TIMEOUT_SECONDS = 24 * 60 * 60.0
DEFAULT_EVIDENCE_ROOT = Path(tempfile.gettempdir()) / "shikigarasu-formalization-evidence"

METADATA_FILE = "metadata.json"
REQUEST_FILE = "request.json"
RESULT_FILE = "result.json"
ACK_FILE = "started.json"
STDOUT_FILE = "stdout.txt"
STDERR_FILE = "stderr.txt"

TERMINAL_STATUSES = {"passed", "failed", "timed_out"}
AGENT_LAUNCHERS = {"codex", "codex.exe", "claude", "claude.exe", "agy", "agy.exe"}


class RunnerError(RuntimeError):
    """A caller or run-directory error that is safe to report to the CLI."""


def _utc_now() -> str:
    return (
        _datetime.datetime.now(_datetime.timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _utc_after(seconds: float) -> str:
    return (
        _datetime.datetime.now(_datetime.timezone.utc)
        + _datetime.timedelta(seconds=seconds)
    ).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse_utc(value: object) -> _datetime.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = _datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=_datetime.timezone.utc)


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Write a complete JSON document and publish it with one atomic rename."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
        )
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(fd, 0o600)
        except (AttributeError, OSError):
            pass
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _process_identity(pid: object) -> str | None:
    """Return a PID-generation token; a PID by itself is never an identity."""

    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return None
    if os.name == "nt":
        return _windows_process_identity(pid)

    # Linux exposes process start ticks in /proc/<pid>/stat.  Include the
    # process id in the comparison separately; the start token prevents a
    # reused PID from being treated as the original supervisor.
    stat_path = Path("/proc") / str(pid) / "stat"
    try:
        raw = stat_path.read_text(encoding="utf-8")
    except OSError:
        return None
    closing_paren = raw.rfind(")")
    if closing_paren < 0:
        return None
    fields = raw[closing_paren + 2 :].split()
    if len(fields) <= 19:
        return None
    return f"proc-start:{fields[19]}"


def _windows_process_identity(pid: int) -> str | None:
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            return None
        try:
            creation = ctypes.wintypes.FILETIME()
            exit_time = ctypes.wintypes.FILETIME()
            kernel_time = ctypes.wintypes.FILETIME()
            user_time = ctypes.wintypes.FILETIME()
            if not kernel32.GetProcessTimes(
                handle,
                ctypes.byref(creation),
                ctypes.byref(exit_time),
                ctypes.byref(kernel_time),
                ctypes.byref(user_time),
            ):
                return None
            ticks = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
            return f"win-creation:{ticks}"
        finally:
            kernel32.CloseHandle(handle)
    except (AttributeError, OSError, ValueError):
        return None


def _supervisor_state(metadata: Mapping[str, Any]) -> str:
    pid = metadata.get("supervisor_pid")
    expected = metadata.get("supervisor_identity")
    if not isinstance(expected, str) or not expected:
        return "unknown"
    actual = _process_identity(pid)
    if actual is None:
        return "dead"
    return "alive" if actual == expected else "dead"


def _validate_timeout(value: float, name: str = "timeout") -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise RunnerError(f"{name} must be a finite positive number") from exc
    if not math.isfinite(number) or number <= 0 or number > MAX_TIMEOUT_SECONDS:
        raise RunnerError(
            f"{name} must be finite, greater than zero, and at most {MAX_TIMEOUT_SECONDS:g} seconds"
        )
    return number


def _validate_argv(argv: Sequence[str]) -> list[str]:
    if isinstance(argv, (str, bytes)):
        raise RunnerError("argv must be a sequence of arguments, not a shell string")
    values = list(argv)
    if not values or any(not isinstance(item, str) or "\x00" in item for item in values):
        raise RunnerError("an explicit non-empty argv without NUL characters is required")
    launcher = Path(values[0]).name.casefold()
    if launcher in AGENT_LAUNCHERS:
        raise RunnerError("agent launchers are not authorized test commands")
    return values


def _resolve_cwd(cwd: str | os.PathLike[str]) -> Path:
    try:
        resolved = Path(cwd).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise RunnerError(f"cwd is not a readable directory: {cwd}") from exc
    if not resolved.is_dir():
        raise RunnerError(f"cwd is not a directory: {resolved}")
    return resolved


def _new_run_directory(evidence_root: Path, requested: Path | None) -> Path:
    if requested is not None:
        candidate = requested.expanduser().resolve(strict=False)
        try:
            candidate.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise RunnerError(f"run directory already exists: {candidate}") from exc
        except OSError as exc:
            raise RunnerError(f"could not create run directory: {candidate}") from exc
        return candidate

    root = evidence_root.expanduser().resolve(strict=False)
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RunnerError(f"could not create evidence root: {root}") from exc
    for _ in range(20):
        name = "run-" + _utc_now().replace(":", "").replace("-", "") + "-" + uuid.uuid4().hex[:12]
        candidate = root / name
        try:
            candidate.mkdir(exist_ok=False)
            return candidate
        except FileExistsError:
            continue
        except OSError as exc:
            raise RunnerError(f"could not create run directory: {candidate}") from exc
    raise RunnerError("could not allocate a unique run directory")


def _paths(run_dir: Path) -> dict[str, Path]:
    return {
        "metadata": run_dir / METADATA_FILE,
        "request": run_dir / REQUEST_FILE,
        "result": run_dir / RESULT_FILE,
        "ack": run_dir / ACK_FILE,
        "stdout": run_dir / STDOUT_FILE,
        "stderr": run_dir / STDERR_FILE,
    }


def _hidden_process_options() -> dict[str, Any]:
    if os.name == "nt":
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup_info.wShowWindow = subprocess.SW_HIDE
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        return {"creationflags": flags, "startupinfo": startup_info}
    return {"start_new_session": True}


def _watch_supervisor(supervisor: subprocess.Popen[Any]) -> None:
    """Reap a detached supervisor when this caller remains alive."""

    def reap() -> None:
        try:
            supervisor.wait()
        except OSError:
            pass

    threading.Thread(target=reap, name="shikigarasu-test-supervisor", daemon=True).start()


def _metadata_for_start(
    run_dir: Path, argv: Sequence[str], cwd: Path, timeout: float
) -> dict[str, Any]:
    encoded_argv = json.dumps(list(argv), ensure_ascii=False, separators=(",", ":")).encode()
    paths = _paths(run_dir)
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_dir.name,
        "run_handle": str(run_dir),
        "handle": str(run_dir),
        "status": "starting",
        "terminal": False,
        "success": None,
        "command": argv[0],
        "argv_count": len(argv),
        "argv_sha256": hashlib.sha256(encoded_argv).hexdigest(),
        "cwd": str(cwd),
        "timeout_seconds": timeout,
        "started_at": None,
        "deadline_at": None,
        "ended_at": None,
        "exit_status": None,
        "pid": None,
        "pid_identity": None,
        "supervisor_pid": None,
        "supervisor_identity": None,
        "metadata_path": str(paths["metadata"]),
        "result_path": str(paths["result"]),
        "stdout_path": str(paths["stdout"]),
        "stderr_path": str(paths["stderr"]),
    }


def _uncertain(run_dir: Path, metadata: Mapping[str, Any] | None, reason: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_handle": str(run_dir),
        "run_id": metadata.get("run_id", run_dir.name) if metadata else run_dir.name,
        "status": "uncertain",
        "terminal": False,
        "success": None,
        "reason": reason,
    }
    if metadata:
        for key in (
            "command",
            "argv_count",
            "argv_sha256",
            "cwd",
            "timeout_seconds",
            "started_at",
            "deadline_at",
            "pid",
            "pid_identity",
            "supervisor_pid",
            "supervisor_identity",
            "metadata_path",
            "result_path",
            "stdout_path",
            "stderr_path",
        ):
            if key in metadata:
                result[key] = metadata[key]
    return result


def _status_from_result(run_dir: Path, metadata: Mapping[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "run_id",
        "status",
        "terminal",
        "success",
        "started_at",
        "ended_at",
        "exit_status",
        "exit_code",
        "timed_out",
        "supervisor_pid",
        "supervisor_identity",
    }
    if not required.issubset(result):
        return _uncertain(run_dir, metadata, "result-fields-missing")
    if result.get("schema_version") != SCHEMA_VERSION:
        return _uncertain(run_dir, metadata, "result-schema-mismatch")
    if result.get("run_id") != metadata.get("run_id"):
        return _uncertain(run_dir, metadata, "result-run-id-mismatch")
    if result.get("run_handle") != metadata.get("run_handle", str(run_dir)):
        return _uncertain(run_dir, metadata, "result-run-handle-mismatch")
    if result.get("status") not in TERMINAL_STATUSES or result.get("terminal") is not True:
        return _uncertain(run_dir, metadata, "invalid-terminal-result")
    status = result["status"]
    if not isinstance(result.get("success"), bool) or result["success"] != (status == "passed"):
        return _uncertain(run_dir, metadata, "result-success-mismatch")
    if not isinstance(result.get("timed_out"), bool) or result["timed_out"] != (status == "timed_out"):
        return _uncertain(run_dir, metadata, "result-timeout-mismatch")
    if _parse_utc(result.get("started_at")) is None or _parse_utc(result.get("ended_at")) is None:
        return _uncertain(run_dir, metadata, "result-timestamps-invalid")
    supervisor_pid = result.get("supervisor_pid")
    if not isinstance(supervisor_pid, int) or isinstance(supervisor_pid, bool) or supervisor_pid <= 0:
        return _uncertain(run_dir, metadata, "result-supervisor-invalid")
    if not isinstance(result.get("supervisor_identity"), str) or not result["supervisor_identity"]:
        return _uncertain(run_dir, metadata, "result-supervisor-identity-missing")
    exit_status = result.get("exit_status")
    if exit_status is not None and (
        not isinstance(exit_status, int) or isinstance(exit_status, bool)
    ):
        return _uncertain(run_dir, metadata, "result-exit-status-invalid")
    if result.get("exit_code") != exit_status:
        return _uncertain(run_dir, metadata, "result-exit-code-mismatch")
    if status == "passed" and exit_status != 0:
        return _uncertain(run_dir, metadata, "passed-result-exit-status-mismatch")
    if status == "failed" and exit_status == 0:
        return _uncertain(run_dir, metadata, "failed-result-exit-status-mismatch")
    if status == "failed" and exit_status is None and not result.get("error"):
        return _uncertain(run_dir, metadata, "failed-result-exit-status-missing")
    for key in ("pid", "pid_identity", "supervisor_pid", "supervisor_identity"):
        if key in metadata and result.get(key) != metadata.get(key):
            return _uncertain(run_dir, metadata, f"result-{key}-mismatch")
    if result.get("pid") is not None and not result.get("pid_identity"):
        return _uncertain(run_dir, metadata, "result-pid-identity-missing")
    output = dict(result)
    output.setdefault("schema_version", SCHEMA_VERSION)
    output.setdefault("run_handle", str(run_dir))
    output.setdefault("handle", str(run_dir))
    output.setdefault("run_id", metadata.get("run_id", run_dir.name))
    output["terminal"] = True
    output["success"] = status == "passed"
    output.setdefault("metadata_path", str(_paths(run_dir)["metadata"]))
    output.setdefault("result_path", str(_paths(run_dir)["result"]))
    output.setdefault("stdout_path", str(_paths(run_dir)["stdout"]))
    output.setdefault("stderr_path", str(_paths(run_dir)["stderr"]))
    return output


def status_run(run_handle: str | os.PathLike[str]) -> dict[str, Any]:
    """Read the durable state for one run without launching or relaunching it."""

    run_dir = Path(run_handle).expanduser().resolve(strict=False)
    if not run_dir.exists() or not run_dir.is_dir():
        raise RunnerError(f"run handle is not an existing directory: {run_dir}")
    paths = _paths(run_dir)
    metadata = _read_json(paths["metadata"])
    if metadata is None:
        return _uncertain(run_dir, None, "metadata-missing-or-invalid")

    durable_result = _read_json(paths["result"])
    if durable_result is not None:
        return _status_from_result(run_dir, metadata, durable_result)
    if paths["result"].exists():
        return _uncertain(run_dir, metadata, "result-invalid")

    supervisor_state = _supervisor_state(metadata)
    if supervisor_state != "alive":
        reason = (
            "supervisor-identity-unavailable"
            if supervisor_state == "unknown"
            else "supervisor-dead-before-result"
        )
        return _uncertain(run_dir, metadata, reason)

    deadline = _parse_utc(metadata.get("deadline_at"))
    if deadline is not None and _datetime.datetime.now(_datetime.timezone.utc) >= deadline:
        return _uncertain(run_dir, metadata, "deadline-passed-without-result")

    output = dict(metadata)
    output["status"] = "running"
    output["terminal"] = False
    output["success"] = None
    output["handle"] = str(run_dir)
    output["supervisor_alive"] = True
    return output


def _write_terminal_result(
    run_dir: Path,
    metadata: Mapping[str, Any],
    *,
    status: str,
    exit_status: int | None,
    started_at: str,
    ended_at: str,
    pid: int | None,
    pid_identity: str | None,
    supervisor_pid: int,
    supervisor_identity: str | None,
    timed_out: bool,
    error: str | None = None,
) -> None:
    duration = max(0.0, (_parse_utc(ended_at) - _parse_utc(started_at)).total_seconds())
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": metadata.get("run_id", run_dir.name),
        "run_handle": str(run_dir),
        "status": status,
        "terminal": True,
        "success": status == "passed",
        "scope": "direct-child",
        "descendants_may_survive": True,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": duration,
        "exit_status": exit_status,
        "exit_code": exit_status,
        "timed_out": timed_out,
        "pid": pid,
        "pid_identity": pid_identity,
        "supervisor_pid": supervisor_pid,
        "supervisor_identity": supervisor_identity,
        "metadata_path": str(_paths(run_dir)["metadata"]),
        "result_path": str(_paths(run_dir)["result"]),
        "stdout_path": str(_paths(run_dir)["stdout"]),
        "stderr_path": str(_paths(run_dir)["stderr"]),
    }
    if error:
        result["error"] = error
    final_metadata = dict(metadata)
    final_metadata.update(
        {
            "status": status,
            "terminal": True,
            "success": status == "passed",
            "scope": "direct-child",
            "descendants_may_survive": True,
            "started_at": started_at,
            "ended_at": ended_at,
            "exit_status": exit_status,
            "pid": pid,
            "pid_identity": pid_identity,
            "supervisor_pid": supervisor_pid,
            "supervisor_identity": supervisor_identity,
        }
    )
    if error:
        final_metadata["error"] = error
    _atomic_write_json(_paths(run_dir)["metadata"], final_metadata)
    # Publish the terminal marker only after its lifecycle metadata is durable.
    _atomic_write_json(_paths(run_dir)["result"], result)


def _supervise(run_dir: Path) -> int:
    paths = _paths(run_dir)
    metadata = _read_json(paths["metadata"])
    if metadata is None:
        return 2
    request = _read_json(paths["request"])
    argv = request.get("argv") if request else None
    if not isinstance(argv, list):
        return 2
    try:
        validated_argv = _validate_argv(argv)
        cwd = _resolve_cwd(str(metadata.get("cwd", "")))
        timeout = _validate_timeout(metadata.get("timeout_seconds"))
    except RunnerError:
        return 2

    supervisor_pid = os.getpid()
    supervisor_identity = _process_identity(supervisor_pid)
    started_at = _utc_now()
    deadline_at = _utc_after(timeout)
    child: subprocess.Popen[bytes] | None = None
    child_identity: str | None = None
    exit_status: int | None = None
    timed_out = False
    error: str | None = None

    paths["stdout"].touch(exist_ok=True)
    paths["stderr"].touch(exist_ok=True)
    try:
        with paths["stdout"].open("wb") as stdout_stream, paths["stderr"].open("wb") as stderr_stream:
            child = subprocess.Popen(
                validated_argv,
                cwd=str(cwd),
                stdin=subprocess.DEVNULL,
                stdout=stdout_stream,
                stderr=stderr_stream,
                shell=False,
                **_hidden_process_options(),
            )
            child_identity = _process_identity(child.pid)
            running_metadata = dict(metadata)
            running_metadata.update(
                {
                    "status": "running",
                    "terminal": False,
                    "started_at": started_at,
                    "deadline_at": deadline_at,
                    "pid": child.pid,
                    "pid_identity": child_identity,
                    "supervisor_pid": supervisor_pid,
                    "supervisor_identity": supervisor_identity,
                }
            )
            _atomic_write_json(paths["metadata"], running_metadata)
            _atomic_write_json(
                paths["ack"],
                {
                    "schema_version": SCHEMA_VERSION,
                    "run_id": metadata.get("run_id", run_dir.name),
                    "status": "started",
                    "pid": child.pid,
                    "pid_identity": child_identity,
                    "supervisor_pid": supervisor_pid,
                    "supervisor_identity": supervisor_identity,
                    "started_at": started_at,
                    "deadline_at": deadline_at,
                },
            )
            try:
                exit_status = child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    child.kill()
                except OSError:
                    pass
                try:
                    exit_status = child.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    exit_status = None
    except (OSError, ValueError) as exc:
        error = f"{type(exc).__name__}: {exc}"

    ended_at = _utc_now()
    if child is None:
        _write_terminal_result(
            run_dir,
            metadata,
            status="failed",
            exit_status=None,
            started_at=started_at,
            ended_at=ended_at,
            pid=None,
            pid_identity=None,
            supervisor_pid=supervisor_pid,
            supervisor_identity=supervisor_identity,
            timed_out=False,
            error=error or "test process could not be started",
        )
        _atomic_write_json(
            paths["ack"],
            {
                "schema_version": SCHEMA_VERSION,
                "run_id": metadata.get("run_id", run_dir.name),
                "status": "failed",
                "error": error or "test process could not be started",
            },
        )
        return 1

    status = "timed_out" if timed_out else ("passed" if exit_status == 0 else "failed")
    _write_terminal_result(
        run_dir,
        metadata,
        status=status,
        exit_status=exit_status,
        started_at=started_at,
        ended_at=ended_at,
        pid=child.pid,
        pid_identity=child_identity,
        supervisor_pid=supervisor_pid,
        supervisor_identity=supervisor_identity,
        timed_out=timed_out,
        error=error,
    )
    return 0 if status == "passed" else 1


def start_run(
    argv: Sequence[str],
    *,
    cwd: str | os.PathLike[str],
    evidence_root: str | os.PathLike[str] | None = None,
    run_dir: str | os.PathLike[str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    startup_timeout: float = DEFAULT_STARTUP_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Start one bounded run and return its durable handle after acknowledgement."""

    validated_argv = _validate_argv(argv)
    resolved_cwd = _resolve_cwd(cwd)
    bounded_timeout = _validate_timeout(timeout)
    bounded_startup_timeout = _validate_timeout(startup_timeout, "startup-timeout")
    root = Path(evidence_root) if evidence_root is not None else DEFAULT_EVIDENCE_ROOT
    requested_dir = Path(run_dir) if run_dir is not None else None
    allocated_dir = _new_run_directory(root, requested_dir)
    paths = _paths(allocated_dir)
    metadata = _metadata_for_start(allocated_dir, validated_argv, resolved_cwd, bounded_timeout)
    _atomic_write_json(paths["request"], {"schema_version": SCHEMA_VERSION, "argv": validated_argv})
    _atomic_write_json(paths["metadata"], metadata)

    supervisor_argv = [
        sys.executable,
        str(Path(__file__).resolve()),
        "_supervise",
        str(allocated_dir),
    ]
    try:
        supervisor = subprocess.Popen(
            supervisor_argv,
            cwd=str(resolved_cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            **_hidden_process_options(),
        )
    except (OSError, ValueError) as exc:
        error = f"{type(exc).__name__}: {exc}"
        failed_metadata = dict(metadata)
        failed_metadata.update(
            {
                "status": "uncertain",
                "reason": "supervisor-start-failed",
                "error": error,
            }
        )
        try:
            _atomic_write_json(paths["metadata"], failed_metadata)
        except OSError:
            pass
        output = _uncertain(allocated_dir, failed_metadata, "supervisor-start-failed")
        output["error"] = error
        return output

    wait_deadline = time.monotonic() + bounded_startup_timeout
    while time.monotonic() < wait_deadline:
        ack = _read_json(paths["ack"])
        if ack and ack.get("run_id") in (metadata["run_id"], allocated_dir.name):
            if ack.get("status") == "started":
                _watch_supervisor(supervisor)
                return {
                    "schema_version": SCHEMA_VERSION,
                    "status": "started",
                    "terminal": False,
                    "success": None,
                    "run_id": metadata["run_id"],
                    "run_handle": str(allocated_dir),
                    "handle": str(allocated_dir),
                    "metadata_path": str(paths["metadata"]),
                    "result_path": str(paths["result"]),
                    "stdout_path": str(paths["stdout"]),
                    "stderr_path": str(paths["stderr"]),
                    "pid": ack.get("pid"),
                    "supervisor_pid": ack.get("supervisor_pid"),
                    "started_at": ack.get("started_at"),
                    "deadline_at": ack.get("deadline_at"),
                }
            if ack.get("status") == "failed":
                _watch_supervisor(supervisor)
                return status_run(allocated_dir)
        if supervisor.poll() is not None:
            current = status_run(allocated_dir)
            if current.get("terminal"):
                _watch_supervisor(supervisor)
                return current
            _watch_supervisor(supervisor)
            return _uncertain(allocated_dir, _read_json(paths["metadata"]), "supervisor-exited-before-ack")
        time.sleep(0.01)

    _watch_supervisor(supervisor)
    return _uncertain(allocated_dir, _read_json(paths["metadata"]), "startup-ack-timeout")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="start one explicit bounded test command")
    start.add_argument("--cwd", required=True, type=Path, help="explicit test working directory")
    start.add_argument(
        "--evidence-root",
        "--run-root",
        dest="evidence_root",
        type=Path,
        default=DEFAULT_EVIDENCE_ROOT,
        help="directory under which a unique run directory is created",
    )
    start.add_argument("--run-dir", type=Path, help="exclusive run directory (normally omit)")
    start.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    start.add_argument("--startup-timeout", type=float, default=DEFAULT_STARTUP_TIMEOUT_SECONDS)
    start.add_argument("argv", nargs=argparse.REMAINDER, help="command and arguments after `--`")

    status = subparsers.add_parser("status", help="read one run handle without relaunching it")
    status.add_argument("run_handle", type=Path)

    supervisor = subparsers.add_parser("_supervise", help=argparse.SUPPRESS)
    supervisor.add_argument("run_dir", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "_supervise":
            return _supervise(args.run_dir.expanduser().resolve(strict=False))
        if args.command == "start":
            command = list(args.argv)
            if command and command[0] == "--":
                command = command[1:]
            output = start_run(
                command,
                cwd=args.cwd,
                evidence_root=args.evidence_root,
                run_dir=args.run_dir,
                timeout=args.timeout,
                startup_timeout=args.startup_timeout,
            )
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 0 if output.get("status") == "started" else 2
        output = status_run(args.run_handle)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except RunnerError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
