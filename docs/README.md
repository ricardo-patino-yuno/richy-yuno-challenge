# Documentation Index

This directory contains the full documentation trail for the Remessas Global Payment Screening API — from initial research through implementation.

## Documents (in chronological order)

### 1. [Research](01-research.md)
Deep analysis of the challenge specification. Covers:
- Business context and compliance domain concepts (sanctions, PEPs, structuring, velocity)
- Functional requirements breakdown (screening endpoint, historical analysis)
- Decision logic analysis
- Acceptance criteria and evaluation rubric mapping
- Risk assessment and time budget

### 2. [Plan Comparison](02-plan-comparison.md)
Side-by-side comparison of three implementation approaches:
- Plan A: Python + FastAPI (recommended)
- Plan B: Go + Gin
- Plan C: TypeScript + Express

Includes scoring projections, development speed analysis, and head-to-head comparisons across 6 dimensions.

### 3. Implementation Plans
Detailed implementation plans for each stack:
- [Plan A: Python + FastAPI](03-plan-a-python-fastapi.md) — **Selected plan**. Includes the detailed TODO list, agent orchestration strategy, dependency graph, and all checklists (acceptance criteria, deliverables, rubric).
- [Plan B: Go + Gin](03-plan-b-go-gin.md)
- [Plan C: TypeScript + Express](03-plan-c-typescript-express.md)

### 4. [AI Session Report](04-ai-session-report.md)
Documents the full AI-assisted build process:
- Prompt-by-prompt breakdown of the session
- Agent architecture (3 agents + orchestrator)
- Parallelism strategy and execution timeline
- Bugs found and fixed during integration testing
- Prompting techniques that worked

## Other Documentation

| File | Location | Purpose |
|------|----------|---------|
| [README.md](../README.md) | Project root | Setup, API reference, architecture decisions, how to test |
| [CLAUDE.md](../CLAUDE.md) | Project root | AI assistant context file (project overview, key files, conventions) |
