import uuid
from fastapi import HTTPException, status
from Database_and_ORM.Database_Models import ContactUs
from .Database_Schemas import ContactSchema
from Utility_Methods.libs import email_sender

async def savecontact(payload:dict,payload_data:ContactSchema):
    name = payload_data.name
    email= payload_data.email
    contactno = payload_data.contactno
    message = payload_data.message
    try:
        new_contact = await ContactUs.create(
            id = uuid.uuid4(),
            name = name,
            email =  email,
            contactno = contactno,
            message =  message
        )
        to = email
        subject = 'Received successfully'
        message =  f'Hi {name} We have received your message we will be in touch with you shortly'
        email_sender(to,subject,message)
        return new_contact
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save contact data: {str(e)}",
        )

async def see_all_contacts():
    try:
        # Fetch all contacts from the database
        all_contacts = await ContactUs.all()
        serialized_contacts = [contact.to_dict() for contact in all_contacts]
        return serialized_contacts
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )
