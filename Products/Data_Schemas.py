from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, UUID4, Field


class ProductStatusEnum(str, Enum):
    in_cart = "inCart"
    in_order = "inanOrder"
    available = "available"


class AddProductSchema(BaseModel):
    name: str
    model: str
    details: dict
    quantity: Optional[int] = None


class ToggleProductListingSchema(BaseModel):
    product_id: UUID4


class GetDelistedProductsSchema(BaseModel):
    limit: str = Field(
        ...,
        pattern=r"^\d+-\d+$",
        description="Range of results in the format 'start-end'",
    )


class SearchProductsSchema(BaseModel):
    query: str
    limit: str
