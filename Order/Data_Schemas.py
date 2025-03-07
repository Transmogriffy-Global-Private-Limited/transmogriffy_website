from enum import Enum
from typing import List,Optional
from pydantic import BaseModel,Field

class OrderSchema(BaseModel):
    productid: Optional[str] =     None
    order_quantity: Optional[str] =      None
    userid: Optional[str] =         None
    totalamount: Optional[str] =    None
    paymentoption: Optional[str] =  None
    orderstatus: Optional[str]  =  None

class StandAloneUserId(BaseModel):
    userid: Optional[str] = None