"""One normalized row of the Purchase Request CSV."""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class PurchaseRequestItem(BaseModel):
    pr_number: Optional[str] = None
    item_code: Optional[str] = None
    item_name: str
    unit: Optional[str] = None
    requested_quantity: Decimal
    max_unit_price: Decimal
    currency: Optional[str] = None
