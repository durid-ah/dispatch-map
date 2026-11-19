---
feature: <kebab-case-slug>
title: <Human-Readable Feature Title>
status: active # active | experimental | deprecated
packages:
  - packages/api
  - packages/web
source_files:
  - packages/api/routers/<router>.py
  - packages/web/src/features/<feature>/components/<component>.tsx
tests:
  - packages/api/tests/<test_file>.py
---

# <Human-Readable Feature Title>

<!--
  Living Specification Guidelines:
  - Write strictly in the present tense describing how the feature works today.
  - Do not include historical "Problem / Proposed Solution" RFC framing or one-off implementation phase checklists.
  - Keep `source_files` and `tests` exact (individual repo-relative paths, no globs or brace expansions).
  - Update this file in place in the same branch/PR whenever the feature changes.
-->

## 1. Overview

[Summarize what this capability does today, who interacts with it, and how it fits into Dispatch Map.]

## 2. Requirements & Behavior

[Document the concrete, testable rules, user workflows, polling/caching intervals, sorting/filtering behavior, and UI states currently implemented.]

- [Behavior or invariant 1]
- [Behavior or invariant 2]

## 3. Interfaces & Contracts

- **API Endpoints & Schemas**: [Routes, query/path parameters, response codes, and Pydantic/SQLModel schema names in `packages/api/schemas.py` and `packages/api/openapi.json`.]
- **Database & Domain Models**: [Tables, columns, and invariants touched; reference the canonical schema in [architecture.md](../architecture.md).]
- **Frontend Contracts & Components**: [Derived types in `packages/web/src/types/api.generated.ts`, TanStack Query keys/hooks, and UI components.]

## 4. Edge Cases & Failure Modes

| Scenario | System Behavior | Expected Outcome / UX |
|---|---|---|
| [Failure mode or boundary input] | [Backend/consumer handling] | [Returned status, fallback, or UI feedback] |

## 5. Verification

- **Automated Tests**: [Exact test files (`tests` frontmatter) and commands (e.g., `./run-dev.sh spec:verify`).]
- **Manual Checks**: [Key interactive or visual verification steps, if applicable.]
