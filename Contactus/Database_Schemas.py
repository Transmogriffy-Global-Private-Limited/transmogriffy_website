from typing import Optional
from pydantic import BaseModel

class ContactSchema(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    message: Optional[str] = None