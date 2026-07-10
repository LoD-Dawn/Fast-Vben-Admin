# Changelog

## Unreleased

- Add PRD, TRD, and executable v1.0 implementation plan for the FastAPI + Vben admin baseline.
- Tighten backend RBAC checks, pagination boundaries, tree parent validation, system role/config protection, dictionary uniqueness, audit log filters, and notice message APIs.
- Add frontend permission-controlled toolbar and table actions for users, roles, menus, departments, dictionaries, settings, files, notices, and Items.
- Add reproducible OpenAPI TypeScript generation from the current backend application.
- Persist uploaded files in Docker Compose and expose upload settings in `.env.example`.
- Expand backend tests for RBAC, users, files, notices, audit logs, system config, and permission/menu consistency.
- Expand Playwright E2E coverage for login, Items CRUD, user CRUD, file upload/download/delete, notice-to-message flow, and limited-user permissions.

## 0.1.0

- Initialize Fast Vben Admin MVP implementation.
- Add FastAPI backend skeleton.
- Add Vue Vben Admin `web-antd` frontend skeleton.
- Add root environment, Compose, and documentation entry points.
