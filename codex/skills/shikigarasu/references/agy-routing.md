# agy routing policy

## Authority

agy is a bounded external worker and reviewer under the Codex coordinator. It does not own task
decomposition, scope changes, canonical-source selection, commits, pushes, publishing, public
commitments, or the final completion decision.

Run `agy --version`, inspect `agy --help`, and run `agy models` before routing. Model names are
runtime data. The patterns below choose among discovered models; the examples are not an
installation manifest.

## Task routing

| Task | Preferred discovered tier | Boundary |
|---|---|---|
| Source extraction, classification, deduplication | Gemini Flash Low | Return bounded evidence only |
| Bulk summarization, translation, format conversion | Gemini Flash Medium | Preserve literals and source boundaries |
| First-pass copy and structure | Gemini Flash High | Draft only; no scope or publication decisions |
| Contradiction analysis, visual review, heterogeneous arbitration | Gemini Pro, prefer High | Reviewer evidence only; Codex arbitrates |
| Scope, canonical source, public commitment, commit, push, publish, final completion | Codex coordinator | Never delegate to Flash or agy |

If the preferred tier is absent, choose at most one compatible discovered fallback. Do not silently
substitute a lower-authority model for a high-risk task.

## Bounded execution

- Run agy in read-only plan/sandbox mode.
- Give the primary request one timeout retry at most.
- After exhausted transport/timeout attempts, allow at most one compatible fallback attempt.
- Do not fallback, retry for a PASS, or repair around a safety refusal.
- Accept a Markdown-fenced JSON object as transport normalization.
- If JSON is otherwise invalid, request exactly one JSON repair. If that response is still invalid,
  fail the review.
- Record `model_requested` and `model_reported`. Normalize display punctuation for comparison, but
  never treat a different family, version, or effort tier as a match.
- If requested and reported identities differ, set status to `degraded`; do not claim heterogeneous
  review from the requested model.

## Heterogeneous review

Heterogeneous review requires distinct verified model identities and actual access to the same raw
artifact or evidence. If two reviewers report the same identity, a requested/reported mismatch
occurs, or either reviewer did not access the artifact, disclose the degradation. Safety refusal is
`refused`, never `PASS`.

## Runtime verification snapshot

On 2026-07-27, agy 1.1.7 read the pixels of a local PNG and correctly reported its filename,
largest title, and the requested spatial relationship. A request for `gemini-3.6-flash-high`
reported the matching display identity and passed every gate. The routed visual-review probe still
requested `gemini-3.1-pro-high` but reported `Gemini 3.6 Flash (High)`; therefore the preferred
Gemini Pro visual-review route remains `degraded` and is not trusted as heterogeneous Pro review.
Until a fresh Pro probe satisfies every gate, Codex performs final visual inspection.
