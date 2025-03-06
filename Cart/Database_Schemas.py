from tortoise import fields
from enum import Enum
from pydantic import BaseModel, UUID4, Field
from typing import List, Optional

class CartSchema(BaseModel):
    userid: Optional[str]=None
    productid:Optional[str]=None
    price:Optional[str]=None

class ManagementQuantity(BaseModel):
    quantity:Optional[int]=None
    productid:Optional[str]=None