from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel


def to_json_value(value: Any) -> Any:
    """Convert Decimal, UUID, dates and Pydantic models so they can be stored as JSON.

    Decimals become strings ("472.00") so no precision is lost.
    """
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (UUID, datetime, date)):
        return str(value)
    if isinstance(value, dict):
        return {key: to_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_json_value(item) for item in value]
    return value
