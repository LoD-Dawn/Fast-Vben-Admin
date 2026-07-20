import hashlib
import json
import os
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

import yaml
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, Field

from app.modules.capabilities import validate_capability_requirements
from app.modules.contracts import ModuleDefinition
from app.modules.registry import get_module_definitions

EDITION_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")


class ManifestModule(BaseModel):
    code: str
    version: str
    migration_namespace: str
    migration_heads: list[str] = Field(default_factory=list)
    openapi_sha256: str


class BuildManifest(BaseModel):
    schema_version: Literal[2] = 2
    edition: str
    source_revision: str
    platform_contract_version: int = 1
    platform_version: str
    modules: list[ManifestModule] = Field(default_factory=list)
    manifest_digest: str

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "edition": self.edition,
            "source_revision": self.source_revision,
            "platform_contract_version": self.platform_contract_version,
            "platform_version": self.platform_version,
            "modules": [module.model_dump() for module in self.modules],
        }

    def public_payload(self) -> dict[str, object]:
        return self.model_dump()


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def editions_directory() -> Path:
    return repository_root() / "editions"


def _canonical_json(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def manifest_digest(payload: Mapping[str, object]) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(payload)).hexdigest()}"


def sha256_digest(payload: Mapping[str, object]) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(payload)).hexdigest()}"


def source_revision() -> str:
    """Return the commit that produced the artifact, with an explicit CI override."""
    configured = os.environ.get("SOURCE_REVISION")
    if configured:
        return configured
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root(),
        check=False,
        capture_output=True,
        text=True,
    )
    revision = result.stdout.strip()
    if result.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Unable to determine source revision; set SOURCE_REVISION")
    return revision


def module_migration_heads(*, namespace: str) -> list[str]:
    config = Config(str(repository_root() / "backend" / "alembic.ini"))
    if namespace != "platform":
        config.set_main_option(
            "script_location",
            str(repository_root() / "backend" / "app" / "modules" / namespace / "migrations"),
        )
    return sorted(ScriptDirectory.from_config(config).get_heads())


def module_openapi_sha256(definition: ModuleDefinition) -> str:
    """Hash the module's public OpenAPI surface without constructing the app lifespan."""
    api = FastAPI(openapi_url=None)
    router = APIRouter()
    for module_router in definition.routers:
        router.include_router(module_router)
    api.include_router(router, prefix="/api/v1")
    return sha256_digest(api.openapi())


def load_edition_modules(*, edition: str, directory: Path | None = None) -> list[str]:
    if not EDITION_NAME_PATTERN.fullmatch(edition):
        raise ValueError(f"Invalid edition name: {edition!r}")

    edition_path = (directory or editions_directory()) / f"{edition}.yaml"
    if not edition_path.is_file():
        raise ValueError(f"Edition file does not exist: {edition_path}")

    loaded = yaml.safe_load(edition_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Edition file must contain an object: {edition_path}")
    if loaded.get("name") != edition:
        raise ValueError(f"Edition name does not match its filename: {edition_path}")

    modules = loaded.get("modules")
    if not isinstance(modules, list) or not modules or not all(
        isinstance(module, str) for module in modules
    ):
        raise ValueError(f"Edition modules must be a non-empty list: {edition_path}")
    if len(modules) != len(set(modules)):
        raise ValueError(f"Edition contains duplicate modules: {edition_path}")
    return modules


def resolve_module_definitions(
    module_codes: list[str],
    definitions: Mapping[str, ModuleDefinition] | None = None,
) -> list[ModuleDefinition]:
    available = definitions or get_module_definitions()
    resolved: list[ModuleDefinition] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(code: str) -> None:
        if code in visited:
            return
        if code in visiting:
            raise ValueError(f"Module dependency cycle detected at: {code}")
        definition = available.get(code)
        if definition is None:
            raise ValueError(f"Edition references an unknown module: {code}")
        visiting.add(code)
        for dependency in definition.dependencies:
            visit(dependency)
        visiting.remove(code)
        visited.add(code)
        resolved.append(definition)

    for module_code in module_codes:
        visit(module_code)
    return resolved


def build_manifest(
    *,
    edition: str,
    directory: Path | None = None,
    definitions: Mapping[str, ModuleDefinition] | None = None,
    source_revision_override: str | None = None,
) -> BuildManifest:
    module_codes = load_edition_modules(edition=edition, directory=directory)
    resolved = resolve_module_definitions(module_codes, definitions)
    validate_capability_requirements(resolved)
    platform = next((definition for definition in resolved if definition.code == "platform"), None)
    if platform is None:
        raise ValueError("Every edition must include the platform module")

    source = source_revision_override or source_revision()
    manifest_modules = [
        ManifestModule(
            code=definition.code,
            version=definition.version,
            migration_namespace=definition.migration.namespace,
            migration_heads=module_migration_heads(
                namespace=definition.migration.namespace
            ),
            openapi_sha256=module_openapi_sha256(definition),
        )
        for definition in resolved
    ]
    payload: dict[str, object] = {
        "schema_version": 2,
        "edition": edition,
        "source_revision": source,
        "platform_contract_version": 1,
        "platform_version": platform.version,
        "modules": [module.model_dump() for module in manifest_modules],
    }
    return BuildManifest(**payload, manifest_digest=manifest_digest(payload))


def load_manifest_file(path: Path) -> BuildManifest:
    try:
        manifest = BuildManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Unable to read build manifest: {path}") from exc

    expected_digest = manifest_digest(manifest.canonical_payload())
    if manifest.manifest_digest != expected_digest:
        raise ValueError(f"Build manifest digest does not match: {path}")

    expected = build_manifest(
        edition=manifest.edition,
        source_revision_override=manifest.source_revision,
    )
    if manifest != expected:
        raise ValueError(f"Build manifest does not match the current module definitions: {path}")
    return manifest


def write_manifest(*, edition: str, output: Path) -> BuildManifest:
    manifest = build_manifest(edition=edition)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest.public_payload(), ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
