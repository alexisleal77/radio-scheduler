# Architecture Review

Review of the Radio Scheduler design as of the initial repository scaffold: `README.md`, `CLAUDE.md`, `docs/architecture.md`, and the module-level `README.md` files under `src/`, `tests/`, and `scripts/`. No implementation code exists yet, so this reviews the *design*, treated as a pre-implementation architecture spec.

The module boundaries and the principle that everything crosses through `scheduling_interface` are sound and worth keeping. The gaps below are mostly forks in the design that will be expensive to change once code exists, so they are worth resolving before language selection and implementation begin.

## Architectural weaknesses

- **Open-loop vs. closed-loop simulation is conflated.** `scenario_generator`'s doc says it produces scenarios "independent of any algorithm" and "has no knowledge of scheduling algorithms." Taken literally, this means a scenario is fully pre-generated data, replayed identically regardless of what the scheduler does. That holds for exogenous state (channel/CQI, mobility, arrivals) but breaks for buffer occupancy: what's in a UE's buffer at TTI *n* depends on what was scheduled at TTI *n-1*. If buffer state is pre-baked independent of scheduling decisions, algorithms are evaluated against a trajectory that assumes neither of them actually ran, and "replaying the same scenario against two schedulers" stops meaning the same thing for both.
- **Scheduler statefulness is not addressed.** Proportional Fair needs a running average of per-UE throughput; Round Robin needs to remember who was served last. Both are inherently stateful across TTIs, but the current contract description ("given state, return a decision") reads as a pure function. Left unresolved, every implementer (including AI-generated ones) will invent their own ad hoc way of carrying state.
- **No shared domain model.** "Scenario," "network state," "allocation decision," "UE," "resource block," "QoS class" are referenced by name in four different module docs, but no module is declared the owner of these types. Without one canonical definition, each module or algorithm author can informally invent its own shape for these concepts, quietly reintroducing the coupling the architecture is trying to avoid.
- **Scenario materialization is unaddressed.** If `scenario_generator` produces a fully materialized "network state over time" structure, scalability benchmarking (an explicit project goal) will be memory-bound before it is compute-bound at any serious UE/TTI count. Whether scenarios are streamed/iterated lazily or generated in full upfront is undecided.
- **Benchmark methodology is unspecified.** "Measure execution time, CPU, memory" is not itself a methodology — reliable measurement needs repetition, warm-up handling, variance/statistical reporting, and ideally process isolation. As currently described, `benchmark` could be satisfied by a single untrusted timing run, which would not produce numbers comparable across algorithms.
- **No parallelization story.** Comparing N algorithms × M scenarios × K repetitions is embarrassingly parallel, but nothing states whether scheduler instances are required to be stateless *between* scenario runs (even if stateful *within* one), which is what would make runs safely parallelizable.
- **Duplicated caveats across documents.** The "language/tooling not yet decided" note is repeated in `README.md`, `CLAUDE.md`, and `docs/architecture.md`. Not incorrect, but it is three places to remember to update once a language is chosen.
- **No durable record of design reasoning.** `CLAUDE.md` commits to explaining the reasoning behind each design decision before implementing it, but there is no ADR (architecture decision record) log — that reasoning currently only lives in chat history and will be lost over time.

## Missing modules

- **Simulation loop / runner.** Something has to step through TTIs, hand state to the scheduler, apply the decision to update decision-dependent state (buffers, HARQ), and hand off to `benchmark`/`tests`. No module currently owns this. If `benchmark` and `tests` each reimplement it independently, they risk diverging on what "running a scenario" means.
- **Core/domain module.** A place to canonically define the shared data model (UE, resource block, scenario snapshot, allocation decision, QoS class) that `scenario_generator`, `scheduling_interface`, and `reference_implementations` all depend on, instead of each module implying its own shape.
- **Metrics/reporting module.** `benchmark` says it "records" throughput, fairness, latency/QoS, execution time, CPU, memory, and scalability, but no module owns how these are computed (e.g., which fairness index), what output format results take, or how runs are persisted and compared over time. For a framework whose purpose is comparing algorithms, this is currently the least specified part of the pipeline despite being the deliverable.
- **Conformance/validation gate for scheduling_interface implementations.** No module verifies that a given implementation (human-written or AI-generated) respects basic invariants — e.g., never allocates more resource blocks than exist, never double-allocates a block, returns a decision for every UE/TTI in scope — before it is trusted in `benchmark` or admitted to `reference_implementations`.
- **Support surface for AI-generated algorithms.** This is a stated project goal but has no corresponding module or design placeholder — nothing distinguishes trusted reference implementations from generated ones in terms of validation or resource/time limits when they are executed and benchmarked.
- **ADR log (`docs/adr/`).** No location exists to record *why* significant decisions were made (e.g., open-loop vs. closed-loop, interface shape), as distinct from `docs/architecture.md`, which records the current state.
- **Project governance files.** No `LICENSE` or `CONTRIBUTING.md` — expected eventually for a framework intended to accept outside or AI-generated algorithm contributions, though not urgent at this stage.

## Testing gaps

- **No conformance/contract test suite.** Beyond per-algorithm functional tests, a framework meant to accept third-party and AI-generated implementations needs a shared test suite that every `scheduling_interface` implementation must pass (capacity constraints, determinism, total-allocation invariants). This matters more here than in most projects given the AI-generation goal.
- **No invariant/property-based testing strategy.** Fixed-input/expected-output tests catch known cases only; scheduling correctness properties (e.g., "no resource block is double-allocated," "every UE with nonzero buffer eventually gets served under Round Robin") are better suited to property-based or randomized testing, which is not currently planned.
- **No end-to-end pipeline test.** All testing described in `tests/README.md` is per-module. Nothing validates the full `scenario_generator → scheduler → benchmark` pipeline together, which is exactly where the open-loop/closed-loop ambiguity would surface as a bug.
- **No performance-regression tracking.** `benchmark` produces numbers, but nothing tracks them over time to catch regressions in reference implementations as the framework evolves.
- **Test fixture determinism is not operationalized.** `tests/` is described as asserting expected outputs for "fixed, deterministic scenarios," while `scenario_generator` is elsewhere implied to support randomized generation for benchmarking realism. Nothing currently connects the two — e.g., via seeded generation plus checked-in scenario fixtures — so `tests/` risks hand-rolling data that drifts from what `scenario_generator` actually produces.

## Unresolved decisions

- Open-loop vs. closed-loop simulation: is any part of scenario state (buffer occupancy, HARQ retransmissions) decision-dependent, or is the entire scenario exogenous and pre-generated?
- Scheduler statefulness and lifecycle: is a `scheduling_interface` implementation a stateful object with a lifecycle (e.g., reset between runs, step per TTI), or a pure function with externally carried state?
- Ownership of the domain model and the simulation loop: one module, or two separate ones?
- How AI-generated algorithms are validated and safely executed/benchmarked (conformance checks, resource/time limits) as distinct from trusted reference implementations.
- Benchmark measurement methodology: repetition count, warm-up handling, variance reporting, process isolation.
- Scenario materialization strategy: fully generated upfront vs. streamed/iterated lazily, given scalability is an explicit goal.
- Parallelization assumptions: whether scheduler instances/runs are required to be independent so benchmark runs can be safely parallelized.
- Implementation language and stack (deliberately deferred until the above are resolved, since interface shape has real implications for language fit).

## Recommended order of resolution

1. Decide open-loop vs. closed-loop simulation — this drives the shape of `scheduling_interface` and the simulation loop, and therefore most other decisions.
2. Decide scheduler statefulness and lifecycle.
3. Assign ownership of the domain model and the simulation loop (likely the same module).
4. Sketch, still language-agnostically, what a conformance test suite checks — this doubles as the practical definition of "correctly implements `scheduling_interface`," and is a prerequisite for supporting AI-generated algorithms safely.
5. Only then: select the implementation language and stack, since the interface shape (stateful objects vs. pure functions, streaming vs. batch) has real implications for which languages are a good fit.
