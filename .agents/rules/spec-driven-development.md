# Spec-Driven Development (SDD) Agent Rule

## Overview
This repository enforces **Spec-Driven Development**. You must adhere to the contract-first lifecycle whenever designing, updating, or implementing features across `packages/api`, `packages/web`, `packages/db`, `packages/migrations`, and `packages/dispatch-consumer`.

## Rules for AI Agents

1. **Check for or Propose a Spec First**:
   - Before implementing any non-trivial user feature or changing endpoints, verify if a specification exists in `docs/specs/features/`.
   - If not, propose or draft one using `docs/specs/templates/feature_spec_template.md`.

2. **Backend is the Source of Truth for API Contracts**:
   - Never manually author or duplicate TypeScript interfaces representing backend models.
   - Define or update schemas in `packages/api/schemas.py` and routers.
   - Run `./run-dev.sh spec:types` to regenerate `packages/web/src/types/api.generated.ts`.
   - Import types in `packages/web` from `@/types/api.generated.ts` or feature type aliases.

3. **Database Model Integrity**:
   - When modifying tables in `packages/db/src/db/models.py`, ensure relationships and foreign keys are reflected in `SQLModel.metadata`.
   - Ensure Alembic migrations are generated when modifying persistent schema.

4. **Verify All Contracts Before Completion**:
   - Always run `./run-dev.sh spec:verify` before declaring any task complete.
   - Zero errors are permitted across tests, contract checks, TypeScript builds, and linters.
