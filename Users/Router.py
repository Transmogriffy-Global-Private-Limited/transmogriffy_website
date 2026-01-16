from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Response,
    Header,
	Body,
    Depends,
    File,
    UploadFile,
)
from Utility_Methods.Utility_Methods import verify_jwt
from Users.Data_Schemas import (
    UserCreate,
    LoginData,
    UserUpdate,
    Toggle2FARequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    TwoFARequest,
    OTPRequest,
    AddressCreate,
    AddressUpdate,
    AddressTypeEnum,
)
from Users.Methods import (
    create_user,
    authenticate_user,
    logout_user,
    update_user,
    delete_user,
    verify_2fa_and_login,
    generate_and_send_otp,
    verify_email_otp,
    request_password_reset_by_email,
    reset_password,
    toggle_2fa_status,
    get_2fa_status,
    get_user_data,
    upload_profile_picture,
    get_profile_picture,
    create_address,
    update_address,
    update_address_type,
    get_all_addresses,
    delete_address,
    get_address_by_type,
    set_default_address,
    get_default_address,
    get_other_address_by_name,
)
from typing import Optional

User_Router = APIRouter()


@User_Router.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(user: UserCreate):
    """
    Endpoint to create a new user. Expects JSON body with name, email, password, and other details.
    """
    new_user = await create_user(user)
    if "error" in new_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=new_user["error"],
        )
    return new_user


@User_Router.post("/login", status_code=status.HTTP_200_OK)
async def login_user(response: Response, login_data: LoginData):
    """
    Login endpoint that validates user credentials. If 2FA is enabled, requires OTP.
    """
    try:
        user, token_or_message = await authenticate_user(
            email=login_data.email, password=login_data.password
        )
        response.headers["Authorization"] = f"Bearer {token_or_message}"
        return {
            "message": f"User {user.name} has successfully logged in",
            "User_Type": "User",
        }
    except HTTPException as e:
        raise e


@User_Router.post("/logout")
async def logout_user_endpoint(
    authorization: str = Header(None),
    payload: dict = Depends(verify_jwt),
):
    """
    Logs out the user by blacklisting the JWT token.
    """
    if not authorization:
        raise HTTPException(status_code=400, detail="Cannot verify user")
    return await logout_user(authorization, payload)


@User_Router.patch("/update")
async def update_user_endpoint(
    update_data: UserUpdate, payload=Depends(verify_jwt)
):
    """
    Updates user details based on the user ID extracted from JWT.
    """
    return await update_user(
        update_data.model_dump(exclude_unset=True), payload
    )


@User_Router.delete("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    authorization: str = Header(None),
    payload: dict = Depends(verify_jwt),
):
    """
    Endpoint to delete a user and blacklist the token.
    """
    return await delete_user(payload, authorization)


@User_Router.get("/2fa/status", status_code=status.HTTP_200_OK)
async def get_2fa_status_endpoint(payload=Depends(verify_jwt)):
    """
    Retrieves the current 2FA status for the authenticated user.
    """
    if payload:
        status = await get_2fa_status(payload)
        return {"status": status}
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Please login to view your 2FA status.",
    )


@User_Router.patch("/2fa/toggle", status_code=status.HTTP_200_OK)
async def toggle_2fa_status_endpoint(
    request: Toggle2FARequest, payload=Depends(verify_jwt)
):
    """
    Toggles the 2FA status for the authenticated user.
    """
    if payload:
        new_status = await toggle_2fa_status(
            payload, entered_password=request.entered_password
        )
        return {"message": f"2FA status updated: {new_status}"}
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Please login to change 2FA Status",
    )


@User_Router.post("/2fa/verify", status_code=status.HTTP_200_OK)
async def verify_2fa_login_endpoint(
    response: Response, two_fa_data: TwoFARequest
):
    """
    Verifies the OTP for 2FA and, if valid, logs the user in by returning a JWT token.
    """
    token, user = await verify_2fa_and_login(
        two_fa_data.email, two_fa_data.otp_code
    )
    response.headers["Authorization"] = f"Bearer {token}"
    return {
        "message": f"2FA verification successful. User {user.name} is now logged in.",
        "User_Type": "User"
    }


@User_Router.post("/otp/generate", status_code=status.HTTP_200_OK)
async def generate_otp_endpoint(otp_request: OTPRequest):
    """
    Generates an OTP for a specified purpose (2FA, email verification, password reset).
    """
    otp = await generate_and_send_otp(otp_request.email, otp_request.purpose)
    return {
        "message": f"OTP for {otp_request.purpose.value} generated successfully.",
        "otp_code": otp,
    }


@User_Router.post("/otp/verify/email", status_code=status.HTTP_200_OK)
async def verify_email_otp_endpoint(
    otp_request: OTPRequest, payload=Depends(verify_jwt)
):
    """
    Verifies the OTP for email verification and updates the user's email_verified status.
    """
    verified = await verify_email_otp(payload, otp_request.otp_code)
    if verified:
        return {"message": "Email verification successful"}
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired OTP for email verification",
    )


@User_Router.post("/password-reset/request", status_code=status.HTTP_200_OK)
async def request_password_reset(request_data: PasswordResetRequest):
    """
    Requests a password reset. Sends a reset token to the user's email.
    """
    response = await request_password_reset_by_email(request_data.email)
    return response


@User_Router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
async def reset_password_endpoint(request_data: PasswordResetConfirm):
    """
    Confirms the password reset by validating the reset token and updating the user's password.
    """
    return await reset_password(
        email=request_data.email,
        new_password=request_data.new_password,
        otp_code=request_data.otp_code,
    )


@User_Router.get("/profile", status_code=status.HTTP_200_OK)
async def get_user_profile(payload=Depends(verify_jwt)):
    """
    Endpoint to retrieve user profile data, excluding the password field.
    """
    user_data = await get_user_data(payload)
    return {"user_data": user_data}


@User_Router.post(
    "/profile-picture/upload", status_code=status.HTTP_201_CREATED
)
async def create_profile_picture(
    payload: dict = Depends(verify_jwt), file: UploadFile = File(...)
):
    """
    Endpoint to upload a profile picture for a user.
    """
    file_path = await upload_profile_picture(file=file, payload=payload)
    if file_path:
        return {"message": "Profile picture uploaded successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload profile picture. Something went wrong on our end.",
        )


@User_Router.get("/profile-picture", status_code=status.HTTP_200_OK)
async def get_profile_picture_endpoint(payload=Depends(verify_jwt)):
    """
    Endpoint to fetch the Base64 encoded profile picture of a user.
    """
    profile_picture_response = await get_profile_picture(payload)

    if "error" in profile_picture_response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=profile_picture_response["error"],
        )

    return {"profile_picture": profile_picture_response["profile_picture"]}


@User_Router.post("/address", status_code=status.HTTP_201_CREATED)
async def create_address_endpoint(
    payload=Depends(verify_jwt),
    address_data: AddressCreate = Body(...),
):
    """
    Creates a new address for the user.
    """
    return await create_address(payload, address_data.model_dump())


@User_Router.patch("/address/{address_type}", status_code=status.HTTP_200_OK)
async def update_address_endpoint(
    address_type: AddressTypeEnum,
    custom_name: Optional[str] = None,
    payload=Depends(verify_jwt),
    update_data: AddressUpdate = Body(...)
):
    """
    Updates an address based on type (Home, Work, Other). If 'Other', a custom name is required.
    """
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Update data is required.",
        )
    return await update_address(
        payload,
        address_type,
        custom_name,
        update_data.model_dump(exclude_unset=True),
    )


@User_Router.patch(
    "/address/{address_type}/update-type", status_code=status.HTTP_200_OK
)
async def update_address_type_endpoint(
    address_type: AddressTypeEnum,
    new_type: AddressTypeEnum,
    custom_name: Optional[str] = None,
    payload=Depends(verify_jwt),
):
    """
    Updates the type of an address.
    """
    return await update_address_type(
        payload, address_type, custom_name, new_type
    )


@User_Router.get("/address", status_code=status.HTTP_200_OK)
async def get_all_addresses_endpoint(payload=Depends(verify_jwt)):
    """
    Retrieves all addresses of the user.
    """
    return await get_all_addresses(payload)


@User_Router.delete(
    "/address/{address_type}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_address_endpoint(
    address_type: AddressTypeEnum,
    custom_name: Optional[str] = None,
    payload=Depends(verify_jwt),
):
    """
    Deletes an address based on type.
    """
    return await delete_address(payload, address_type, custom_name)


@User_Router.get("/address/{address_type}", status_code=status.HTTP_200_OK)
async def get_address_by_type_endpoint(
    address_type: AddressTypeEnum, payload=Depends(verify_jwt)
):
    """
    Retrieves all addresses of a given type.
    """
    return await get_address_by_type(payload, address_type)


@User_Router.patch(
    "/address/{address_type}/set-default", status_code=status.HTTP_200_OK
)
async def set_default_address_endpoint(
    address_type: AddressTypeEnum,
    custom_name: Optional[str] = None,
    payload=Depends(verify_jwt),
):
    """
    Sets an address as the default.
    """
    return await set_default_address(payload, address_type, custom_name)


@User_Router.get("/address/default", status_code=status.HTTP_200_OK)
async def get_default_address_endpoint(payload=Depends(verify_jwt)):
    """
    Retrieves the default address for the user.
    """
    return await get_default_address(payload)


@User_Router.get(
    "/address/other/{custom_name}", status_code=status.HTTP_200_OK
)
async def get_other_address_by_name_endpoint(
    custom_name: str, payload=Depends(verify_jwt)
):
    """
    Retrieves 'Other' type addresses by their custom name.
    """
    return await get_other_address_by_name(payload, custom_name)
