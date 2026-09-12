# Spec-driven closure contract

`closure_gate.py` is a small coordinator-side evidence checker for an approved,
spec-driven change. It reads a frozen JSON manifest and the files named by that
manifest. It never runs a command, changes a queue, discovers repository files,
enforces an OS policy, or verifies that a textual receipt is authentic. A
`CLOSABLE` result therefore permits coordinator review; it is not a proof that
the evidence is true.

## Contract

Run the checker from the plugin checkout with one manifest path:

```text
python -X utf8 codex/skills/shikigarasu/scripts/closure_gate.py path/to/manifest.json
```

For a new tiered manifest, also supply the review decision frozen before work
started.  The baseline can be a JSON file or a digest of the canonical policy:

```text
python -X utf8 codex/skills/shikigarasu/scripts/closure_gate.py path/to/manifest.json --review-baseline path/to/review-baseline.json
python -X utf8 codex/skills/shikigarasu/scripts/closure_gate.py path/to/manifest.json --review-baseline-digest <sha256-of-review-policy>
```

The programmatic equivalent is `run(manifest, review_baseline=<json-path>)` or
`run(manifest, review_baseline_digest=...)`.  A manifest that has no
`review_policy` is a legacy v1 manifest and retains the old two-reviewer gate;
an explicit tiered policy without a separately supplied baseline is `BLOCKED`.

The process prints a JSON result. Exit `0` means `CLOSABLE`; exit `2` means
`BLOCKED`. Missing files, malformed JSON or fields, non-zero acceptance
evidence, hash mismatches, or an incomplete review contract fail closed.
There is no queue or state-mutating CLI option.

Relative paths resolve from the manifest's directory. The manifest's
`contract` is the frozen input:

```json
{
  "schema_version": "sdd-closure/v1",
  "contract": {
    "requirement_ids": ["REQ-A", "REQ-B"],
    "spec": {"path": "spec.md", "sha256": "<sha256-of-spec.md>"},
    "artifact": {
      "path": "artifact.json",
      "sha256": "<sha256-of-artifact.json>",
      "files": {
        "src/main.py": "<sha256-of-src/main.py>"
      }
    }
  },
  "review_policy": {
    "tier": 2,
    "count": 2,
    "reason": "high-risk change with two independent reviews",
    "frozen": true,
    "high_risk": true
  },
  "evidence": {
    "requirements": {
      "REQ-A": {"path": "evidence/REQ-A.json"},
      "REQ-B": {"path": "evidence/REQ-B.json"}
    },
    "slices": [
      {
        "id": "slice-a",
        "requirement_ids": ["REQ-A", "REQ-B"],
        "receipts": [
          {"path": "evidence/slice-a-red.json"},
          {"path": "evidence/slice-a-green.json"}
        ]
      }
    ],
    "integration": {"path": "evidence/integration.json"}
  },
  "producers": ["producer-id"],
  "reviewers": [
    {"id": "reviewer-a", "path": "evidence/reviewer-a.json"},
    {"id": "reviewer-b", "path": "evidence/reviewer-b.json"}
  ],
  "findings": [],
  "collective_fix_rounds": 0
}
```

The coordinator keeps the execution-queue mapping separately: each ticket may
carry requirement IDs, dependencies, producer, and receipt paths. This checker
does not inspect or mutate that queue; it only confirms that the manifest's
declared requirement IDs have corresponding evidence.

`review_policy.tier` is the review decision, not a requirement or test count:

| Tier | Meaning | Required reviewers |
|---:|---|---:|
| `0` | mechanical | `0` |
| `1` | standard | `1` |
| `2` | high | `2` |

`count` must match the tier exactly, `reason` must be non-empty, and
`frozen` must be the JSON boolean `true`. The policy is compared with the
separately supplied baseline before the reviewer list is checked, so editing a
manifest alone cannot lower its reviewer requirement. `high_risk: true` or
`gate_change: true` always requires tier `2` and count `2`; changes to this
closure gate use that old dual-review requirement. The checker can validate a
declared baseline or digest, but cannot prove who authored it, when it was
frozen, or that its risk assessment is authentic.

Producer IDs remain distinct from reviewer IDs, and every required reviewer
still binds evidence to the frozen artifact digest. A reviewer may re-review a
narrowed change by submitting fresh review evidence bound to the new artifact
digest; unrelated valid requirement/TDD receipts do not need to be rerun. The
existing unresolved Critical/Important finding and collective two-fix-round
ceiling remain in force.

The placeholders above are the only values that must be computed. The following
runnable fixture exercises the legacy path; run it from the
plugin checkout (or use an absolute script path), then pass the printed
manifest path to the command above. It writes only a fresh temporary example
directory; remove that directory when finished. To exercise an explicit
tiered fixture, add the `review_policy` object shown above and pass a matching
external baseline.

```python
from pathlib import Path
import hashlib, json, tempfile

root = Path(tempfile.mkdtemp(prefix="sdd-closure-example-"))
(root / "src").mkdir(parents=True, exist_ok=True)
(root / "evidence").mkdir(parents=True, exist_ok=True)
(root / "spec.md").write_text("# Example\n", encoding="utf-8")
(root / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
def checks(command, code=0, failures=0):
    return {"checks": [{"command": command, "exit_code": code,
                        "failures": failures, "observed": ["captured"]}]}

member = root / "src" / "main.py"
write(root / "artifact.json", {"files": {"src/main.py": sha(member)}})
artifact = root / "artifact.json"
write(root / "evidence" / "REQ-A.json",
      {"requirement_id": "REQ-A", **checks("test requirement")})
write(root / "evidence" / "slice-a-red.json",
      {"slice_id": "slice-a", "phase": "RED", **checks("test red", 1, 1)})
write(root / "evidence" / "slice-a-green.json",
      {"slice_id": "slice-a", "phase": "GREEN", **checks("test green")})
write(root / "evidence" / "integration.json", checks("test integration"))
artifact_hash = sha(artifact)
for name in ("reviewer-a", "reviewer-b"):
    write(root / "evidence" / f"{name}.json", {
        "reviewer_id": name, "independent": True, "verdict": "pass",
        "artifact_sha256": artifact_hash, **checks(f"review {name}")})
manifest = {
    "schema_version": "sdd-closure/v1",
    "contract": {
        "requirement_ids": ["REQ-A"],
        "spec": {"path": "spec.md", "sha256": sha(root / "spec.md")},
        "artifact": {"path": "artifact.json", "sha256": artifact_hash,
                      "files": {"src/main.py": sha(member)}}},
    "evidence": {"requirements": {"REQ-A": {"path": "evidence/REQ-A.json"}},
                 "slices": [{"id": "slice-a", "requirement_ids": ["REQ-A"], "receipts": [
                     {"path": "evidence/slice-a-red.json"},
                     {"path": "evidence/slice-a-green.json"}]}],
                 "integration": {"path": "evidence/integration.json"}},
    "producers": ["producer-id"],
    "reviewers": [{"id": "reviewer-a", "path": "evidence/reviewer-a.json"},
                   {"id": "reviewer-b", "path": "evidence/reviewer-b.json"}],
    "findings": [], "collective_fix_rounds": 0,
}
write(root / "manifest.json", manifest)
print(root / "manifest.json")
```

## Evidence rules

Every evidence JSON object uses a non-empty `checks` array. Each check has a
non-empty `command`, an `observed` list of non-empty strings, an integer
`exit_code`, and a non-negative integer `failures`. JSON booleans are not
accepted as integers, even though Python normally treats `bool` as a subclass
of `int`.

* Requirement evidence must identify its requirement with `requirement_id` and
  every check must exit `0` with zero failures. The requirement evidence keys
  must equal the frozen `contract.requirement_ids` exactly; no required item may
  be omitted or silently added.
* Slices must be a non-empty ordered list with unique IDs. Each slice has
  one or more unique `requirement_ids` from the frozen list, and the union of
  slice mappings must cover every frozen requirement. Each slice has exactly
  two receipt paths, in `[RED, GREEN]` order. Receipt JSON identifies
  the slice with `slice_id` and its phase with `phase`. RED must show a non-zero
  exit code or positive failure count; GREEN must have exit `0` and zero
  failures. The array order is a declared evidence order; the checker cannot
  independently prove execution chronology or the cause of a failure. This
  records behavior-first TDD evidence, not merely a source diff, so the
  coordinator must inspect raw outputs and must not count a bootstrap/import
  error as behavioral RED.
* Integration evidence must have exit `0` and zero failures for every check.
* `artifact.json` must be a JSON object with a non-empty `files` map. The
  declared map in the frozen contract must equal the descriptor's embedded map
  exactly, and every declared file must exist with the declared SHA-256. The
  checker hashes only these declared paths; it does not claim full repository
  discovery. The descriptor's own SHA-256 is also checked.
* `producers` must contain unique non-empty IDs. Legacy manifests and tier `2`
  require exactly two reviewer entries; tier `1` requires one and tier `0`
  requires none. Each required reviewer evidence object must match its reviewer
  ID, set `independent` to JSON `true`, use verdict `pass`, and bind
  `artifact_sha256` to the same frozen artifact digest. Reviewer IDs must be
  distinct and absent from `producers`.
* For an explicit tiered policy, the caller must provide `review_baseline` or
  `review_baseline_digest` separately from the manifest. A baseline object must
  contain the same tier/count/reason/frozen decision (and any high-risk flags);
  a mapping passed directly as `review_baseline` is invalid. The digest form is
  the SHA-256 of compact, sorted JSON containing
  `tier`, `count`, `reason`, `frozen`, `high_risk` (default `false`), and
  `gate_change` (default `false`). Invalid integer/boolean shapes or any
  mismatch block closure.
* `findings` must be a list of objects with severity `Critical`, `Important`,
  `Minor`, or `Info`, and status `open`, `resolved`, or `closed`.
  `Important` and `Critical` findings must be `resolved` or `closed`. The
  integer `collective_fix_rounds` must be between `0` and `2`, inclusive; the
  ceiling is collective across all findings.

The result's claims make the boundary explicit: the gate is read-only,
`queue_mutated`, `os_enforcement`, `authenticity_verified`, and
`full_repository_discovery` are all false. A supplied review baseline is an
explicit trust input, not proof of risk authenticity or chronology. A
coordinator still needs to inspect the raw evidence and apply the
independent-review protocol before closing.
