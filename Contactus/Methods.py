import uuid
from fastapi import HTTPException, status
from Database_and_ORM.Database_Models import ContactUs
from .Database_Schemas import ContactSchema
from Utility_Methods.libs import email_sender

async def savecontact(payload:dict,payload_data:ContactSchema):
    try:
        new_contact = await ContactUs.create(
            id = uuid.uuid4(),
            firstname = payload_data.firstname,
            lastname = payload_data.lastname,
            company = payload_data.company,
            yoursite = payload_data.yoursite,
            address = payload_data.address,
            city = payload_data.city,
            postcode = payload_data.postcode,
            telephone = payload_data.telephone,
            email =  payload_data.email,
            message =  payload_data.message
        )
        to = 'transmogrify13@outlook.com'
        subject = 'Received successfully'
        text =  f'Contact detail firstname - {new_contact.firstname} lastname -{new_contact.lastname} address - {new_contact.address} city - {new_contact.city} postcode - {new_contact.postcode} user_email={new_contact.email} contact_phoneno - {new_contact.telephone} contact reason - message - {new_contact.message} '
        email_sender(to,subject,text)
        return new_contact
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save contact data: {str(e)}",
        )
        

async def see_all_contacts():
    try:
        contacts: list[dict] = await ContactUs.all().values(
            "id", "firstname", "lastname", "company", "yoursite", "address", "city", "postcode", "telephone", "email", "message"
        )
        return contacts
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve contacts: {e}"
        )