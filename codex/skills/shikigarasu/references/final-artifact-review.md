# Final artifact review

Use this workflow once for a complete presentation or document, after content and design direction
are already approved. This is the canonical one-review/one-revision contract.

## Required sequence

1. Codex and the owning production capability create the complete first version.
2. Export PPTX, PDF, every page as PNG, and a full-page montage.
3. agy actually views every exported page and the montage.
4. agy records concrete visual observations.
5. agy arbitrates its own findings: merge duplicates; remove personal preference, image-unverifiable
   speculation, scope conflicts, content additions that do not improve decisions, and changes to an
   external production dependency. Produce one revision proposal.
6. Codex verifies actual image access and evaluates every retained finding as `ACCEPT`, `MODIFY`,
   `REJECT`, or `UNVERIFIABLE`.
7. Codex merges every `ACCEPT` and `MODIFY` into one change set.
8. Apply one concentrated design revision.
9. Run deterministic blocking QA only. Do not run a second free-form art review.
10. If a blocking defect remains, fix only that defect and rerun the deterministic check. This is
    not another design revision.

## Vision gate

Before trusting agy visual review, require one local PNG probe that correctly reports:

- the inspected filename;
- the exact largest title on the first page;
- one concrete spatial relationship;
- a reported model identity matching the requested model after punctuation-only normalization.

If any condition fails, output `vision_verified: false`, set `status: "degraded"`, and let Codex
perform the visual inspection. Do not repeatedly probe or bypass runtime safety. Never claim agy
visual QA succeeded without verified pixel access.

## agy arbitration output

```json
{
  "status": "ok|degraded|refused|failed",
  "vision_verified": true,
  "model_requested": "",
  "model_reported": "",
  "artifacts_reviewed": [],
  "arbitrated_findings": [
    {
      "id": "VIS-001",
      "slide": 1,
      "severity": "blocking|recommended|optional",
      "problem": "",
      "user_impact": "",
      "evidence": "",
      "proposed_change": "",
      "reason_to_change": "",
      "reason_to_leave_unchanged": ""
    }
  ],
  "keep_unchanged": [],
  "revision_priority": []
}
```

Retain at most 5 blocking, 8 recommended, and 5 optional findings. Reject findings without a page
and location, pure style preferences, directions that conflict with approved intent, changes that
add content without decision value, changes to external production dependencies, image-unverifiable
claims, and duplicates.

## Codex evaluation output

```json
{
  "id": "VIS-001",
  "decision": "ACCEPT|MODIFY|REJECT|UNVERIFIABLE",
  "reason": "",
  "final_change": ""
}
```

Codex retains final scope, brand, content, revision, and completion authority.

## Deterministic final QA

Check only clipping, overflow, overlap, missing content, unreadable contrast, broken fonts, export
failure, page count, and file integrity. Complete immediately when no blocking defect remains.
