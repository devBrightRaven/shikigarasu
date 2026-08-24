#!/usr/bin/env python3
"""Bounded, read-only agy routing and JSON/vision verification."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Callable, Sequence


COORDINATOR_TASKS = {
    "scope",
    "canonical_source",
    "public_commitment",
    "commit",
    "push",
    "publish",
    "final_completion",
}

TASK_PATTERNS = {
    "source_extract": ("flash-low",),
    "classify": ("flash-low",),
    "deduplicate": ("flash-low",),
    "bulk_summary": ("flash-medium",),
    "translate": ("flash-medium",),
    "format_convert": ("flash-medium",),
    "draft": ("flash-high",),
    "structure": ("flash-high",),
    "contradiction": ("-pro-high", "-pro-low"),
    "visual_review": ("-pro-high", "-pro-low"),
    "heterogeneous_arbitration": ("-pro-high", "-pro-low"),
}

REFUSAL_RE = re.compile(
    r"\b(?:i (?:can(?:not|'t)|must refuse)|unable to comply|safety (?:policy|refusal)|"
    r"cannot assist|refuse to)\b",
    re.IGNORECASE,
)

READ_ONLY_PREAMBLE = """You are a bounded read-only reviewer under a Codex coordinator.
Do not modify files, change scope, select a canonical source, commit, push, publish, make public
commitments, or declare the overall task complete.
"""


def discover_models(
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    timeout_sec: int = 15,
) -> list[str]:
    result = runner(
        ["agy", "models"],
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "agy models failed")
    return [
        line.strip()
        for line in result.stdout.splitlines()
        if re.fullmatch(r"[a-z0-9][a-z0-9.-]*", line.strip())
    ]


def route_task(task: str, models: Sequence[str]) -> dict[str, str | None]:
    if task in COORDINATOR_TASKS:
        return {"owner": "codex", "model": None, "status": "protected"}
    patterns = TASK_PATTERNS.get(task)
    if not patterns:
        return {"owner": "codex", "model": None, "status": "unrouted"}
    for pattern in patterns:
        for model in models:
            if pattern in model:
                return {"owner": "agy", "model": model, "status": "ready"}
    return {"owner": "codex", "model": None, "status": "degraded"}


def model_identity_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def model_identity_matches(requested: str, reported: str) -> bool:
    return bool(requested and reported) and model_identity_key(requested) == model_identity_key(
        reported
    )


def is_safety_refusal(text: str) -> bool:
    return bool(REFUSAL_RE.search(text))


def json_text(raw: str) -> str:
    text = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    return fenced.group(1).strip() if fenced else text


def parse_json_with_one_repair(
    raw: str, repair: Callable[[str], str]
) -> tuple[dict, bool]:
    if is_safety_refusal(raw):
        raise PermissionError("safety refusal")
    try:
        return json.loads(json_text(raw)), False
    except json.JSONDecodeError:
        repaired = repair(raw)
        if is_safety_refusal(repaired):
            raise PermissionError("safety refusal")
        return json.loads(json_text(repaired)), True


def _agy_args(model: str, prompt: str, timeout_sec: int) -> list[str]:
    return [
        "agy",
        "--model",
        model,
        "--mode",
        "plan",
        "--sandbox",
        "--print-timeout",
        f"{timeout_sec}s",
        "-p",
        READ_ONLY_PREAMBLE + "\n" + prompt,
    ]


def run_bounded(
    prompt: str,
    model: str,
    timeout_sec: int = 90,
    retry_limit: int = 1,
    fallback_model: str | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict:
    attempts = 0
    candidates = [(model, retry_limit + 1)]
    if fallback_model and fallback_model != model:
        candidates.append((fallback_model, 1))

    last_error = "agy invocation failed"
    for candidate_index, (candidate, allowed_attempts) in enumerate(candidates):
        for _ in range(allowed_attempts):
            attempts += 1
            try:
                result = runner(
                    _agy_args(candidate, prompt, timeout_sec),
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec + 10,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                last_error = "timeout"
                continue

            raw = result.stdout.strip()
            if is_safety_refusal(raw):
                return {
                    "status": "refused",
                    "model_requested": model,
                    "model_used": candidate,
                    "attempts": attempts,
                    "raw": raw,
                }
            if result.returncode:
                last_error = result.stderr.strip() or f"agy exited {result.returncode}"
                continue
            return {
                "status": "degraded" if candidate_index else "ok",
                "model_requested": model,
                "model_used": candidate,
                "attempts": attempts,
                "raw": raw,
            }

    return {
        "status": "failed",
        "model_requested": model,
        "model_used": candidates[-1][0],
        "attempts": attempts,
        "error": last_error,
        "raw": "",
    }


def invoke_json(
    prompt: str,
    model: str,
    timeout_sec: int = 90,
    fallback_model: str | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict:
    result = run_bounded(
        prompt,
        model,
        timeout_sec=timeout_sec,
        retry_limit=1,
        fallback_model=fallback_model,
        runner=runner,
    )
    if result["status"] in {"failed", "refused"}:
        return result

    def repair(raw: str) -> str:
        repair_prompt = (
            "Return one valid JSON object only. Preserve the meaning and do not add facts.\n"
            f"Invalid response:\n{raw}"
        )
        repaired = run_bounded(
            repair_prompt,
            result["model_used"],
            timeout_sec=timeout_sec,
            retry_limit=0,
            runner=runner,
        )
        if repaired["status"] in {"failed", "refused"}:
            return repaired.get("raw", "")
        return repaired["raw"]

    try:
        payload, repaired = parse_json_with_one_repair(result["raw"], repair)
    except PermissionError:
        result["status"] = "refused"
        return result
    except json.JSONDecodeError as exc:
        result["status"] = "failed"
        result["error"] = f"invalid JSON after one repair: {exc}"
        return result

    result["payload"] = payload
    result["json_repaired"] = repaired
    return result


def evaluate_vision_gate(
    payload: dict,
    requested_model: str,
    expected_filename: str,
    expected_title: str,
    expected_relation: str,
) -> dict:
    reported = str(payload.get("model_reported", ""))
    expected_relation_tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", expected_relation.casefold())
        if token not in {"a", "an", "the", "is", "of", "to"}
    }
    actual_relation_tokens = set(
        re.findall(r"[a-z0-9]+", str(payload.get("position_relation", "")).casefold())
    )
    checks = {
        "pixels_accessed": payload.get("vision_verified") is True,
        "model_match": model_identity_matches(requested_model, reported),
        "filename_match": payload.get("filename") == expected_filename,
        "title_match": payload.get("largest_title") == expected_title,
        "relation_match": bool(expected_relation_tokens)
        and expected_relation_tokens <= actual_relation_tokens,
    }
    verified = all(checks.values())
    result = dict(payload)
    result["vision_verified"] = verified
    result["status"] = "ok" if verified else "degraded"
    result["vision_checks"] = checks
    return result


def assess_heterogeneous_review(reviewers: Sequence[dict]) -> dict:
    identities = [
        model_identity_key(str(item.get("model_reported", ""))) for item in reviewers
    ]
    verified = all(
        item.get("artifact_verified") is True
        and model_identity_matches(
            str(item.get("model_requested", "")),
            str(item.get("model_reported", "")),
        )
        for item in reviewers
    )
    diverse = len(identities) == len(set(identities)) and all(identities)
    return {
        "status": "ok" if verified and diverse else "degraded",
        "artifact_verified": verified,
        "model_diversity_verified": bool(diverse),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("models", help="Discover current agy models")

    review = subparsers.add_parser("review", help="Run one bounded read-only JSON review")
    review.add_argument("--model", required=True)
    review.add_argument("--prompt-file", type=Path, required=True)
    review.add_argument("--fallback-model")
    review.add_argument("--timeout", type=int, default=90)

    vision = subparsers.add_parser("vision", help="Verify actual access to one local PNG")
    vision.add_argument("--image", type=Path, required=True)
    vision.add_argument("--model", required=True)
    vision.add_argument("--title", required=True)
    vision.add_argument("--relation", required=True)
    vision.add_argument("--timeout", type=int, default=90)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "models":
        print(json.dumps({"models": discover_models()}, indent=2))
        return 0

    if args.command == "review":
        prompt = args.prompt_file.read_text(encoding="utf-8")
        result = invoke_json(
            prompt,
            args.model,
            timeout_sec=args.timeout,
            fallback_model=args.fallback_model,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] in {"ok", "degraded"} else 1

    if args.image.suffix.casefold() != ".png" or not args.image.is_file():
        raise SystemExit("--image must be an existing PNG")
    prompt = f"""Read the PNG at {args.image.resolve()} using actual image pixels.
Return JSON only with:
{{
  "vision_verified": true,
  "model_requested": "{args.model}",
  "model_reported": "exact actual model identity or unknown",
  "filename": "{args.image.name}",
  "largest_title": "exact largest title",
  "position_relation": "copy this exact expected relation if it is visible, otherwise describe the contradiction: {args.relation}",
  "evidence": "how image pixels were accessed"
}}
Set vision_verified false and leave visual fields empty if pixels are unavailable."""
    invoked = invoke_json(prompt, args.model, timeout_sec=args.timeout)
    if invoked["status"] not in {"ok", "degraded"} or "payload" not in invoked:
        print(json.dumps(invoked, ensure_ascii=False, indent=2))
        return 1
    result = evaluate_vision_gate(
        invoked["payload"],
        args.model,
        args.image.name,
        args.title,
        args.relation,
    )
    result["json_repaired"] = invoked["json_repaired"]
    result["attempts"] = invoked["attempts"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["vision_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
