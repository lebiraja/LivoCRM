# LivoCRM Codebase Documentation Index

This folder now includes a full codebase documentation set generated from the current implementation.

## Documents
- `docs/ARCHITECTURE_OVERVIEW.md`
  - System architecture, runtime topology, service boundaries, and key integration notes.

- `docs/BACKEND_DOCUMENTATION.md`
  - FastAPI architecture, auth flow, router/endpoint inventory, migration flow, backend gaps.

- `docs/FRONTEND_DOCUMENTATION.md`
  - React app structure, routing, state stores, API client layer, UI behavior, contract gaps.

- `docs/DATABASE_SCHEMA_AND_ERD.md`
  - Table-by-table schema details, FK/delete behavior, and Mermaid ER diagram.

## Source Coverage Used
- Backend source in `backend/app/**`
- Migrations in `backend/alembic/**`
- ML scripts in `backend/ml/**`
- Frontend source in `frontend/src/**`
- Infra/runtime config in `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `.env.example`

## Important Note
This documentation intentionally reflects the code as-is, including current frontend-backend contract mismatches and partially implemented flows.
