# Living Spec-Driven Development (SDD) Agent Rule

## Overview
This repository enforces **Living Spec-Driven Development** across `packages/api`, `packages/web`, `packages/db`, `packages/migrations`, and `packages/dispatch-consumer`. Every active feature owns one present-tense specification under `docs/specs/features/<slug>.md`, updated in place whenever behavior changes.

## Rules for AI Agents

1. **Locate & Update Living Specs In Place**:
   - **Modifying an existing capability**: Find the owning spec in `docs/specs/README.md` (Feature Catalog) or by matching `source_files` across `docs/specs/features/*.md`. Read it before editing code, and update that spec **in place** in the same branch/change so requirements, interfaces, edge cases, `source_files`, and `tests` accurately describe the updated steady state in present tense.
   - **Adding a new capability**: Create `docs/specs/features/<kebab-slug>.md` (no numeric prefixes like `001-`) from `docs/specs/templates/feature_spec_template.md`, register it in the Feature Catalog in `docs/specs/README.md`, and keep `source_files`/`tests` exact.
   - **Retiring a capability**: Delete its `docs/specs/features/<slug>.md` file and remove its row from `docs/specs/README.md` (do not create `"retire-*"` spec files).
   - **Shared architecture & schema changes**: Update `docs/specs/architecture.md` whenever database tables, system topology, contract sync, or SPA hosting change.

2. **Backend is the Source of Truth for API Contracts**:
   - Never manually author or duplicate TypeScript interfaces representing backend models.
   - Define or update schemas in `packages/api/schemas.py` and routers.
   - Run `./run-dev.sh spec:types` to regenerate `packages/web/src/types/api.generated.ts`.
   - Import types in `packages/web` from `@/types/api.generated.ts` or feature type aliases.

3. **Database Model Integrity**:
   - When modifying tables in `packages/db/src/db/models.py`, ensure relationships and foreign keys are reflected in `SQLModel.metadata`.
   - Generate and verify Alembic migrations in `packages/migrations` when modifying persistent schema, and keep `docs/specs/architecture.md` synchronized.

4. **Verify Specs & Contracts Before Completion**:
   - Always run `./run-dev.sh spec:verify` before declaring any task complete.
   - Zero errors are permitted across `./run-dev.sh spec:check` (spec structure, catalog sync, `source_files`, and links), Python unit tests, OpenAPI/TypeScript contract sync, TypeScript builds, and linters.
