import sqlite3
from typing import Iterable

from eth_utils import to_checksum_address

from contextswap.platform.db import models


class NotFoundError(RuntimeError):
    pass


def _normalize_keywords(keywords: list[str] | str | None) -> list[str]:
    if keywords is None:
        return []
    items: Iterable[str]
    if isinstance(keywords, str):
        cleaned = keywords.replace(",", " ")
        items = cleaned.split()
    else:
        items = keywords
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        token = (item or "").strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result


def _keywords_to_text(keywords: list[str]) -> str:
    return ",".join(keywords)


def _keywords_from_text(text: str) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    return [token for token in raw.split(",") if token]


def _normalize_seller_id(evm_address: str) -> str:
    return to_checksum_address(evm_address)


def _normalize_price(value: int | None) -> int | None:
    if value is None:
        return None
    value = int(value)
    if value <= 0:
        return None
    return value


def _format_units(value: int, decimals: int) -> str:
    base = 10**decimals
    whole = value // base
    frac = value % base
    if frac == 0:
        return str(whole)
    frac_str = str(frac).rjust(decimals, "0").rstrip("0")
    return f"{whole}.{frac_str}"


def register_seller(
    conn: sqlite3.Connection,
    *,
    evm_address: str,
    price_wei: int | None = None,
    price_conflux_wei: int | None = None,
    price_tron_sun: int | None = None,
    description: str | None,
    keywords: list[str] | str | None,
    seller_id: str | None = None,
) -> models.Seller:
    checksum_address = to_checksum_address(evm_address)
    resolved_seller_id = seller_id or _normalize_seller_id(checksum_address)
    normalized_keywords = _normalize_keywords(keywords)
    keywords_text = _keywords_to_text(normalized_keywords)
    desc = (description or "").strip()

    resolved_price_conflux = _normalize_price(price_conflux_wei)
    if resolved_price_conflux is None:
        resolved_price_conflux = _normalize_price(price_wei)
    resolved_price_tron = _normalize_price(price_tron_sun)

    if resolved_price_conflux is None and resolved_price_tron is None:
        raise ValueError("price_conflux_wei/price_wei or price_tron_sun is required")

    if price_wei is None and resolved_price_conflux is not None:
        price_wei = resolved_price_conflux
    if price_wei is None:
        price_wei = 0

    existing = models.get_seller_by_id(conn, seller_id=resolved_seller_id)
    if existing is None:
        return models.create_seller(
            conn,
            seller_id=resolved_seller_id,
            evm_address=checksum_address,
            price_wei=int(price_wei),
            price_conflux_wei=resolved_price_conflux,
            price_tron_sun=resolved_price_tron,
            description=desc,
            keywords=keywords_text,
            status="active",
        )

    fields = {
        "evm_address": checksum_address,
        "description": desc,
        "keywords": keywords_text,
        "status": "active",
    }
    if price_wei is not None:
        fields["price_wei"] = int(price_wei)
    if price_wei is not None or price_conflux_wei is not None:
        fields["price_conflux_wei"] = resolved_price_conflux
    if price_tron_sun is not None:
        fields["price_tron_sun"] = resolved_price_tron

    return models.update_seller_fields(
        conn,
        seller_id=resolved_seller_id,
        fields=fields,
    )


def unregister_seller(
    conn: sqlite3.Connection,
    *,
    seller_id: str | None = None,
    evm_address: str | None = None,
) -> models.Seller:
    resolved_id = None
    if seller_id:
        resolved_id = seller_id
    elif evm_address:
        checksum_address = to_checksum_address(evm_address)
        seller = models.get_seller_by_address(conn, evm_address=checksum_address)
        if seller is None:
            raise NotFoundError("seller not found")
        resolved_id = seller.seller_id
    else:
        raise ValueError("seller_id or evm_address is required")

    seller = models.get_seller_by_id(conn, seller_id=resolved_id)
    if seller is None:
        raise NotFoundError("seller not found")
    if seller.status == "inactive":
        return seller

    return models.update_seller_fields(
        conn,
        seller_id=resolved_id,
        fields={"status": "inactive"},
    )


def search_sellers(conn: sqlite3.Connection, *, keyword: str) -> list[models.Seller]:
    return models.search_sellers(conn, keyword=keyword)


def seller_to_dict(seller: models.Seller) -> dict:
    has_conflux = seller.price_conflux_wei is not None and seller.price_conflux_wei > 0
    has_tron = seller.price_tron_sun is not None and seller.price_tron_sun > 0
    payment_modes = []
    if has_conflux:
        payment_modes.append("conflux")
    if has_tron:
        payment_modes.append("tron")

    price_display = {}
    if has_conflux:
        price_display["conflux"] = f"{_format_units(seller.price_conflux_wei, 18)} CFX"
    if has_tron:
        price_display["tron"] = f"{_format_units(seller.price_tron_sun, 6)} TRX"

    return {
        "seller_id": seller.seller_id,
        "evm_address": seller.evm_address,
        "price_wei": seller.price_conflux_wei if has_conflux else None,
        "price_conflux_wei": seller.price_conflux_wei if has_conflux else None,
        "price_tron_sun": seller.price_tron_sun if has_tron else None,
        "payment_modes": payment_modes,
        "price_display": price_display,
        "description": seller.description,
        "keywords": _keywords_from_text(seller.keywords),
        "status": seller.status,
        "created_at": seller.created_at,
        "updated_at": seller.updated_at,
    }
