# Bounded File Reads: 15 Small Commits

## Goal

Let the agent read a specific file section with bounded output and explicit
continuation metadata. Keep the existing single-prompt CLI and workspace checks.

## Known State

`read_file` currently reads a whole file into memory and accepts only `path`.
The repository already has deterministic unittest coverage. The previously
written README/roadmap documentation will be included in the planning commit.

## Contract

Use 1-based `offset`, a line `limit`, and a character budget `max_chars`.
Defaults will be 200 lines and 16,000 characters; hard ceilings will be 2,000
lines and 65,536 characters. Return JSON text containing content, range, and
continuation metadata. Preserve complete lines: when a single selected line
exceeds the character budget, return an actionable error instead of silently
omitting part of it. Read incrementally, including when skipping long lines.

## Checklist

- [x] 1. Record the roadmap and implementation plan on a feature branch.
  Verification: baseline unittest discovery and `git diff --check`.
  Result: all 59 baseline tests and diff checks passed.
- [x] 2. Add a 1-based starting-line offset.
  Verification: focused offset tests.
  Result: 3 focused tests and diff checks passed.
- [x] 3. Add an optional line limit.
  Verification: focused range tests.
  Result: all 5 range tests and diff checks passed.
- [x] 4. Validate range argument types and values.
  Verification: invalid offset/limit tests, including booleans.
  Result: all 7 focused tests and diff checks passed.
- [x] 5. Advertise optional range arguments to the model.
  Verification: tool schema contract tests.
  Result: all 14 focused/schema tests and diff checks passed.
- [x] 6. Bound default and maximum line counts.
  Verification: default truncation and hard-limit tests.
  Result: all 16 focused/schema tests and diff checks passed.
- [x] 7. Return structured range and continuation metadata.
  Verification: exact-boundary, EOF, and continuation tests.
  Result: all 71 tests and diff checks passed, including continuation without gaps.
- [x] 8. Add a configurable character budget and preserve complete lines.
  Verification: character-boundary and oversized-line tests.
  Result: all 24 focused/schema tests and diff checks passed.
- [x] 9. Stream selected lines instead of loading the whole file.
  Verification: streaming and existing range tests.
  Result: all 17 focused tests and diff checks passed; whole-file reads are rejected by the test reader.
- [~] 10. Bound selected-line reads to protect against huge lines.
  Verification: guarded-reader test for bounded `readline` calls.
- [ ] 11. Skip earlier oversized lines in bounded chunks.
  Verification: late-offset reads after an oversized line.
- [ ] 12. Cover text and workspace boundary cases.
  Verification: empty files, Unicode, newline variants, and symlink containment.
- [ ] 13. Verify ranged reads and error recovery through the agent loop.
  Verification: fake-client multi-round integration tests.
- [ ] 14. Document the tool contract and continuation examples.
  Verification: documentation diff and schema tests.
- [ ] 15. Record final verification and roadmap progress.
  Verification: full unittest discovery, syntax checks, diff checks, and commit count.

## Blockers / Failed Checks

The initial focused schema command imported `app.main` before the existing
OpenAI test stub was installed, and failed because the dependency is absent in
the system interpreter. Loading `tests.test_file_reads` (which imports the
shared helpers) first resolved the test setup; the rerun passed. Full discovery
also loads the existing helpers before these modules.
