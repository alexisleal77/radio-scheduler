# ADR-006: Entity representation conventions (references, embedding, collections, CQI scale)

## Status

Accepted

## Date

2026-08-13

## Context

`docs/specification/domain-model-v0.1.md` defines the 13 Core Entities conceptually but explicitly defers attribute-level detail and concrete field types to implementation. Implementing the remaining 11 entities (Channel Quality, Traffic Arrival, Resource Block, UE, Buffer, HARQ State, Scenario, AllocationDecision, Scheduler, Run, Scheduling Performance Metric) as dataclasses in `radio_scheduler.domain.entities` requires resolving a small set of structural questions that apply uniformly across all of them — not just to one entity in isolation. Left unresolved, each entity risks being modeled inconsistently (some referencing related entities by embedding, others by ID, arbitrarily), which is exactly the kind of drift `docs/architecture_review.md` and Design Principle 1 (single canonical ownership) were meant to prevent. These are structural/data-flow decisions — they affect the shape of every JSON document produced under ADR-001 — so they meet this project's own bar for an ADR (`docs/adr/README.md`: "affects module boundaries... data flow between modules... would be expensive to reverse once implementation exists").

Reference points used in deciding this: how 3GPP defines CQI (a standardized 0–15 index, already discussed in ADR-003's research into K0/K1/K2 pipelines and reused by ns-3 NR, srsRAN, OpenAirInterface); and the general data-modeling practice (common in scientific/reproducible datasets and relational schemas alike) of normalizing repeated, time-varying records by foreign-key-style identifiers rather than duplicating embedded copies of a parent object in every record.

## Decision

Four conventions apply to all entities implemented from this point on:

1. **Per-TTI / repeated records reference their parent entities by identifier (`str`), not by embedding.** `ChannelQuality`, `TrafficArrival`, `Buffer`, `HARQState`, and `AllocationDecision` each carry a `ue_id: str` (and, where relevant, a `tti: TTI`) rather than embedding a full `UE` object. This avoids duplicating an entire UE (or Scenario, or Scheduler) once per TTI across potentially thousands of records, and avoids the inconsistency risk of the same UE existing as slightly different embedded copies across records.
2. **Static, one-to-one relationships may still be embedded.** `UE` embeds its `QoSClass` directly (created once, not repeated per TTI); `Run` embeds its `Scenario` and `Scheduler` directly (a Run has exactly one of each, so there is no duplication risk to normalize away).
3. **Collections inside entities are `tuple`, not `list`.** Frozen dataclasses are otherwise immutable; a `list` field would silently break that guarantee (lists are mutable in place). Tuples keep every entity, including its collections, genuinely immutable and hashable.
4. **Channel Quality is represented as a 3GPP CQI index (`int`, 0–15), not SINR.** This is the value the project's own named reference implementations (MaxCQI, Proportional Fair) consume directly, avoiding an undecided SINR→CQI conversion step. Within that range, **1–15 are reportable CQI indices**, and **0 represents the absence of a usable CQI indication** — an "out of range" condition or an unreported CQI, per the simulator's own abstraction (this is a simulation-level convention adopted for this project, not a restatement of the 3GPP CQI table's own indexing). HARQ State is simplified to a single `retransmission_pending: bool` rather than modeling multiple parallel HARQ processes, consistent with the "minimal and additive vocabulary" design principle already applied to `QoSClass` (free-text label instead of full 5QI) — richer modeling can be added later without breaking this shape.

No validation logic (e.g., asserting `0 <= cqi <= 15`) is added to any entity, per Design Principle 3 (entities are pure data, no embedded behavior).

## Alternatives considered

- **Embed full related entities everywhere** (e.g., `ChannelQuality` carrying a nested `UE` object). Rejected: duplicates the same UE data across every TTI record, and creates the risk of two "copies" of the same UE silently diverging — the exact coupling/consistency risk the domain model was created to prevent.
- **Represent Channel Quality as SINR (float, dB)** instead of CQI. Rejected for v0.1: SINR is the more physically fundamental quantity, but it requires a SINR→CQI mapping table that is undecided and out of scope for the current milestone; CQI is directly usable by the reference schedulers this project names as goals.
- **Model HARQ with full per-process state** (multiple parallel HARQ processes, as real 3GPP stacks do). Rejected for v0.1 as premature relative to the "minimal and additive vocabulary" principle; a boolean pending-retransmission flag is sufficient until a reference implementation actually needs more.

## Consequences

- Every future entity referencing a UE, Scenario, Resource Block, or Scheduler in a per-TTI or per-record context must follow the same `_id: str` convention, for consistency.
- JSON serialization (ADR-001) of a Scenario or Run will be a flat/normalized structure (parallel arrays of records keyed by ID and TTI) rather than a deeply nested tree — this needs to be kept in mind once a concrete JSON Schema is written.
- If CQI later proves insufficient (e.g., a future algorithm needs raw SINR), adding a `sinr` field alongside `cqi` is additive and does not break this ADR's decision, per the domain model's own evolution principle.
- HARQ State's simplified boolean will need to be revisited (a new, additive field or entity, not a breaking change) if a future reference implementation requires distinguishing which of several parallel HARQ processes is pending.

## Validation criteria

All 13 domain entities in `radio_scheduler.domain.entities` follow the same reference/embedding/collection conventions described above, with no exceptions; a Scenario and a Run can each be round-tripped to a flat dict/JSON structure without any entity requiring special-cased handling.

## Related documents

- [`docs/specification/domain-model-v0.1.md`](../specification/domain-model-v0.1.md) — conceptual entity definitions this ADR adds implementation-level structure to.
- [`ADR-001`](ADR-001-json-as-scenario-format.md) — canonical JSON format these conventions shape.
- [`ADR-003`](ADR-003-scheduling-pipeline-delay.md) — prior research into 3GPP K0/K1/K2 and simulator conventions (ns-3 NR, srsRAN, OpenAirInterface), reused here for the CQI scale decision.
- [`ADR-005`](ADR-005-domain-module.md) — `radio_scheduler.domain` as the module these entities live in.
