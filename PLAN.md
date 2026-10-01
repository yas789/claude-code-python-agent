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
- [~] 4. Isolate filesystem tests with shared temporary-workspace setup. Verify tests.
- [ ] 5. Stabilize fake clients and add call-ID lookup. Verify helper regressions.
- [ ] 6. Make contracts unconditional and assert CLI exit codes. Verify focused tests.
- [ ] 7. Extract consistently named limits/defaults. Verify schemas and tests.
- [ ] 8. Extract validation and explicit errors. Verify invalid-input behavior.
- [ ] 9. Apply shared validation to reads. Verify read boundaries and invalid paths.
- [ ] 10. Centralize registry and argument decoding. Verify malformed calls in verbose mode.
- [ ] 11. Extract bounded logging and JSON-aware summaries. Verify diagnostics.
- [ ] 12. Introduce explicit workspace context. Verify independent workspaces.
- [ ] 13. Extract read/list operations. Verify pagination and bounded I/O.
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
