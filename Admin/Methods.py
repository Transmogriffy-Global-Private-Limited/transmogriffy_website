from tortoise.transactions import atomic
import json
from tortoise.exceptions import IntegrityError
from Database_and_ORM.Database_Models import (
    AdminOTP,
    User,
    Admin,
    Blacklisted_Tokens,
)
from fastapi import HTTPException, status, UploadFile
from decouple import config
import os
from typing import Union
from Comms.Methods import get_email_content, send_email
from datetime import datetime, timezone, timedelta
from Utility_Methods.Utility_Methods import (
    create_jwt,
    verify_admin_otp,
    verify_user_password,
    get_hashed_password,
    encode_path_to_base64,
    generate_random_otp,
    get_token_from_authorization_header_value,
)
from Admin.Data_Schemas import OTPTypeEnum, RoleEnum, AdminCreate


async def create_admin(admin_data: AdminCreate) -> Union[Admin, dict]:
    """
    Creates a new admin in the database with hashed password.
    """
    # Hash the password with a salt
    hashed_password = await get_hashed_password(admin_data.password)

    admin = Admin(
        name=admin_data.name,
        email=admin_data.email,  # Defaults to False if not passed
        password=hashed_password,
        role=RoleEnum.admin,  # Defaults to False if not passed
    )

    try:
        await admin.save()
        return {"message": "Account succesfully created!"}
    except IntegrityError:
        return {"error": "An admin with same details already exists."}


# Authenticate Admin
async def authenticate_admin(email: str, password: str, otp_code: str = None):
    """
    Authenticates an admin by email and password.
    """
    admin = await Admin.get_or_none(email=email)

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    verified = await verify_user_password(
        entered_password=password, user_password=admin.password
    )

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # 2FA Check
    if admin.two_fa_status:
        if not otp_code:
            await generate_and_send_otp(
                admin.id, purpose=OTPTypeEnum.TWO_FA
            )
            raise HTTPException(
                status_code=status.HTTP_308_PERMANENT_REDIRECT,
                detail="2FA enabled. Please verify with OTP.",
            )

    # Generate JWT
    token = await create_jwt(
        str(admin.id),
        expiration_duration=int(config("JWT_VALIDITY_FOR_NORMAL_SESSIONS")),
    )
    return admin, token


# Update Admin
async def update_admin(update_data: dict, payload: dict):
    """
    Updates admin details. Sets email_verification to False if the email is changed
    and updates the user count after saving changes.
    """
    admin_id = payload.get("user_id")
    admin = await Admin.get_or_none(id=admin_id)

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found",
        )

    changes = {}

    for field, new_value in update_data.items():
        if field == "password":  # Hash password if updating
            new_value = await get_hashed_password(new_value)
        current_value = getattr(admin, field, None)

        if current_value != new_value:
            setattr(admin, field, new_value)
            changes[field] = (
                f"Updated `{field}` from `{current_value}` to `{new_value}`"
            )

            # If the email is changed, reset email verification status
            if field == "email":
                admin.email_verified = False
                changes["email_verified"] = (
                    "Set to `False` due to email change"
                )

    if changes:
        await admin.save()
        return {"changes": changes}
    else:
        return {"message": "No changes made."}


# Delete Admin
async def delete_admin(payload: dict, authorization: str):
    """
    Deletes an admin based on admin ID.
    """
    admin_id = payload.get("user_id")
    admin = await Admin.get_or_none(id=admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found",
        )

    await admin.delete()
    # Blacklist the token
    token = await get_token_from_authorization_header_value(authorization)
    await Blacklisted_Tokens.create(Blacklisted_Tokens=token)
    return {"message": "Admin deleted successfully and token blacklisted"}


# Upload Profile Picture
async def upload_admin_profile_picture(
    payload: dict, file: UploadFile
) -> dict:
    """
    Uploads a profile picture for the admin.
    """
    admin_id = payload.get("user_id")
    directory = os.path.join(
        config("ADMIN_MEDIA_PATH"),
        config("ADMIN_PROFILE_PICTURES_DIRECTORY"),
    )
    os.makedirs(directory, exist_ok=True)

    if file.content_type not in [
        "image/jpeg",
        "image/png",
        "image/jpg",
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG and PNG images are allowed.",
        )

    # Check file size
    file_size = await file.read()
    if len(file_size) > int(config("MAXIMUM_IMAGE_SIZE")) * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size should not exceed {config('MAXIMUM_IMAGE_SIZE')} MBs.",
        )

    await file.seek(0)

    file_path = os.path.join(
        directory,
        f"{config('ADMIN_PROFILE_PICTURE_PREFIX')}_{admin_id}_{file.filename}",
    )
    with open(file_path, "wb") as buffer:
        buffer.write(file_size)

    admin = await Admin.get(id=admin_id)
    admin.profile_picture_path = file_path
    await admin.save()

    return {"message": "Profile picture uploaded successfully"}


async def request_admin_password_reset(email: str) -> dict:
    """
    Generates a password reset OTP for an admin and sends it via email.

    Args:
        email (str): The admin's registered email address.

    Returns:
        dict: A message indicating that the password reset OTP was sent successfully.

    Raises:
        HTTPException: If the email does not exist or OTP generation fails.
    """

    # Retrieve the admin by email
    admin = await Admin.get_or_none(email=email)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="An admin with this email does not exist.",
        )

    # Check for an existing OTP
    existing_otp = await AdminOTP.filter(
        admin_id=admin.id, purpose=OTPTypeEnum.PASSWORD_RESET
    ).first()

    # Use existing OTP if still valid; otherwise, generate a new one
    if existing_otp and existing_otp.expiration > datetime.now(timezone.utc):
        otp_code = existing_otp.otp_code
    else:
        otp_code = await generate_random_otp()

        # Invalidate any existing OTPs for password reset for this user
        await AdminOTP.filter(
            admin_id=admin.id, purpose=OTPTypeEnum.PASSWORD_RESET
        ).delete()

        # Create a new OTP entry
        try:
            new_otp = AdminOTP(
                otp_code=otp_code,
                admin_id=admin.id,
                purpose=OTPTypeEnum.PASSWORD_RESET,
                expiration=datetime.now(timezone.utc)
                + timedelta(minutes=10),  # OTP valid for 10 minutes
            )
            await new_otp.save()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating OTP: {str(e)}",
            )

    # Prepare the email content
    email_content = await get_email_content(
        "Password_Reset", username=admin.name, otp_code=otp_code
    )

    # Send the OTP via email
    email_sent = await send_email(
        to_email=admin.email,
        subject=email_content["subject"],
        body=email_content["body"],
    )

    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OTP could not be sent.",
        )

    return {"message": "Password reset OTP sent successfully."}


# Get Profile Picture
async def get_admin_profile_picture(payload: dict) -> dict:
    """
    Retrieves the profile picture for an admin, ensuring proper handling of invalid paths.
    """
    admin_id = payload.get("user_id")
    admin = await Admin.get_or_none(id=admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found",
        )

    if not admin.profile_picture_path:
        return {"message": "No profile picture available."}

    # Encode the profile picture path
    profile_picture_base64 = await encode_path_to_base64(
        admin.profile_picture_path
    )
    if (
        profile_picture_base64
        == "Invalid path provided. Path is neither a file nor a directory, or doesn't exist."
    ):
        return {"profile_picture": None}

    return {"profile_picture": profile_picture_base64}


# Get 2FA Status
async def get_admin_2fa_status(payload: dict) -> dict:
    """
    Retrieves the current 2FA status for an admin.
    """
    admin_id = payload.get("user_id")
    admin = await Admin.get_or_none(id=admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found.",
        )

    status_message = "enabled" if admin.two_fa_status else "disabled"
    return {"message": f"2FA is currently {status_message} for this admin."}


# Toggle 2FA Status
async def toggle_2fa_status(payload: dict, entered_password: str) -> str:
    """
    Toggles the 2FA status for a user and returns the new status.
    Ensures the user's email is verified before enabling 2FA.
    """
    admin_id = payload.get("user_id")

    # Fetch the user
    admin = await Admin.get_or_none(id=admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found.",
        )

    # Verify the password
    verified = await verify_user_password(
        entered_password=entered_password, user_password=admin.password
    )
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password. Please try again.",
        )

    # Ensure email is verified before enabling 2FA
    if not admin.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must verify your email before enabling 2FA.",
        )

    # Toggle the 2FA status
    admin.two_fa_status = not admin.two_fa_status
    await admin.save()

    if admin.two_fa_status:
        return {"message": "You have enabled 2FA!"}
    else:
        return {"message": "You have disabled 2FA!"}


async def generate_and_send_otp(admin_id: str, purpose: str) -> dict:
    """
    Generates an OTP for an admin, stores it in the database, and sends it via email.

    Args:
        admin_id (str): The ID of the admin for whom the OTP is generated.
        purpose (str): The purpose of the OTP (e.g., TWO_FA, PASSWORD_RESET).

    Returns:
        dict: A success message if the OTP is generated and sent.

    Raises:
        HTTPException: If the admin is not found or the OTP could not be sent.
    """
    # Retrieve the admin
    admin = await Admin.get_or_none(id=admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found.",
        )

    # Check for existing OTP for this admin and purpose
    existing_otp = await AdminOTP.filter(
        admin_id=admin.id, purpose=purpose
    ).first()

    # Validate existing OTP or generate a new one
    if existing_otp and existing_otp.expiration > datetime.now(timezone.utc):
        otp_code = existing_otp.otp_code
    else:
        otp_code = await generate_random_otp()  # Generate a new random OTP
        await AdminOTP.filter(
            admin_id=admin.id, purpose=purpose
        ).delete()  # Invalidate old OTPs

        # Create and save the new OTP
        try:
            new_otp = AdminOTP(
                admin_id=admin.id,
                purpose=purpose,
                otp_code=otp_code,
                expiration=datetime.now(timezone.utc)
                + timedelta(minutes=10),  # Valid for 10 minutes
            )
            await new_otp.save()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating OTP: {str(e)}",
            )
        
    otp_template=purpose    

    # Prepare and send the OTP via email
    email_content = await get_email_content(
        otp_template, username=admin.name, otp_code=otp_code
    )
    email_sent = await send_email(
        to_email=admin.email,
        subject=email_content["subject"],
        body=email_content["body"],
    )

    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OTP could not be sent.",
        )

    return {"message": "OTP sent successfully."}


async def verify_2fa_and_login(email: str, otp_code: str):
    """
    Verifies the OTP for 2FA and, if valid, generates a JWT token and sets it in the response headers.
    """
    # Retrieve the OTP entry for the user and 2FA purpose
    user = await Admin.get_or_none(email=email)
    user_id = user.id
    verified = await verify_admin_otp(
        user_id, otp_code, purpose=OTPTypeEnum.TWO_FA
    )

    if verified:
        # Generate JWT token
        token = await create_jwt(
            user_id,
            expiration_duration=int(
                config("JWT_VALIDITY_FOR_NORMAL_SESSIONS")
            ),
        )
        response = token, user
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="2FA Verification Failed",
        )

    return response


async def logout_admin(authorization: str) -> dict:
    """
    Logs out the admin by blacklisting the token.
    """
    try:
        token = await get_token_from_authorization_header_value(authorization)
        await Blacklisted_Tokens.create(Blacklisted_Tokens=token)
        return {"message": "Admin successfully logged out"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Either you have already logged out, or there has been an error from our end {e}",
        )


async def reset_admin_password(email: str, otp_code: str, new_password: str):
    """
    Resets the admin's password by verifying the OTP and updating the password.
    """
    admin = await Admin.get_or_none(email=email)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin with this email was not found.",
        )

    # Verify OTP
    verified = await verify_admin_otp(
        otp_code=otp_code,
        admin_id=admin.id,
        purpose=OTPTypeEnum.PASSWORD_RESET,
    )
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP for password reset.",
        )

    # Update password
    try:
        hashed_password = await get_hashed_password(new_password)
        admin.password = hashed_password
        await admin.save()
        return {"message": "Password has been reset successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resetting password.",
        )


async def get_admin_data(payload: dict) -> dict:
    """
    Retrieves admin data by user_id, excluding the password field.
    """
    admin_id = payload.get("user_id")
    admin = await Admin.get_or_none(id=admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found",
        )

    # Convert admin instance to a dictionary excluding private/internal attributes
    admin_data = {
        field: value
        for field, value in admin.__dict__.items()
        if not field.startswith("_")
    }

    # Remove sensitive or unnecessary fields
    admin_data.pop("password", None)
    admin_data.pop("id", None)

    return admin_data


import base64


async def view_user_data(
	payload: dict, user_id: str = None, limit: str = None
) -> list:
	"""
	Retrieves user data by user_id or all users in a paginated format.
	Excludes sensitive fields such as password and profile_picture_path.
	"""

	admin_id = payload.get("user_id")
	admin = await Admin.get_or_none(id=admin_id)
	if not admin:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Only admins are authorized to view user data.",
		)

	async def enrich_user_data(user: dict) -> dict:
		user.pop("password", None)
		user.pop("profile_picture_path", None)

		user_obj = await User.get_or_none(id=user.get("id"))
		if not user_obj:
			user["profile_picture"] = None
			return user

		raw_pic = user_obj.profile_picture
		if not raw_pic or not isinstance(raw_pic, bytes):
			user["profile_picture"] = None
			return user

		try:
			mime_type = "image/png"
			if raw_pic.startswith(b"\xff\xd8"):
				mime_type = "image/jpeg"
			elif raw_pic.startswith(b"\x89PNG"):
				mime_type = "image/png"

			encoded_picture = base64.b64encode(raw_pic).decode("utf-8")
			user["profile_picture"] = f"data:{mime_type};base64,{encoded_picture}"
		except Exception:
			user["profile_picture"] = None

		return user

	if user_id:
		user_list = await User.filter(id=user_id).values()
		if not user_list:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="User not found",
			)
		enriched_user = await enrich_user_data(user_list[0])
		return [enriched_user]

	if not limit:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Limit parameter is required if user_id is not provided.",
		)

	try:
		start, end = map(int, limit.split("-"))
		if start < 1 or end < start:
			raise ValueError
	except ValueError:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Limit parameter format is incorrect. Use 'start-end' with start â‰¥ 1 and end â‰¥ start.",
		)

	users = (
		await User.all()
		.order_by("-updated_at")
		.offset(start - 1)
		.limit(end - start + 1)
		.values()
	)

	enriched_users = []
	for user in users:
		enriched_user = await enrich_user_data(user)
		enriched_users.append(enriched_user)

	return enriched_users


async def verify_email_otp(payload: dict, otp_code: str) -> bool:
    """
    Verifies the OTP for email verification. If valid, marks the admin's email as verified.
    """
    admin_id = payload.get("user_id")
    admin = await Admin.get(id=admin_id)

    if await verify_admin_otp(
        admin_id, otp_code=otp_code, purpose=OTPTypeEnum.MAIL_VERIFICATION
    ):
        # Update the user's email_verified status
        admin.email_verified = True
        await admin.save()
        return True
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired OTP for email verification",
    )
