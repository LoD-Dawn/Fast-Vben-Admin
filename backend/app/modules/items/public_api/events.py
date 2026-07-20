import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ItemChangedV1(BaseModel):
    """Versioned public event schema for an Item lifecycle change."""

    model_config = ConfigDict(frozen=True)

    item_id: uuid.UUID
    tenant_id: uuid.UUID
    owner_id: uuid.UUID
    action: Literal["created", "updated", "deleted"]
    occurred_at: datetime
