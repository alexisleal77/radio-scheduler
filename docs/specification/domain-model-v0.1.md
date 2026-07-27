# Domain Model v0.1

## Purpose

This document canonically defines the shared domain model for Radio Scheduler — the core entities and relationships that every module (`scenario_generator`, `scheduling_interface`, `reference_implementations`, the Simulation Loop, `benchmark`, `tests`) depends on. Without a single canonical definition, each module or algorithm author could informally invent its own shape for concepts like UE, resource block, or allocation decision, reintroducing the coupling the architecture is designed to avoid. This document is the single source of truth for those shared concepts.

## Scope

This document defines domain concepts conceptually and language-agnostically: entities, their fields, and how they relate to one another. It covers the boundary between state that is independent of any scheduling decision and state that results from one, as well as parameters that shape how decisions are applied over time. It does not cover the implementation language, concrete schema definitions, module or directory ownership of these types, or the scheduler statefulness/lifecycle question — these remain separate, open decisions.

## Design Principles

1. **Single canonical ownership.** Every domain concept is defined exactly once, in this document. No component may reinvent or extend its shape locally.

2. **Entities represent domain concepts, not implementation artifacts.** Every entity in this model must correspond to something a domain expert would recognize as real — not to internal bookkeeping, loop indices, or other accidents of a particular implementation.

3. **Entities are pure data.** No behavior, methods, or embedded logic; every entity is representable as plain structured data, independent of any programming language, framework, platform, or serialization format.

4. **Determinism as an intrinsic property of the data.** The value of an entity must be entirely traceable from information contained in the model itself (parameters, seeds, or references to other entities) — never from computation or state hidden outside the model.

5. **Minimal and additive vocabulary.** Define only the entities genuinely required by the domain itself; evolve by adding new fields or entities, never by changing the meaning of existing ones.

## Core Entities

This section defines the concepts of the Radio Scheduler domain and how they relate to one another. Attribute-level detail and the Entity/Value Object/other-pattern classification for each concept are deliberately deferred to a later revision of this document.

**Scenario** — A specific network operating condition (traffic load, mobility, and channel profile), generated independently of any scheduling decision, spanning a fixed sequence of TTIs. A Scenario is the environment a Run evaluates a Scheduler against.

**TTI (Transmission Time Interval)** — The discrete unit of time the domain is organized around. Every time-varying concept in a Scenario or Run is indexed by a TTI.

**Channel Quality** — The condition of a UE's radio channel at a given TTI. Part of a Scenario; independent of any scheduling decision.

**Traffic Arrival** — New data entering a UE's Buffer at a given TTI. Part of a Scenario; independent of any scheduling decision.

**UE (User Equipment)** — A device being scheduled. Persists across the TTIs of a Scenario/Run, carrying a QoS Class, a Buffer, and a HARQ State, which evolve over time as decisions are applied.

**QoS Class** — The service-level classification of a UE, describing its priority or performance requirements.

**Buffer** — The accumulated, unsent data queued for a UE. Its value at a given TTI depends on prior Traffic Arrivals and prior AllocationDecisions.

**HARQ State** — The outstanding retransmission need for a UE, resulting from a prior transmission that failed or was not scheduled.

**Resource Block** — A schedulable unit of radio capacity available at a given TTI.

**Run** — One execution of a Scheduler against a Scenario, producing a sequence of AllocationDecisions and a resulting Scheduling Performance Metric. Ties a Scenario and a Scheduler together for comparison.

**Scheduler** — The identity of a scheduling algorithm being evaluated (e.g., Round Robin, Proportional Fair, MaxCQI, or a future AI-generated algorithm).

**AllocationDecision** — The outcome produced by a Scheduler for a given TTI within a Run: an assignment of Resource Blocks to UEs.

**Scheduling Performance Metric** — A measure (e.g., throughput, fairness, latency/QoS satisfaction) summarizing how well a Scheduler performed over the course of a Run.

### Relationships

```
Scenario
 ├─ TTI
 │   ├─ Channel Quality  (per UE, per TTI)
 │   └─ Traffic Arrival  (per UE, per TTI)
 ├─ UE
 │   ├─ QoS Class
 │   ├─ Buffer
 │   └─ HARQ State
 └─ Resource Block

Run
 ├─ references a Scenario
 ├─ references a Scheduler
 ├─ produces a sequence of AllocationDecision (one per TTI)
 │   └─ AllocationDecision references TTI + UE(s) + Resource Block(s)
 └─ produces a Scheduling Performance Metric
```
