# Clean Code: 20 Verified Commits

Baseline: `1b7c116`, 136 passing tests. Previous plans are preserved in
`FILE_READ_PLAN.md` and `WORKSPACE_TOOLS_PLAN.md`.

Goal: isolate responsibilities and dependencies, fix confirmed defects, preserve
the five JSON tool contracts, and enforce documented Python standards.

Every step requires focused tests, formatting/lint checks when available, and
`git diff --check`. Update the result before proceeding; do not skip failures.

- [x] 1. Record standards and this plan. Verify the baseline suite.
- [x] 2. Configure Ruff and normalize formatting/imports. Verify lint and tests.
- [x] 3. Use installed dependencies and remove global SDK stubs. Verify independent imports.
- [x] 4. Isolate filesystem tests with shared temporary-workspace setup. Verify tests.
- [x] 5. Stabilize fake clients and add call-ID lookup. Verify helper regressions.
- [x] 6. Make contracts unconditional and assert CLI exit codes. Verify focused tests.
- [x] 7. Extract consistently named limits/defaults. Verify schemas and tests.
- [x] 8. Extract validation and explicit errors. Verify invalid-input behavior.
- [x] 9. Apply shared validation to reads. Verify read boundaries and invalid paths.
- [x] 10. Centralize registry and argument decoding. Verify malformed calls in verbose mode.
- [x] 11. Extract bounded logging and JSON-aware summaries. Verify diagnostics.
- [x] 12. Introduce explicit workspace context. Verify independent workspaces.
- [~] 13. Extract read/list operations. Verify pagination and bounded I/O.
- [ ] 14. Extract writes and pre-encode edits. Verify failures preserve files.
- [ ] 15. Extract search and deterministic iterator cleanup. Verify search contracts.
- [ ] 16. Isolate provider and runtime configuration. Verify environment changes.
- [ ] 17. Extract agent orchestration and clear error boundaries. Verify recovery.
- [ ] 18. Make CLI thin with expected-failure handling. Verify exit codes and output.
- [ ] 19. Correct launcher roots. Verify launchers outside the checkout.
- [ ] 20. Enforce CI standards and finish audit/docs. Verify all checks and 20 commits.

## Verification record

1. Baseline: 136 tests and diff checks passed. No blockers.
2. Locked Ruff installed; formatting, lint, all 136 tests, and diff checks passed.
3. Independent schema/config imports and all 136 tests passed; lint/format/diff clean.
4. Shared temporary fixtures isolate filesystem inputs; all 136 tests and quality checks passed.
5. Stable fake snapshots and call-ID lookup verified; 142 tests and quality checks passed.
6. All 16 focused CLI/contract tests and quality checks passed; no implemented-tool skips remain.
7. Static configuration extracted with unchanged values/schemas; 142 tests and quality checks passed.
8. Typed validators and explicit errors extracted; 150 tests and quality checks passed.
9. Read validation unified; all 40 focused read/validation tests and quality checks passed.
10. Registry and single argument decoding verified; 161 tests and quality checks passed.
11. Bounded diagnostics and JSON counts/ranges/truncation verified; preserved step 10
    regression tests (argument-decode assertion scoped to arguments because results now
    also decode JSON). All 165 tests, Ruff lint/format, and diff checks passed. No blockers.
12. Frozen canonical Workspace and instance-bound LocalTools/registries replace the
    mutable global. Tests inject registries; interleaved reads/writes/search/agent runs
    stay isolated, and CLI/agent defaults use runtime cwd. All 170 tests, Ruff
    lint/format, and diff checks passed. No blockers. Step 13 is next.

Follow-up: the five-commit edit reliability delivery in `PLAN.md` completes the
failure-preservation portion of step 14: pre-encoding, atomic replacement,
permission/newline preservation, staging cleanup, and regression tests. The
broader tool extraction checklist above remains partial.
