# Changelog

## Unreleased

- Move settings and file management out of `System` into a top-level `Infrastructure` menu placed before `Sample Items`.
- Remove the online-user page and the legacy operations-management module from backend routes, frontend pages, and docs.
- Start v1.2 infrastructure work with S3/MinIO-compatible file storage, private
  pre-signed download URLs, database-table code generation, and a code generation UI.
- Add PRD, TRD, and executable v1.0 implementation plan for the FastAPI + Vben admin baseline.
- Tighten backend RBAC checks, pagination boundaries, tree parent validation, system role/config protection, dictionary uniqueness, audit log filters, and notice message APIs.
- Add frontend permission-controlled toolbar and table actions for users, roles, menus, departments, dictionaries, settings, files, notices, and Items.
- Add reproducible OpenAPI TypeScript generation from the current backend application.
- Add CI gates for generated OpenAPI drift detection and Playwright E2E execution.
- Persist uploaded files in Docker Compose and expose upload settings in `.env.example`.
- Expand backend tests for RBAC, users, files, notices, audit logs, system config, and permission/menu consistency.
- Expand Playwright E2E coverage for login, Items CRUD, user CRUD, file upload/download/delete, notice-to-message flow, and limited-user permissions.
- Add encrypted TOTP MFA setup, verification, and disable flows in the personal security settings.
- Enforce TOTP verification during login for accounts with MFA enabled.
- Add one-time MFA recovery codes and permission-protected administrator MFA reset.

## 0.1.0

- Initialize Fast Vben Admin MVP implementation.
- Add FastAPI backend skeleton.
- Add Vue Vben Admin `web-antd` frontend skeleton.
- Add root environment, Compose, and documentation entry points.
