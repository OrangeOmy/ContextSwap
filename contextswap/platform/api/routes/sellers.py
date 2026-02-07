from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from contextswap.platform.api.deps import get_db
from contextswap.platform.services import seller_service

router = APIRouter(prefix="/v1/sellers", tags=["sellers"])


class SellerRegisterRequest(BaseModel):
    evm_address: str
    price_wei: int
    description: str | None = None
    keywords: list[str] | str | None = None
    seller_id: str | None = None


class SellerUnregisterRequest(BaseModel):
    seller_id: str | None = None
    evm_address: str | None = None


@router.post("/register")
def register_seller(payload: SellerRegisterRequest, conn=Depends(get_db)) -> dict:
    try:
        seller = seller_service.register_seller(
            conn,
            evm_address=payload.evm_address,
            price_wei=payload.price_wei,
            description=payload.description,
            keywords=payload.keywords,
            seller_id=payload.seller_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return seller_service.seller_to_dict(seller)


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

    return seller_service.seller_to_dict(seller)


@router.get("/search")
def search_sellers(keyword: str, conn=Depends(get_db)) -> dict:
    try:
        sellers = seller_service.search_sellers(conn, keyword=keyword)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"items": [seller_service.seller_to_dict(seller) for seller in sellers]}
