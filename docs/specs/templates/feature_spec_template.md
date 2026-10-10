# Feature Specification: [Feature Name]

- **Status**: Draft | Under Review | Approved | Implemented
- **Author**: [Author / Pair]
- **Date**: [YYYY-MM-DD]
- **Related Issues / PRs**: [Links]

---

## 1. Summary & Problem Statement

### Problem
[Describe the problem or opportunity. What is broken, missing, or inefficient today?]

### Proposed Solution
[High-level overview of the feature from the user or developer perspective.]

### User Stories / Use Cases
- **As a** [user/dispatcher/viewer]
- **I want to** [action]
- **So that** [benefit / outcome]

---

## 2. Scope Boundaries

### In Scope
- [Deliverable 1]
- [Deliverable 2]

### Out of Scope (Deferred)
- [Explicitly excluded item 1]
- [Explicitly excluded item 2]

---

## 3. Data Models & Interface Contracts

### 3.1 Database Schema (SQLModel / PostgreSQL)
```python
# Model additions or diffs in packages/db/src/db/models.py
```

### 3.2 API Endpoint & Schemas (FastAPI / OpenAPI)
- **Endpoint**: `GET /events` | `POST /...`
- **Request Parameters / Body**:
```python
# Pydantic schema in packages/api/schemas.py
```
- **Response Schema**:
```python
# Expected response structure
```

### 3.3 Frontend Contracts & Types (TypeScript)
```typescript
// Derived from packages/web/src/types/api.generated.ts
```

---

## 4. Edge Cases, Failure Modes & Resilience

| Scenario | System Behavior | Expected UX / Feedback |
|---|---|---|
| Network failure / API offline | TanStack Query retry policy triggers | Error state with manual retry button |
| Empty dataset | Returns empty array `[]` | Empty state with friendly prompt |
| Invalid coordinate data | Geocoder returns `None` | Rendered with missing-coords badge |

---

## 5. Executable Acceptance Criteria

### Verification Commands
- [ ] Backend tests pass: `uv run python -m unittest discover packages/api/tests`
- [ ] Contract types generated: `./run-dev.sh spec:types`
- [ ] Web app compiles: `npm run build --prefix packages/web`
- [ ] Full pipeline verified: `./run-dev.sh spec:verify`

### Behavior Checklist
- [ ] Criterion 1: [Specific, testable behavior]
- [ ] Criterion 2: [Specific, testable behavior]
- [ ] Criterion 3: [Specific, testable behavior]
