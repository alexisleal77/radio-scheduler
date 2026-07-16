# Architecture Decision Records

This directory contains the Architecture Decision Records (ADRs) for Radio Scheduler.

## What is an ADR

An ADR is a short document that captures a single architecturally significant decision: the problem that forced it, the options that were weighed, the option chosen, and the consequences of that choice. Unlike `docs/architecture.md`, which describes the *current* state of the architecture, an ADR is a historical record — it is not rewritten as the system evolves. When a decision changes, a new ADR supersedes the old one; the old one stays as-is for context.

## When an ADR should be created

Create an ADR when a decision has architectural impact: it affects module boundaries, the `scheduling_interface` contract, data flow between modules, reproducibility guarantees, or would be expensive to reverse once implementation exists. Examples from this project's open questions: open-loop vs. closed-loop simulation, scheduler statefulness, ownership of the shared domain model, or the implementation language.

Do not create an ADR for decisions that are easily reversible, purely local to one file, or that don't require weighing alternatives (see "Only architecturally significant decisions" below).

## ADR lifecycle

Each ADR has a status, recorded at the top of the document:

- **Proposed** — the decision is written up and under discussion; not yet acted on.
- **Accepted** — the decision is adopted and should be treated as current guidance.
- **Superseded** — the decision was later replaced by another ADR. The document is kept for history and must link to the ADR that supersedes it.
- **Rejected** — the decision was considered and explicitly not adopted. Kept for history so the option isn't re-litigated without new information.

Status changes are recorded in the ADR itself (e.g., "Superseded by ADR-005"); ADRs are otherwise not edited after acceptance.

## File naming convention

`ADR-NNN-short-kebab-case-title.md`, where `NNN` is a zero-padded, sequential, never-reused number (e.g., `ADR-001-open-loop-vs-closed-loop-simulation.md`). Numbers are assigned in the order ADRs are created, regardless of status. `ADR-000-template.md` is the template and is not itself a decision record.

## Only architecturally significant decisions

Not every choice needs an ADR. Reserve them for decisions that shape the architecture and would be costly to change later — module boundaries, interface contracts, data flow, reproducibility, and similar structural choices. Implementation details, naming, and easily reversible choices belong in code, code review, or regular documentation instead.
