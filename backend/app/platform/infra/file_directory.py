"""Platform implementation of the public file-asset directory."""

import uuid

from sqlmodel import Session, select

from app.platform.infra.file_models import FileAsset
from app.platform.public_api.files import FileAssetSummary


class SqlFileAssetDirectory:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_accessible_file(
        self, *, tenant_id: uuid.UUID, file_id: uuid.UUID
    ) -> FileAssetSummary | None:
        asset = self._session.exec(
            select(FileAsset).where(
                FileAsset.id == file_id,
                FileAsset.tenant_id == tenant_id,
            )
        ).first()
        if asset is None:
            return None
        return FileAssetSummary(
            id=asset.id,
            original_name=asset.original_name,
            content_type=asset.content_type,
            size=asset.size,
        )
