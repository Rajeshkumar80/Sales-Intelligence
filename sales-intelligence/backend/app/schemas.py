"""Request/response models. All timestamps are stored and returned in UTC."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

TIMESTAMP_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d")


def to_utc(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, str):
        text = value.strip().replace("Z", "+00:00")
        try:
            value = datetime.fromisoformat(text)
        except ValueError:
            for fmt in TIMESTAMP_FORMATS:
                try:
                    value = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError("timestamp must be ISO 8601, e.g. 2026-11-11T09:30:00Z")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class TransactionIn(BaseModel):
    transaction_id: str | None = Field(default=None, max_length=64)
    product_id: str = Field(min_length=1, max_length=32)
    product_name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=60)
    quantity: int = Field(ge=1, le=100_000)
    unit_price: float = Field(ge=0, le=10_000_000)
    region: str = Field(min_length=1, max_length=60)
    timestamp: datetime | None = None

    @field_validator("transaction_id", "product_id", "product_name", "category", "region")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, value):
        return to_utc(value)


class TransactionOut(BaseModel):
    transaction_id: str
    product_id: str
    product_name: str
    category: str
    quantity: int
    unit_price: float
    revenue: float
    region: str
    timestamp: datetime
    source: str
    processed: bool
    batch_id: str | None

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc(cls, value):
        return to_utc(value)


class SimulatorStart(BaseModel):
    interval_seconds: float | None = Field(default=None, ge=1, le=120)
    batch_size: int | None = Field(default=None, ge=1, le=500)


class ProcessRequest(BaseModel):
    batch_size: int | None = Field(default=None, ge=1, le=20_000)
