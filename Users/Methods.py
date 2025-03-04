from Database_and_ORM.Database_Models import (
    User,
    Blacklisted_Tokens,
    OTP,
    Address,
)
from Users.Data_Schemas import UserCreate, OTPTypeEnum, AddressTypeEnum
from Comms.Methods import send_email, get_email_content
from tortoise.exceptions import IntegrityError, DoesNotExist
from typing import Union, Optional
from datetime import datetime, timedelta, timezone
from decouple import config
from fastapi import HTTPException, status, UploadFile
from typing import Dict
from Utility_Methods.Utility_Methods import (
    create_jwt,
    verify_otp,
    verify_user_password,
    get_hashed_password,
    encode_path_to_base64,
    generate_random_otp,
    get_token_from_authorization_header_value,
)
import os


async def create_user(user_data: UserCreate) -> Union[User, dict]:
    """
    Creates a new user in the database with hashed password.
    """
    # Hash the password with a salt
    hashed_password = await get_hashed_password(user_data.password)

    user = User(
        name=user_data.name,
        email=user_data.email,  # Defaults to False if not passed
        password=hashed_password,
        phone_number=user_data.phone_number,  # Defaults to False if not passed
    )

    try:
        await user.save()
        return {"message": "Account succesfully created!"}
    except IntegrityError:
        return {"error": "A user with same details already exists."}


async def authenticate_user(email: str, password: str):
    """
    Authenticates a user by email and password.
    If 2FA is enabled, requires OTP verification before generating JWT.
    """
    user = await User.get_or_none(email=email)
    verified = await verify_user_password(
        entered_password=password, user_password=user.password
    )
    if user is None or not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Check if 2FA is enabled for the user
    if user and verified and user.two_fa_status:
        await generate_and_send_otp(email, purpose=OTPTypeEnum.TWO_FA)
        raise HTTPException(
            status_code=status.HTTP_308_PERMANENT_REDIRECT,
            detail="2FA is enabled. Please verify with OTP.",
        )

    # Generate JWT token if 2FA is not enabled or OTP verification is successful
    token = await create_jwt(
        str(user.id),
        expiration_duration=int(config("JWT_VALIDITY_FOR_NORMAL_SESSIONS")),
    )
    return user, token


async def logout_user(authorization: str, payload: dict):
    """
    Logs out the user by adding the token to the blacklist.
    """
    if payload:
        try:
            token = await get_token_from_authorization_header_value(
                authorization
            )
            await Blacklisted_Tokens.create(Blacklisted_Tokens=token)
            return {"message": "Successfully logged out"}
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Either you have already logged out, or there's something wrong on our end",
            )
    else:
        return "You have already logged out!"


async def update_user(update_data: Dict, payload: dict):
    """
    Updates user details based on user_id extracted from JWT token in authorization header.
    """
    # Manually call verify_jwt with the authorization header

    if payload:
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please log in",
            )

        # Retrieve the user from the database
        user = await User.get_or_none(id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        changes = {}

        # Iterate through the update data and apply changes
        for field, new_value in update_data.items():
            if field == "role":  # Exclude updating the role field
                continue
            current_value = getattr(user, field)
            if current_value != new_value:
                setattr(user, field, new_value)
                changes[field] = (
                    f"`{field}` updated from `{current_value}` to `{new_value}`"
                )

            if field == "email":
                user.email_verified = False
                changes["email_verified"] = (
                    "Set to `False` due to email change"
                )

        if changes:
            await user.save()
            return changes
        else:
            return {"message": "Nothing was changed!"}

    else:
        return "Please login to update your data!"


async def delete_user(payload: dict, authorization: str):
    """
    Deletes a user based on user ID extracted from JWT token and blacklists the token.
    """
    # Extract user_id from payload
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please log in first to delete your account",
        )

    # Find the user and delete
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await user.delete()

    # Blacklist the token
    token = await get_token_from_authorization_header_value(authorization)
    blacklisted = await Blacklisted_Tokens.create(Blacklisted_Tokens=token)
    if blacklisted:
        return {"message": "User deleted successfully and token blacklisted"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong on our end",
        )


async def verify_2fa_and_login(email: str, otp_code: str):
    """
    Verifies the OTP for 2FA and, if valid, generates a JWT token and sets it in the response headers.
    """
    # Retrieve the OTP entry for the user and 2FA purpose
    user = await User.get_or_none(email=email)
    user_id = user.id
    verified = await verify_otp(user_id, otp_code, purpose=OTPTypeEnum.TWO_FA)

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


async def generate_and_send_otp(email: str, purpose: OTPTypeEnum) -> dict:
    """
    Checks for an existing OTP for the user and purpose. If none exists or it's expired,
    generates a new OTP, stores it, and sends it via email.
    """
    # Look up the user_id based on the email
    try:
        user = await User.get(email=email)
        user_id = user.id
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email does not exist.",
        )

    # Look for an existing OTP entry
    existing_otp = await OTP.filter(user_id=user_id, purpose=purpose).first()

    # Check if OTP exists and is still valid
    if existing_otp and existing_otp.expiration > datetime.now(timezone.utc):
        otp_code = existing_otp.otp_code  # Use the existing OTP if valid
    else:
        # Generate a new random 6-digit OTP
        otp_code = (
            await generate_random_otp()
        )  # Example of a 6-digit random OTP using UUID

        # Invalidate any existing OTPs for this user and purpose
        await OTP.filter(user_id=user_id, purpose=purpose).delete()

        # Attempt to create a new OTP entry
        try:
            otp_entry = OTP(
                otp_code=otp_code,
                user_id=user_id,
                purpose=purpose,
                expiration=datetime.now(timezone.utc)
                + timedelta(minutes=10),  # OTP valid for 10 minutes
            )
            await otp_entry.save()
        except IntegrityError as e:
            # Log detailed error and raise a user-friendly exception
            print(f"Integrity error while saving OTP: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while generating the OTP. Please try again.",
            )
        except Exception as e:
            # General error handling for any unexpected issue
            print(f"Unexpected error while saving OTP: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred.",
            )

    # Prepare the email content
    values = {"username": user.name, "otp_code": otp_code}
    if purpose == OTPTypeEnum.TWO_FA:
        content = await get_email_content("2fa_verification", **values)
    elif purpose == OTPTypeEnum.MAIL_VERIFICATION:
        content = await get_email_content("email_verification", **values)
    elif purpose == OTPTypeEnum.PASSWORD_RESET:
        content = await get_email_content("password_reset", **values)

    # Send the email
    email_sent = await send_email(
        to_email=email, subject=content["subject"], body=content["body"]
    )

    if email_sent:
        return {"message": "OTP sent successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OTP could not be sent.",
        )


async def get_user_data(payload: dict) -> dict:
    """
    Retrieves user data by user_id, excluding the password field.
    """
    user_id = payload.get("user_id")
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Convert user instance to a dictionary excluding private/internal attributes
    user_data = {
        field: value
        for field, value in user.__dict__.items()
        if not field.startswith("_")
    }

    # Remove sensitive fields
    user_data.pop("password", None)
    user_data.pop("id", None)

    # Handle profile picture
    if user_data.get("profile_picture_path"):
        encoded_picture = await encode_path_to_base64(
            user_data["profile_picture_path"]
        )
        if (
            encoded_picture
            == "Invalid path provided. Path is neither a file nor a directory, or doesn't exist."
        ):
            # If the path is invalid, remove the field
            user_data.pop("profile_picture_path", None)
        else:
            # Otherwise, set the Base64-encoded string
            user_data["profile_picture"] = encoded_picture
    else:
        user_data["profile_picture"] = None

    # Remove the path field to keep the response clean
    user_data.pop("profile_picture_path", None)

    return user_data


async def verify_email_otp(payload: Dict, otp_code: str) -> bool:
    """
    Verifies the OTP for email verification. If valid, marks the user's email as verified.
    """
    user_id = payload.get("user_id")
    user = await User.get(id=user_id)

    if await verify_otp(
        otp_code, user_id, purpose=OTPTypeEnum.MAIL_VERIFICATION
    ):
        # Update the user's email_verified status
        user.email_verified = True
        await user.save()
        return True
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired OTP for email verification",
    )


async def request_password_reset_by_email(email: str) -> str:
    """
    Checks if a user exists with the provided email and generates a password reset JWT token.
    """
    # Find user by email
    user = await User.get_or_none(email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with the provided email.",
        )

    # Generate and send OTP using the existing method
    try:
        result = await generate_and_send_otp(
            email, purpose=OTPTypeEnum.PASSWORD_RESET
        )
        return result  # Result from `generate_and_send_otp`
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating or sending the OTP",
        )


async def reset_password(email: str, otp_code: str, new_password: str):
    user = await User.get_or_none(email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email was not found.",
        )

    # Verify OTP using the existing verify_otp method
    verified = await verify_otp(
        otp_code=otp_code,
        user_id=user.id,
        purpose=OTPTypeEnum.PASSWORD_RESET,
    )
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP for password reset.",
        )

    # Update password if OTP is verified
    try:
        hashed_password = await get_hashed_password(new_password)
        user.password = hashed_password
        await user.save()
        return {"message": "Password has been reset successfully."}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong on our end",
        )


async def get_2fa_status(payload: dict) -> str:
    """
    Retrieves the current 2FA status for a user.
    """
    user_id = payload.get("user_id")
    user = await User.get_or_none(id=user_id)
    if user.two_fa_status:
        return {"message": "You have 2FA enabled!"}
    elif not user.two_fa_status:
        return {"message": "You have 2FA disabled!"}
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Something wrong happened on our end!",
    )


async def toggle_2fa_status(payload: dict, entered_password: str) -> str:
    """
    Toggles the 2FA status for a user and returns the new status.
    Ensures the user's email is verified before enabling 2FA.
    """
    user_id = payload.get("user_id")

    # Fetch the user
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # Verify the password
    verified = await verify_user_password(
        entered_password=entered_password, user_password=user.password
    )
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password. Please try again.",
        )

    # Ensure email is verified before enabling 2FA
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must verify your email before enabling 2FA.",
        )

    # Toggle the 2FA status
    user.two_fa_status = not user.two_fa_status
    await user.save()

    if user.two_fa_status:
        return {"message": "You have enabled 2FA!"}
    else:
        return {"message": "You have disabled 2FA!"}


async def upload_profile_picture(payload: dict, file: UploadFile) -> dict:
    user_id = payload.get("user_id")
    directory = os.path.join(
        f"{config('USER_MEDIA_PATH')}",
        f"{config('USER_PROFILE_PICTURES_DIRECTORY')}",
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

    # Check file size (limit 500kB)
    file_size = await file.read()  # read content to check size
    if len(file_size) > int(config("MAXIMUM_IMAGE_SIZE")) * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size should not exceed {config('MAXIMUM_IMAGE_SIZE')} mBs.",
        )

    await file.seek(0)

    # Create the file path
    file_path = os.path.join(
        directory,
        f"{config('USER_PROFILE_PICTURE_PREFIX')}_{user_id}_{file.filename}",
    )

    # Save the file to the directory
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Update the user profile picture path in the database
    user = await User.get(id=user_id)
    user.profile_picture_path = file_path
    await user.save()

    return {"message": "Profile picture uploaded successfully"}


async def get_profile_picture(payload: dict) -> dict:
    """
    Retrieves the profile picture for a user in Base64 format with MIME encoding.
    """
    # Fetch the user from the database
    user_id = payload.get("user_id")
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check if user has a profile picture path
    if not user.profile_picture_path:
        return {"message": "No profile picture available."}

    # Convert profile picture to Base64 using the utility method
    try:
        profile_picture_base64 = await encode_path_to_base64(
            user.profile_picture_path
        )
        if (
            profile_picture_base64
            == "Invalid path provided. Path is neither a file nor a directory, or doesn't exist."
        ):
            return {"profile_picture": None}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error encoding profile picture: {str(e)}",
        )

    return {"profile_picture": profile_picture_base64}


async def create_address(payload: dict, address_data: Dict) -> Dict:
    """
    Creates a new address for the logged-in user.
    """
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated.",
        )

    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # Ensure only one default address exists
    if address_data.get("is_default"):
        await Address.filter(user=user).update(is_default=False)

    # Create new address
    try:
        new_address = await Address.create(user=user, **address_data)
        return {
            "message": "Address successfully added",
            "address_id": str(new_address.id),
        }
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error adding address. Please try again.",
        )


async def update_address(
    payload: dict,
    address_type: AddressTypeEnum,
    custom_name: Optional[str],
    update_data: Dict,
) -> Dict:
    """
    Updates an existing address of the logged-in user based on type.
    """
    user_id = payload.get("user_id")

    # Fetch address based on type and (if applicable) custom name
    filters = {"user_id": user_id, "type": address_type}
    if address_type == AddressTypeEnum.OTHER:
        if not custom_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom name is required for 'Other' address type.",
            )
        filters["custom_type_name"] = (
            custom_name  # Match the exact 'Other' name
        )

    address = await Address.get_or_none(**filters)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found.",
        )

    # Ensure only one default address exists
    if update_data.get("is_default"):
        await Address.filter(user_id=user_id).update(is_default=False)

    for field, value in update_data.items():
        setattr(address, field, value)

    await address.save()
    return {"message": "Address updated successfully"}


async def update_address_type(
    payload: dict,
    address_type: AddressTypeEnum,
    custom_name: Optional[str],
    new_type: AddressTypeEnum,
) -> Dict:
    """
    Updates the type of an address based on type and (if needed) custom name.
    """
    user_id = payload.get("user_id")

    # Fetch address based on type and (if applicable) custom name
    filters = {"user_id": user_id, "type": address_type}
    if address_type == AddressTypeEnum.OTHER:
        if not custom_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom name is required for 'Other' address type.",
            )
        filters["custom_type_name"] = custom_name

    address = await Address.get_or_none(**filters)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found.",
        )

    address.type = new_type

    if new_type == AddressTypeEnum.OTHER:
        if not custom_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom name required for 'Other' type address.",
            )
        address.custom_type_name = custom_name  # Preserve the custom name
    else:
        address.custom_type_name = None  # Reset custom name if type changes

    await address.save()
    return {"message": "Address type updated successfully"}


async def get_all_addresses(payload: dict) -> list[Dict]:
    """
    Retrieves all addresses associated with the logged-in user.
    """
    user_id = payload.get("user_id")

    addresses = await Address.filter(user_id=user_id).all()
    if not addresses:
        return {"message": "No addresses found."}

    return [address.__dict__ for address in addresses]


async def delete_address(
    payload: dict, address_type: AddressTypeEnum, custom_name: Optional[str]
) -> Dict:
    """
    Deletes an address based on type and (if needed) custom name.
    """
    user_id = payload.get("user_id")

    # Fetch address based on type and (if applicable) custom name
    filters = {"user_id": user_id, "type": address_type}
    if address_type == AddressTypeEnum.OTHER:
        if not custom_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom name is required for 'Other' address type.",
            )
        filters["custom_type_name"] = (
            custom_name  # Ensure correct 'Other' address
        )

    address = await Address.get_or_none(**filters)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found.",
        )

    await address.delete()
    return {"message": "Address deleted successfully"}


async def get_address_by_type(
    payload: dict, address_type: AddressTypeEnum
) -> list[Dict]:
    """
    Retrieves all addresses of a particular type.
    """
    user_id = payload.get("user_id")

    addresses = await Address.filter(user_id=user_id, type=address_type).all()
    if not addresses:
        return {"message": f"No {address_type.value} addresses found."}

    return [address.__dict__ for address in addresses]


async def set_default_address(
    payload: dict, address_type: AddressTypeEnum, custom_name: Optional[str]
) -> Dict:
    """
    Sets an address as the default for the user based on type and (if needed) custom name.
    """
    user_id = payload.get("user_id")

    # Fetch address based on type and (if applicable) custom name
    filters = {"user_id": user_id, "type": address_type}
    if address_type == AddressTypeEnum.OTHER:
        if not custom_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom name is required for 'Other' address type.",
            )
        filters["custom_type_name"] = (
            custom_name  # Ensure correct 'Other' address
        )

    address = await Address.get_or_none(**filters)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found.",
        )

    # Reset all default addresses for this user
    await Address.filter(user_id=user_id).update(is_default=False)

    # Set the new default address
    address.is_default = True
    await address.save()

    return {"message": "Default address set successfully"}


async def get_default_address(payload: dict) -> Dict:
    """
    Retrieves the default address for the user.
    """
    user_id = payload.get("user_id")

    default_address = await Address.get_or_none(
        user_id=user_id, is_default=True
    )
    if not default_address:
        return {"message": "No default address set."}

    return default_address.__dict__


async def get_other_address_by_name(payload: dict, custom_name: str):
    """
    Retrieves 'Other' type addresses for the logged-in user by their custom name.
    """
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated.",
        )

    addresses = await Address.filter(
        user_id=user_id,
        type=AddressTypeEnum.OTHER,
        custom_type_name=custom_name,
    ).all()

    if not addresses:
        return {
            "message": f"No addresses found with the name '{custom_name}'."
        }

    return [address.__dict__ for address in addresses]
