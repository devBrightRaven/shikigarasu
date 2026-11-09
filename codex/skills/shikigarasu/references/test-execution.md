# Durable bounded test execution

Use `codex/skills/shikigarasu/scripts/test_runner.py` (from the checkout root)
when a test command may outlive the current tool call. The coordinator remains
the single execution owner: provide one
explicit, already-authorized test command and poll the returned handle. The
runner does not discover tests, dispatch agents, or launch `codex`, `claude`,
or `agy`.

## CLI

Start a run (the `--` separator is required before the command argv):

```text
python codex/skills/shikigarasu/scripts/test_runner.py start --cwd . --evidence-root ./test-evidence --timeout 180 -- python -B -X utf8 tests/test_test_runner.py
```

The example is one line so it works in both a POSIX shell and PowerShell;
quote paths or argv values according to the shell in use.

`--cwd` must name an existing directory. `--evidence-root` is optional and
defaults to the OS temporary directory's
`shikigarasu-formalization-evidence` folder. The runner creates a new
`run-<timestamp>-<uuid>` directory with an exclusive `mkdir`; it never
overwrites an existing run directory. `--run-dir` is available for tests that
need to exercise collision handling, and is also exclusive.

The start command prints JSON and returns after a supervisor has persisted a
startup acknowledgement, normally well before the test finishes:

```json
{
  "status": "started",
  "terminal": false,
  "run_handle": "<evidence-root>/run-<timestamp>-<uuid>"
}
```

Poll the same handle; this command is read-only and never relaunches anything:

```text
python codex/skills/shikigarasu/scripts/test_runner.py status <run-handle>
```

The status JSON uses these states:

- `running`: the supervisor's PID and process-generation identity still
  match, and no terminal result is published.
- `passed`: a complete persisted result reports exit status `0`.
- `failed`: the command exited nonzero or could not be started.
- `timed_out`: the supervisor reached the configured deadline, killed the
  direct child, and persisted the timeout result. This is only a direct-child
  result, not proof that a process tree has stopped.
- `uncertain`: the result is missing/invalid, the supervisor is dead, its
  identity cannot be verified, or its deadline passed without a result. This
  state has `success: null`; it must never be treated as a pass.

The run handle is not a success signal. Inspect `status`, `terminal`,
`success`, and `exit_status` in the terminal result. A valid `status` command
returns process exit code `0` so callers can inspect failed and uncertain
results; the JSON state is authoritative for the run outcome.

## Evidence files and boundaries

Each run directory contains:

- `metadata.json`: atomic lifecycle metadata including `pid`,
  `pid_identity`, `supervisor_pid`, `supervisor_identity`, `started_at`,
  `ended_at`, `timeout_seconds`, and `exit_status`;
- `request.json`: the exact argv needed by the supervisor (no environment
  snapshot is written);
- `started.json`: the atomic startup acknowledgement;
- `stdout.txt` and `stderr.txt`: captured direct-child output;
- `result.json`: the atomic terminal result.

All JSON publication uses a temporary file followed by `os.replace`. Final
lifecycle metadata is written before
`result.json` is published. Metadata alone cannot establish completion; if
publication is interrupted before the result, status remains non-success.
A PID is never used alone: status compares the persisted process-generation token to a
fresh token (`/proc/<pid>/stat` on Linux or process creation time on Windows).
If that comparison cannot be made, status is `uncertain`.

The child is started with `shell=False` and the explicit `cwd`. On Windows the
supervisor and test child use hidden-window process startup flags. The runner
does not serialize the inherited environment or search for credentials. Test
stdout/stderr and the explicit argv are still evidence supplied by the
caller; do not put secrets in a test command or cause a test to print them.

The timeout bounds the direct child. `terminal: true` and `success` describe
that direct child only; they do not freeze `stdout.txt`/`stderr.txt` or prove
that a process tree has stopped. This small runner does not promise
process-tree containment: a test that spawns descendants may leave them
running and may write more output after the direct-child result is published.
A valid `timed_out` result can therefore coexist with surviving descendants or
logs that are still changing.
It also does not promise recovery after a supervisor crash. In either case, a
missing result remains `uncertain`; do not retry or relaunch until the
coordinator has inspected the run evidence.

## Python API

For tests, the same contract is available without a shell:

```python
from test_runner import start_run, status_run

started = start_run(
    ["python", "-m", "unittest", "tests.test_example"],
    cwd=".",
    evidence_root="./test-evidence",
    timeout=180,
)
state = status_run(started["run_handle"])
```

`start_run` requires a sequence of argv strings, not a shell command string;
`status_run` only reads the run directory represented by its handle.
