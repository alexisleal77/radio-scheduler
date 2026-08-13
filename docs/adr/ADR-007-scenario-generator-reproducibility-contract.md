# ADR-007: Scenario Generator reproducibility contract (seeded `random.Random`, fixed iteration order)

## Status

Accepted

## Date

2026-08-13

## Context

Implementing `scenario_generator` requires deciding how the `seed` field on `Scenario` is actually honored. Without a fixed, documented contract for how pseudo-randomness is consumed, "same seed" does not by itself guarantee "same `Scenario`" — the same seed fed through a different order of random draws produces a different result. This directly touches the reproducibility guarantee already committed to in ADR-002 and Design Principle 4 of `docs/specification/domain-model-v0.1.md` ("the value of an entity must be entirely traceable from information contained in the model itself... never from computation or state hidden outside the model").

Per `docs/adr/README.md`'s criteria, this decision affects "reproducibility guarantees" by name and would be expensive to reverse silently: any accidental change to the Scenario Generator's draw order or PRNG scoping would silently invalidate every previously-recorded seed or fixture that depends on its output. This warrants an ADR — scoped narrowly to the Scenario Generator's own reproducibility mechanism, not to the concrete configuration shape or generation distributions (ordinary, reversible implementation details), and not to how any other module might achieve reproducibility for its own randomness.

## Decision

1. **Local PRNG only.** `generate_scenario()` creates its own `random.Random(seed)` instance, scoped to that single call. It never reads or reseeds the global `random` module state, and never accepts an externally shared `Random` instance. Determinism stays traceable to the call's own inputs, not to hidden external state.

2. **Fixed, documented iteration order.** All randomness is drawn in exactly this order: TTIs ascending by index, then UEs ascending by index within each TTI; for each (TTI, UE) pair, the Channel Quality value is drawn before the corresponding Traffic Arrival value. UEs, QoS Class assignment, TTIs, and Resource Blocks are generated deterministically and consume no randomness, so their generation order has no effect on reproducibility.

3. **Reproducibility guarantee.** For a fixed generator version, calling `generate_scenario(config)` twice with the same `ScenarioGeneratorConfig` (including the same `seed`) produces two `Scenario` values that are structurally equal (`==`), as a consequence of points 1–2 combined with the domain entities already being frozen dataclasses over tuples (ADR-006).

4. **No cross-version reproducibility guarantee.** This ADR guarantees reproducibility only within a fixed generator version (fixed algorithm and fixed iteration order). It does not guarantee that a given seed reproduces the same `Scenario` across different versions of the generator; changing the generation algorithm or the iteration order is expected to change the output for a previously-used seed.

5. **Sequence-affecting changes are observable behavior changes.** Any change to the generator that could alter the sequence of values drawn from the PRNG — reordering iteration, adding or removing a draw, or moving a field from fixed to randomly-drawn or vice versa — must be treated as an observable behavioral change, not an internal refactor. Such changes must be called out explicitly in code review/commit messages, and if they would invalidate previously-recorded seeds or fixtures relied upon elsewhere in the project, they must be recorded via a new or superseding ADR rather than folded silently into an unrelated change.

6. **Scenario independence from scheduling is preserved.** This ADR does not relax ADR-002. `generate_scenario()` produces only exogenous state (TTI, UE, QoSClass, ResourceBlock, ChannelQuality, TrafficArrival) and takes no scheduler, decision, or Run as input. This contract governs *how* values are drawn, never *what* is drawn, and cannot be used to introduce scheduling-dependent state.

7. **Concrete generation choices are out of scope.** Default numeric ranges (e.g. CQI bounds, traffic size bounds), the probability distribution used for CQI and Traffic Arrival, and the full field list of `ScenarioGeneratorConfig` are reversible implementation details local to `scenario_generator`, governed by code and its README — not by this ADR.

8. **Verification uses `unittest`.** The determinism guarantee in point 3 is initially verified with Python's standard-library `unittest`, avoiding a new dependency (e.g. `pytest`) at this stage, consistent with ADR-004's tooling scope and `pyproject.toml`'s current `dependencies = []`.

## Alternatives considered

- **Use the global `random` module** (module-level calls like `random.randint`) instead of a local `random.Random(seed)` instance. Rejected: reading/reseeding global state creates hidden shared state across calls and test runs, conflicting directly with Design Principle 4 and risking cross-test contamination.
- **Leave iteration order unspecified.** Rejected: without a documented, fixed order, two otherwise-correct implementations (or two refactors of the same one) could produce different sequences for the same seed, silently breaking the reproducibility guarantee already committed to elsewhere.
- **Guarantee seed stability across generator versions.** Rejected: promising that a seed reproduces identically forever, even as the algorithm evolves, would freeze the generator's internals prematurely and conflicts with this project's incremental development principle (`CLAUDE.md`). Reproducibility is scoped to "same version"; version-breaking changes are handled as an explicit process obligation (point 5) instead.
- **Adopt `pytest` now** for the determinism test. Rejected at this stage: it would be the project's first third-party dependency, and stdlib `unittest` is sufficient for the structural-equality test this guarantee requires.

## Consequences

- The randomness used to generate a `Scenario` is confined to `scenario_generator`: every draw goes through the one local `Random` instance, in the documented order, and the generator neither reads nor modifies Python's global pseudo-random state. This makes order-affecting changes something code review is specifically responsible for catching.
- Test fixtures or example scenarios recorded against one generator version remain valid only for that version; if the algorithm or iteration order changes, previously-recorded "expected `Scenario` for seed X" fixtures must be regenerated, not assumed stable.
- Future modules that need reproducibility for their own pseudo-randomness (e.g. a Simulation Loop, or repeated `benchmark` trials) may adopt an equivalent decision — a local seeded `Random` instance with a documented consumption order — but that choice belongs to each module's own context and is not mandated by this ADR.
- Tuning concrete distributions or default ranges (point 7) never requires revisiting this ADR; only a change to the mechanism itself (instance scoping, iteration order, or the observable draw sequence) does.
- Adopting `unittest` now does not block adopting `pytest` later if the test suite grows in ways `unittest` handles poorly — that remains a separate, reversible decision.

## Validation criteria

- Two calls to `generate_scenario` with an identical `ScenarioGeneratorConfig` (same seed) produce `Scenario` values that compare equal (`==`).
- `scenario_generator`'s randomness never touches `random`'s module-level functions or global state.
- The iteration order documented in point 2 matches the order actually implemented in `generate_scenario()`.

## Related documents

- [`ADR-002`](ADR-002-closed-loop-simulation.md) — exogenous-state independence this ADR inherits and does not relax.
- [`ADR-004`](ADR-004-implementation-language-and-tooling.md) — Python/uv, stdlib-first tooling basis for choosing `unittest` here.
- [`ADR-006`](ADR-006-entity-representation-conventions.md) — frozen dataclasses and tuple collections that make structural `==` sufficient for the reproducibility guarantee.
- [`docs/specification/domain-model-v0.1.md`](../specification/domain-model-v0.1.md) — Design Principle 4 (determinism as an intrinsic property of the data).
- [`docs/adr/README.md`](README.md) — criteria applied to justify this ADR's narrow scope.
