# Clean-Code Standard and Review

This project's standard is explicit dependencies, readable Python, stable tool
contracts, and automated verification. PEP 8 conventions are enforced through
Ruff formatting and a focused lint rule set; this is a practical project
standard, not a claim of universal certification.

## Current checklist

Reviewed during the consolidation milestone in [PLAN.md](PLAN.md). Checked items
have implementation evidence; unchecked items are incomplete or only partially
complete, rather than a claim that no work has been done.

- [ ] Cohesive modules: CLI, provider, agent, workspace, validation, and tools.
- [ ] Workspace/environment configuration is explicit or loaded at runtime.
      Workspace is explicit; mlab settings load at runtime. The legacy
      `app.main.BASE_URL` still reads the environment at import time.
- [ ] Public core interfaces have useful annotations and descriptive names.
- [x] Tool registration connects schemas and implementations in one place.
- [x] Validate argument objects and values before side effects.
- [ ] Expected failures become actionable errors; programming failures remain visible.
      mlab handles expected provider/runtime errors, but the tool loop still
      catches all `Exception` instances and returns them to the model.
- [x] Encoding failures do not truncate existing files.
- [x] Preserve containment, bounded read/search buffers, paginated output, and exclusive creation.
- [x] Logs summarize large arguments and structured results without dumping content.
- [x] Tests own their filesystem inputs and use scoped mocks.
- [x] Fakes preserve caller data and record stable request snapshots.
- [x] Implemented contracts cannot silently skip tests; CLI exit codes are checked.
- [x] Launchers preserve caller working directories and use the correct project root.
- [x] Locked dependencies, format, lint, syntax, and tests are configured in CI.
- [x] Delivered cleanup layers have verification records in the delivery plans.

Directory listing still collects entry names for sorting; edits read the whole
file. Bounded read/search I/O does not imply a bounded runtime or full OS sandbox.

## Historical baseline findings, current disposition

Locations below identify files at review time; old line numbers have been removed
because the implementation has changed. The original 20-step extraction is
partial; see [CLEAN_CODE_PLAN.md](CLEAN_CODE_PLAN.md).

| Finding | Priority | Baseline location | Status |
| --- | --- | --- | --- |
| Verbose logging crashes on JSON arrays/null before error handling | High | `app/main.py` | Fixed: validated parsing and bounded diagnostics; `tests/test_agent_loop.py`, `tests/test_diagnostics.py` |
| Edit encoding can fail after destination truncation | High | `app/main.py` | Fixed: pre-encoding and atomic replacement; `app/writes.py`, `tests/test_write_tools.py` |
| Test imports replace the SDK globally | High | `tests/helpers.py`, `tests/test_tool_contracts.py` | Fixed: installed SDK and scoped mocks; no global SDK replacement remains |
| CLI, tools, SDK, schemas, and loop share one module | Medium | `app/main.py` | Partial: mlab CLI, settings, schemas, registry, workspace, and rendering extracted; tools and orchestration remain together |
| Mutable workspace and import-time environment state | Medium | `app/main.py` | Partial: frozen injected `Workspace` and runtime mlab settings; legacy `BASE_URL` remains import-time |
| Duplicated validation and disconnected schema/function registries | Medium | `app/main.py` | Fixed: `app/validation.py`, `app/registry.py`; registry/schema/validation tests |
| Tests depend on repository files, fixed indexes, and conditional skips | Medium | `tests/` | Fixed for tool fixtures/contracts: temporary workspaces, call-ID lookup, unconditional contracts; launcher tests intentionally inspect actual launchers |
| Fakes mutate scripts and retain shared historical references | Medium | `tests/helpers.py` | Fixed: copied response queue and deep request snapshots; `tests/test_helpers.py` |
| Dependency environment and style checks are inconsistent | Medium | `pyproject.toml`, CI, README | Fixed: CI and contributor commands use locked sync, Ruff, recursive syntax, tests, and installed-wheel smoke |
| Remote launcher points at `.codecrafters` instead of project root | Medium | `.codecrafters/run.sh` | Fixed: absolute checkout roots with caller cwd preserved; `tests/test_launchers.py` |

## Acceptance evidence

The original clean-code delivery completed steps 1–12, not its proposed 20-commit
sequence. Later terminal, edit-reliability, and consolidation deliveries complete
some additional portions; they do not finish the remaining extraction work.
Their verification records are preserved in the delivery plans. CI configuration
has been exercised locally; hosted CI results require pushing the branch.

Existing tool defaults, JSON shapes, and single-prompt behavior remain stable
unless a confirmed defect is documented. The remaining structural work is tool
and orchestration extraction, legacy runtime configuration, stronger error
boundaries, and useful public-interface annotations.

## Scope boundaries

Session persistence, command execution, round-budget redesign, regex/file-filter
features, and a full OS sandbox remain roadmap work. Do not introduce speculative
frameworks or abstractions to satisfy this cleanup checklist.
