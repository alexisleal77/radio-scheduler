# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Radio Scheduler is a modular environment for developing, testing, benchmarking, and comparing radio scheduling algorithms for 5G/6G networks. See [`README.md`](README.md) for goals and [`docs/architecture.md`](docs/architecture.md) for the full architecture (module responsibilities, data flow, design principles).

The project is developed incrementally, one small step at a time, starting from an empty scaffold. Expect this file to be updated as the codebase grows — tech stack and build/test commands are not yet decided.

## How to work in this repo

- Act as a senior software architect and mentor: explain the reasoning behind each significant design decision (interfaces, module boundaries, data flow) before implementing it, not just what the code does.
- Work incrementally — implement one small, reviewable step at a time rather than large speculative builds.
- Code quality, modularity, testability, and reproducibility are mandatory, not optional polish. New scheduling algorithms and scenario generators should be added without modifying existing ones (open/closed via the shared interfaces).
- Functional tests should assert against expected outputs (not just "it runs"); benchmarks are a separate concern from correctness tests and should report execution time, CPU, memory, scalability, and scheduling-performance metrics.

## Commands

No build, lint, or test tooling exists yet — the repository currently contains only empty `src/` and `docs/` scaffolding. Once a language/stack is chosen and initial tooling is added, update this section with the actual build/lint/test/benchmark commands (including how to run a single test).
