from fastapi import APIRouter,status,HTTPException
from .Methods import see_all_contacts, savecontact
from .Database_Schemas import ContactSchema

contact_router  = APIRouter()

@contact_router.post("/contactus",status_code=status.HTTP_200_OK)
async def contact_endpoint(contact_data:ContactSchema):
    try:
        result = await savecontact({},contact_data)
        return {"message":"Contact hasbeen saved successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save contact: {str(e)}",
        )
    
@contact_router.get("/getallcontacts", status_code=status.HTTP_200_OK)
async def getallcontact():
    try:
        # Call the function to retrieve all contacts
        all_contacts = await see_all_contacts()
        
        # Return the list of all contacts
        return {"contacts": all_contacts}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve contacts: {str(e)}",
        )