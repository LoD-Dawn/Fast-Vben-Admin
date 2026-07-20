from datetime import UTC, datetime


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)
