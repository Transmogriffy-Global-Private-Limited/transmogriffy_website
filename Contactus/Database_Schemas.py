from typing import Optional
from pydantic import BaseModel

class ContactSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    contactno: Optional[str] = None
    message: Optional[str] = None