"""Stable file-asset lookup contracts for business modules."""

import uuid
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class FileAssetSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    original_name: str
    content_type: str | None = None
    size: int


class FileAssetDirectory(Protocol):
    def get_accessible_file(
        self, *, tenant_id: uuid.UUID, file_id: uuid.UUID
    ) -> FileAssetSummary | None: ...
