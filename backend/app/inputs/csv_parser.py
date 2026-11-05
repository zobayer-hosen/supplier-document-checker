"""Parse the Purchase Request CSV.

We do not assume exact column names. Instead each logical field has a list of
accepted header names, and we look for them in the real header row. The
supplied file uses:

    PR number, Item, Description, Unit, Quantity requested, Maximum unit price (BDT)

If a required column cannot be found, we stop with a clear error instead of
guessing which column was meant.
"""

import csv
import io
import re

from app.schemas.purchase_request import PurchaseRequestItem
from app.utils.text import parse_decimal


class PurchaseRequestError(ValueError):
    """The CSV cannot be used. The message explains why."""


# Logical field -> header names we accept (compared lower-case, without
# anything in brackets, so "Maximum unit price (BDT)" -> "maximum unit price").
COLUMN_ALIASES = {
    "pr_number": ["pr number", "pr no", "purchase request number", "pr"],
    "item_code": ["item", "item code", "item id", "item no"],
    "item_name": ["description", "item name", "item description"],
    "unit": ["unit", "uom", "unit of measure"],
    "requested_quantity": ["quantity requested", "requested quantity", "quantity", "qty"],
    "max_unit_price": ["maximum unit price", "max unit price", "max price", "maximum price"],
    "currency": ["currency"],
}
REQUIRED_COLUMNS = ["item_name", "requested_quantity", "max_unit_price"]


def _simplify_header(header: str) -> str:
    without_brackets = re.sub(r"\(.*?\)", "", header)
    return re.sub(r"\s+", " ", without_brackets).strip().casefold()


def _currency_from_header(header: str) -> str | None:
    """Read a currency written in the header, e.g. "Maximum unit price (BDT)" -> "BDT"."""
    match = re.search(r"\(([A-Za-z]{3})\)", header)
    return match.group(1).upper() if match else None


def map_columns(headers: list[str]) -> dict[str, str]:
    """Map each logical field to the real column name found in the CSV."""
    simplified = {_simplify_header(header): header for header in headers}
    column_map: dict[str, str] = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in simplified:
                column_map[field] = simplified[alias]
                break

    missing = [field for field in REQUIRED_COLUMNS if field not in column_map]
    if missing:
        raise PurchaseRequestError(
            f"The Purchase Request CSV is missing required columns: {', '.join(missing)}. "
            f"Columns found: {', '.join(headers)}."
        )
    return column_map


def parse_purchase_request(content: bytes) -> list[PurchaseRequestItem]:
    """Read CSV bytes and return one PurchaseRequestItem per row."""
    try:
        text = content.decode("utf-8-sig")  # "-sig" removes the Excel byte-order mark
    except UnicodeDecodeError as error:
        raise PurchaseRequestError("The Purchase Request CSV must be UTF-8 text.") from error

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise PurchaseRequestError("The Purchase Request CSV is empty.")

    headers = [header.strip() for header in reader.fieldnames]
    reader.fieldnames = headers
    column_map = map_columns(headers)
    header_currency = _currency_from_header(column_map["max_unit_price"])

    items: list[PurchaseRequestItem] = []
    for row_number, row in enumerate(reader, start=2):  # row 1 is the header
        if not any((value or "").strip() for value in row.values()):
            continue  # skip blank lines

        def read(field: str) -> str | None:
            column = column_map.get(field)
            value = (row.get(column) or "").strip() if column else ""
            return value or None

        quantity = parse_decimal(read("requested_quantity"))
        max_price = parse_decimal(read("max_unit_price"))
        item_name = read("item_name")
        if item_name is None or quantity is None or max_price is None:
            raise PurchaseRequestError(
                f"Row {row_number} of the Purchase Request CSV has a missing or "
                "non-numeric description, quantity or maximum unit price."
            )
        if quantity <= 0 or max_price <= 0:
            raise PurchaseRequestError(
                f"Row {row_number}: quantity and maximum unit price must be greater than zero."
            )

        items.append(
            PurchaseRequestItem(
                pr_number=read("pr_number"),
                item_code=read("item_code"),
                item_name=item_name,
                unit=read("unit"),
                requested_quantity=quantity,
                max_unit_price=max_price,
                currency=(read("currency") or header_currency),
            )
        )

    if not items:
        raise PurchaseRequestError("The Purchase Request CSV has a header but no item rows.")

    codes = [item.item_code for item in items if item.item_code]
    if len(codes) != len(set(codes)):
        raise PurchaseRequestError("The Purchase Request CSV lists the same item code more than once.")
    return items
