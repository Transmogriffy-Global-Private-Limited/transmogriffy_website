import uuid
from fastapi import HTTPException, status
from Database_and_ORM.Database_Models import ContactUs
from .Database_Schemas import ContactSchema
from Utility_Methods.libs import email_sender
from datetime import datetime
from zoneinfo import ZoneInfo

async def savecontact(payload:dict,payload_data:ContactSchema):

    ist_now = datetime.now(ZoneInfo("Asia/Kolkata"))

    try:
        new_contact = await ContactUs.create(
            id = uuid.uuid4(),
            firstname = payload_data.firstname,
            lastname = payload_data.lastname,
            telephone = payload_data.telephone,
            email =  payload_data.email,
            message =  payload_data.message,
            contacted_at = ist_now
        )
        recipients = [
            "tgwbin@gmail.com",
            "info@transmogrify.in",
            "chakrapanimondal@tgplin.com",
            "sujatarouth@tgplin.com"
        ]

        subject = 'Reaching out from transev.in'
        # text =  f'My Details: \nName: {new_contact.firstname} {new_contact.lastname} \nE-mail: {new_contact.email} \nPhone no.: {new_contact.telephone} \n\n\nHello,\n{new_contact.message} \n\nSigned\n{new_contact.firstname} {new_contact.lastname} '
        text = f"""You have received a new inquiry through the Transev website.

        Submitted By:

        Name: {new_contact.firstname} {new_contact.lastname}

        Email: {new_contact.email}

        Phone: {new_contact.telephone}

        Message:

        {new_contact.message}

        Submitted From:

        Website: transev.in

        Form: Contact Us

        Received On:

        {ist_now}

        Regards,

        team@transev.in
        """
        for email in recipients:
            email_sender(email, subject, text)
        # email_sender(to,subject,text)
        return new_contact
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save contact data: {str(e)}",
        )
        

async def see_all_contacts():
    try:
        contacts: list[dict] = await ContactUs.all().values(
            "id", "firstname", "lastname", "telephone", "email", "message", "contacted_at"
        )
        return contacts
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve contacts: {e}"
        )