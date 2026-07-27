# ADR-001: JSON as the canonical scenario data format

## Status

Accepted

## Date

2026-07-27

## Context

`scenario_generator` produces scenario data (network state over time — UEs, CQI, buffer/traffic demand, resource blocks, QoS class) that must be replayable, byte-for-byte, against any scheduling algorithm. `docs/architecture.md` states reproducibility as a core design principle: the same scenario must produce comparable, deterministic results across runs and across algorithms.

A serialization format for scenarios (and, by extension, benchmark results) needs to be chosen. The implementation language is not yet decided, so the format must be well-supported and behave consistently across languages.

## Decision

Use JSON as the canonical format for scenario data and benchmark results.

## Alternatives considered

- **YAML** — more human-readable and supports comments, but its parsers diverge in behavior across languages and implicit typing is ambiguous (e.g. the "Norway problem," where values like `NO`, `on`, or `1.0` are interpreted inconsistently depending on the parser). This is a direct risk to the reproducibility guarantee for data that is generated and consumed by code rather than hand-written.

## Consequences

- Scenario and result files can be validated with JSON Schema, which doubles as groundwork for the future conformance test suite for `scheduling_interface` implementations.
- Parsing behavior is consistent regardless of which language ends up being chosen for implementation.
- Scenario/config files intended to be hand-written or hand-edited by humans lose YAML's comment support and lighter syntax; this ADR does not preclude using YAML for such files if that need arises — it only fixes the format for scenario data and results.
- JSON's lack of native support for comments or trailing commas means scenario fixtures checked into `tests/` will need external documentation (e.g. a sibling README or `$comment` fields) rather than inline notes.

## Validation criteria

Scenario files produced by `scenario_generator` and results produced by `benchmark` parse identically across at least two different language runtimes (relevant once the implementation language is chosen), and validate against a published JSON Schema without ambiguity in type interpretation.

## Related documents

- [`docs/architecture.md`](../architecture.md) — reproducibility principle, `scenario_generator` responsibilities.
- [`docs/architecture_review.md`](../architecture_review.md) — scenario materialization and conformance test suite gaps.
