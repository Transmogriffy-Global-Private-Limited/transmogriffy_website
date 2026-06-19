from fastapi import APIRouter, status, HTTPException, Depends

from Utility_Methods.Utility_Methods import verify_admin_jwt
from .Methods import see_all_contacts, savecontact
from .Database_Schemas import ContactSchema

contact_router = APIRouter()


@contact_router.post("/contactus", status_code=status.HTTP_200_OK)
async def contact_endpoint(contact_data: ContactSchema):
    try:
        result = await savecontact({}, contact_data)
        return {"message": "Contact hasbeen saved successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save contact: {str(e)}",
        )


@contact_router.get("/getallcontacts", status_code=status.HTTP_200_OK)
async def getallcontact(admin_payload: dict = Depends(verify_admin_jwt)):
    try:
        all_contacts = await see_all_contacts()
        return {"contacts": all_contacts}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve contacts: {str(e)}",
        )
