from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, UUID4, Field


class AddProductSchema(BaseModel):
    name: str
    model: str
    details: dict
    quantity: Optional[int] = None
    price: float


class UpdateProductSchema(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    details: Optional[dict] = None
    quantity: Optional[int] = None
    price: Optional[float] = None


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


class ProductResponse(BaseModel):
    id: str
    name: str
    model: str
    details: dict
    is_listed: bool
    image_paths: List[str]
    quantity: int
    price: float
