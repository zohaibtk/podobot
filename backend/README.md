# Backend

The backend provides the production workflow API for PodoBot.

## Capabilities

- FastAPI application with PostgreSQL sessions and Alembic migrations.
- JWT access-token authentication and server-side permission enforcement.
- Workspace settings, users, roles, permissions, and audit logs.
- Series workflow modules from discovery through scheduling.
- Local file storage for recording assets and transcripts.
- Integration health, masked API keys, and critical integration blocking.
- AI agent registry, prompt registry, agent runs, validation, and audit logs.
- MCP server/tool registry, tool execution runs, retry, circuit breaker foundation, and audit logs.

## Setup

```bash
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Tests

```bash
cd backend
../.venv/bin/python -m pytest
../.venv/bin/python -m ruff check app tests
```

## Environment Notes

- `auth_jwt_secret` must be replaced outside development.
- `auth_dev_auto_login` must remain disabled outside local test/development runs.
- `auth_dev_admin_password` seeds the development admin password if an admin is not configured.
- `local_storage_root` controls filesystem asset storage.
- `database_url_override` can replace the composed PostgreSQL URL.

## Auth And RBAC

All product routes should be protected server-side. Frontend route guards only improve user
experience and must not be treated as security controls.

Default roles:

- Admin: all default permissions.
- Producer: production workflow permissions, excluding admin/security settings.
- Viewer: read-oriented permissions.

## AI And MCP Notes

Agents call tools through MCP where integrations are involved. MCP runs redact sensitive input
and metadata before response/audit exposure. Real third-party clients should be added behind MCP
adapters rather than inside workflow services.
