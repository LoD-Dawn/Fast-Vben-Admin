"""Provision the non-superuser database role used by application processes."""

import os
import re

import psycopg
from psycopg import sql

from app.core.config import settings

ROLE_NAME_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
SCHEMAS = ("public", "items", "erp")


def runtime_role_credentials() -> tuple[str, str]:
    username = os.environ.get("APP_RUNTIME_DB_USER", "").strip()
    password = os.environ.get("APP_RUNTIME_DB_PASSWORD", "")
    if not ROLE_NAME_PATTERN.fullmatch(username):
        raise ValueError("APP_RUNTIME_DB_USER must be a valid PostgreSQL role name")
    if not password:
        raise ValueError("APP_RUNTIME_DB_PASSWORD must be configured")
    return username, password


def schema_exists(cursor: psycopg.Cursor[object], schema: str) -> bool:
    cursor.execute("SELECT to_regnamespace(%s) IS NOT NULL", (schema,))
    return cursor.fetchone() == (True,)


def table_exists(cursor: psycopg.Cursor[object], qualified_table: str) -> bool:
    cursor.execute("SELECT to_regclass(%s) IS NOT NULL", (qualified_table,))
    return cursor.fetchone() == (True,)


def grant_schema_access(
    cursor: psycopg.Cursor[object], *, schema: str, runtime_role: str
) -> None:
    if not schema_exists(cursor, schema):
        return
    schema_identifier = sql.Identifier(schema)
    role_identifier = sql.Identifier(runtime_role)
    cursor.execute(
        sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
            schema_identifier, role_identifier
        )
    )
    cursor.execute(
        sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {} TO {}").format(
            schema_identifier, role_identifier
        )
    )
    cursor.execute(
        sql.SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {} TO {}").format(
            schema_identifier, role_identifier
        )
    )
    cursor.execute(
        sql.SQL(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA {} "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}"
        ).format(schema_identifier, role_identifier)
    )
    cursor.execute(
        sql.SQL(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA {} "
            "GRANT USAGE, SELECT ON SEQUENCES TO {}"
        ).format(schema_identifier, role_identifier)
    )


def restrict_immutable_erp_table_access(
    cursor: psycopg.Cursor[object], *, runtime_role: str
) -> None:
    if not schema_exists(cursor, "erp"):
        return
    for table in ("erp.stock_ledger", "erp.document_action_log"):
        if table_exists(cursor, table):
            cursor.execute(
                sql.SQL("REVOKE UPDATE, DELETE ON {} FROM {}").format(
                    sql.SQL(table), sql.Identifier(runtime_role)
                )
            )


def provision_runtime_role() -> None:
    runtime_role, password = runtime_role_credentials()
    connection_string = str(settings.SQLALCHEMY_DATABASE_URI).replace(
        "postgresql+psycopg://", "postgresql://", 1
    )
    with psycopg.connect(connection_string, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (runtime_role,))
            if cursor.fetchone() is None:
                cursor.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                        "NOCREATEROLE NOINHERIT NOBYPASSRLS"
                    ).format(sql.Identifier(runtime_role), sql.Literal(password))
                )
            else:
                cursor.execute(
                    sql.SQL(
                        "ALTER ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                        "NOCREATEROLE NOINHERIT NOBYPASSRLS"
                    ).format(sql.Identifier(runtime_role), sql.Literal(password))
                )

            cursor.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(settings.POSTGRES_DB),
                    sql.Identifier(runtime_role),
                )
            )
            for schema in SCHEMAS:
                grant_schema_access(
                    cursor,
                    schema=schema,
                    runtime_role=runtime_role,
                )
            restrict_immutable_erp_table_access(cursor, runtime_role=runtime_role)


def main() -> None:
    provision_runtime_role()


if __name__ == "__main__":
    main()
