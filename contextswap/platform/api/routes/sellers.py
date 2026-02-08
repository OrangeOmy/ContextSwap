from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from contextswap.platform.api.deps import get_db
from contextswap.platform.db import models
from contextswap.platform.services import seller_service
from eth_utils import to_checksum_address

router = APIRouter(prefix="/v1/sellers", tags=["sellers"])


class SellerRegisterRequest(BaseModel):
    evm_address: str
    price_wei: int | None = None
    price_conflux_wei: int | None = None
    price_tron_sun: int | None = None
    description: str | None = None
    keywords: list[str] | str | None = None
    seller_id: str | None = None


class SellerUnregisterRequest(BaseModel):
    seller_id: str | None = None
    evm_address: str | None = None


class SellerUpdateRequest(BaseModel):
    """可更新的 seller 字段（与 db 一致，禁止 id/seller_id/created_at）。"""
    evm_address: str | None = None
    price_wei: int | None = None
    price_conflux_wei: int | None = None
    price_tron_sun: int | None = None
    description: str | None = None
    keywords: str | None = None
    status: str | None = None


def _seller_full(seller: models.Seller) -> dict:
    return seller_service.seller_to_full_dict(seller)


# ---------- List & get（按 db 全字段返回） ----------


@router.get("")
def list_sellers(
    conn=Depends(get_db),
    limit: int = 100,
    offset: int = 0,
    status: str | None = None,
) -> dict:
    """列出卖家，支持分页与按 status 筛选。返回与 db 表一致的全字段。"""
    if limit < 1 or limit > 200:
        limit = 100
    if offset < 0:
        offset = 0
    items = seller_service.list_sellers(conn, limit=limit, offset=offset, status=status)
    return {"items": [_seller_full(s) for s in items]}


@router.get("/by-address/{evm_address}")
def get_seller_by_address(evm_address: str, conn=Depends(get_db)) -> dict:
    """按 evm_address 查询卖家。返回与 db 表一致的全字段。"""
    try:
        addr = to_checksum_address(evm_address)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    seller = models.get_seller_by_address(conn, evm_address=addr)
    if seller is None:
        raise HTTPException(status_code=404, detail="seller not found")
    return _seller_full(seller)


@router.get("/search")
def search_sellers(keyword: str, conn=Depends(get_db)) -> dict:
    """按关键词搜索（仅 active）。返回与 db 表一致的全字段。"""
    try:
        sellers = seller_service.search_sellers(conn, keyword=keyword)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"items": [_seller_full(s) for s in sellers]}


@router.get("/{seller_id}")
def get_seller(seller_id: str, conn=Depends(get_db)) -> dict:
    """按 seller_id 查询卖家。返回与 db 表一致的全字段。"""
    seller = models.get_seller_by_id(conn, seller_id=seller_id)
    if seller is None:
        raise HTTPException(status_code=404, detail="seller not found")
    return _seller_full(seller)


# ---------- Create / update / unregister ----------


@router.post("/register")
def register_seller(payload: SellerRegisterRequest, conn=Depends(get_db)) -> dict:
    try:
        seller = seller_service.register_seller(
            conn,
            evm_address=payload.evm_address,
            price_wei=payload.price_wei,
            price_conflux_wei=payload.price_conflux_wei,
            price_tron_sun=payload.price_tron_sun,
            description=payload.description,
            keywords=payload.keywords,
            seller_id=payload.seller_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _seller_full(seller)


@router.patch("/{seller_id}")
def update_seller(seller_id: str, payload: SellerUpdateRequest, conn=Depends(get_db)) -> dict:
    """部分更新卖家。仅提交需修改的字段。禁止修改 id、seller_id、created_at。"""
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        seller = models.get_seller_by_id(conn, seller_id=seller_id)
        if seller is None:
            raise HTTPException(status_code=404, detail="seller not found")
        return _seller_full(seller)
    try:
        seller = models.update_seller_fields(conn, seller_id=seller_id, fields=fields)
    except models.DbError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _seller_full(seller)


@router.post("/unregister")
def unregister_seller(payload: SellerUnregisterRequest, conn=Depends(get_db)) -> dict:
    try:
        seller = seller_service.unregister_seller(
            conn,
            seller_id=payload.seller_id,
            evm_address=payload.evm_address,
        )
    except seller_service.NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _seller_full(seller)
