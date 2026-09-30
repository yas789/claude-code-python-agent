# Remaining Tools: 15 Small Commits

## Goal and Baseline

Apply bounded, structured output and precise validation to listing, search,
editing, and creation in 15 verified commits from baseline `cf3e327`.
The earlier completed file-read plan is preserved in [FILE_READ_PLAN.md](FILE_READ_PLAN.md).
File reads already support bounded streaming. Listings are unbounded; search
silently caps results and loads whole files. Write tools return plain text.

## Contracts

- Listing: stable sorted entry names; 1-based entry offset; default 100 entries,
  ceiling 2,000; default 16,000 name characters, ceiling 65,536.
- Search: case-sensitive, single-line substring queries; default 20 results,
  ceiling 200; default 16,000 snippet characters, ceiling 65,536. Stream files
  and long lines in bounded chunks. Snippet clipping must be explicit. Use a
  1-based matching-line offset to continue; rescanning assumes an unchanged tree.
- Both return JSON text and explicit `truncated`/`next_offset` metadata. Content
  budgets exclude metadata and JSON serialization overhead.
- Writes: validate complete arguments before mutation; return compact JSON
  receipts without echoing content. Preserve complete edits and creation content.
- Keep tool schemas synchronized with each implemented capability.

## Checklist

- [x] 1. Record plan and baseline on a feature branch.
  Verification: full unittest discovery and diff checks.
  Result: all 92 baseline tests and diff checks passed.
- [x] 2. Validate listing arguments.
  Verification: invalid types, booleans, offsets, and budgets.
  Result: 2 focused tests passed with invalid-input subcases; diff checks passed.
- [x] 3. Paginate directory listings.
  Verification: ordering, line/name budgets, and exact boundaries.
  Result: all 5 focused tests and diff checks passed.
- [x] 4. Add structured listing metadata and schemas.
  Verification: continuation reconstruction and schema contracts.
  Result: all 99 tests and diff checks passed.
- [x] 5. Verify listings through the agent loop.
  Verification: empty directories, EOF, and multi-page fake-client tests.
  Result: all 27 focused/agent tests and diff checks passed.
- [~] 6. Validate search arguments and configurable budgets.
  Verification: malformed queries, types, and budget boundaries.
- [ ] 7. Fix search containment and prune ignored directories.
  Verification: symlink escapes, internal links, and traversal checks.
- [ ] 8. Stream searched files and oversized lines.
  Verification: bounded-reader tests and chunk-boundary matching.
- [ ] 9. Add structured search results and explicit snippet clipping.
  Verification: result fields, character budgets, and schema contracts.
- [ ] 10. Add search continuation.
  Verification: match offsets, exact EOF, and reconstruction without gaps.
- [ ] 11. Verify search boundaries and recovery.
  Verification: Unicode, newline variants, unreadable files, and agent-loop tests.
- [ ] 12. Validate edit arguments before writing.
  Verification: empty targets, incorrect types, and unchanged files on failure.
- [ ] 13. Return structured edit receipts.
  Verification: replacement counts, deletion, and agent integration.
- [ ] 14. Validate creation and return structured receipts.
  Verification: full content, empty files, existing-file protection, and agent integration.
- [ ] 15. Document contracts and close the milestone.
  Verification: complete test suite, syntax/diff checks, and exactly 15 commits.

## Blockers / Failed Checks

None.
