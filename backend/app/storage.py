"""Deprecated compatibility import for Platform storage infrastructure."""

from app.platform.infra.storage import (
    _ensure_s3_bucket,
    _get_s3_client,
    copy_file_to_uploads,
    delete_local_file,
    delete_stored_file,
    get_default_storage_channel,
    get_file_download_response,
    get_presigned_download_url,
    get_presigned_url_expire_seconds,
    get_upload_allowed_extensions,
    get_upload_default_public,
    get_upload_max_size_mb,
    save_upload_file,
)

__all__ = [
    "_ensure_s3_bucket",
    "_get_s3_client",
    "copy_file_to_uploads",
    "delete_local_file",
    "delete_stored_file",
    "get_default_storage_channel",
    "get_file_download_response",
    "get_presigned_download_url",
    "get_presigned_url_expire_seconds",
    "get_upload_allowed_extensions",
    "get_upload_default_public",
    "get_upload_max_size_mb",
    "save_upload_file",
]
