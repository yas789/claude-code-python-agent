# Clean-Code Standard and Review

This project's standard is explicit dependencies, readable Python, stable tool
contracts, and automated verification. PEP 8 conventions are enforced through
Ruff formatting and a focused lint rule set; this is a practical project
standard, not a claim of universal certification.

## Required checklist

- [ ] Cohesive modules: CLI, provider, agent, workspace, validation, and tools.
- [ ] Workspace/environment configuration is explicit or loaded at runtime.
- [ ] Public core interfaces have useful annotations and descriptive names.
- [ ] Tool registration connects schemas and implementations in one place.
- [ ] Validate argument objects and values before side effects.
- [ ] Expected failures become actionable errors; programming failures remain visible.
- [x] Encoding failures do not truncate existing files.
- [ ] Preserve containment, bounded I/O, pagination, and exclusive creation.
- [ ] Logs summarize large arguments and structured results without dumping content.
- [ ] Tests own their filesystem inputs and use scoped mocks.
- [ ] Fakes preserve caller data and record stable request snapshots.
- [ ] Implemented contracts cannot silently skip tests; CLI exit codes are checked.
- [ ] Launchers preserve caller working directories and use the correct project root.
- [ ] Locked dependencies, format, lint, syntax, and tests are checked in CI.
- [ ] Each cleanup layer is verified and recorded in `PLAN.md`.

## Baseline findings

| Finding | Priority | Baseline location | Status |
| --- | --- | --- | --- |
| Verbose logging crashes on JSON arrays/null before error handling | High | `app/main.py:517–541` | Open |
| Edit encoding can fail after destination truncation | High | `app/main.py:311` | Fixed: pre-encoding and atomic replacement; see `PLAN.md` edit reliability delivery |
| Test imports replace the SDK globally | High | `tests/helpers.py`, `tests/test_tool_contracts.py` | Open |
| CLI, tools, SDK, schemas, and loop share one module | Medium | `app/main.py` | Open |
| Mutable workspace and import-time environment state | Medium | `app/main.py:9–12,571–575` | Open |
| Duplicated validation and disconnected schema/function registries | Medium | `app/main.py` | Open |
| Tests depend on repository files, fixed indexes, and conditional skips | Medium | `tests/` | Open |
| Fakes mutate scripts and retain shared historical references | Medium | `tests/helpers.py` | Open |
| Dependency environment and style checks are inconsistent | Medium | `pyproject.toml`, CI, README | Open |
| Remote launcher points at `.codecrafters` instead of project root | Medium | `.codecrafters/run.sh` | Open |

## Acceptance evidence

Final evidence will record command results, regression coverage, module layout,
and the exact 20-commit sequence. Existing tool defaults, JSON shapes, and
single-prompt behavior must remain stable unless a confirmed defect is documented.

## Scope boundaries

Session persistence, command execution, round-budget redesign, regex/file-filter
features, and a full OS sandbox remain roadmap work. Do not introduce speculative
frameworks or abstractions to satisfy this cleanup checklist.
