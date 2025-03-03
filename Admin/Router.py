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
from Admin.Data_Schemas import (
    AdminCreate,
    AdminUpdate,
    Toggle2FARequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    TwoFARequest,
    OTPRequest,
    ViewUsersRequest,
)
from Utility_Methods.Utility_Methods import verify_jwt
from Admin.Methods import (
    create_admin,
    authenticate_admin,
    logout_admin,
    update_admin,
    delete_admin,
    verify_2fa_and_login,
    generate_and_send_otp,
    request_admin_password_reset,
    reset_admin_password,
    toggle_2fa_status,
    get_admin_2fa_status,
    get_admin_data,
    upload_admin_profile_picture,
    get_admin_profile_picture,
    verify_email_otp,
    view_user_data,
    get_training_status_from_file,
)
from Machine_Learning.Methods import retrain_model
from Database_and_ORM.Database_Models import Admin

Admin_Router = APIRouter()


@Admin_Router.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_admin_endpoint(admin: AdminCreate):
    """
    Creates a new admin account.
    """
    response = await create_admin(admin)
    if "error" in response:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response["error"],
        )
    return response


@Admin_Router.post("/login", status_code=status.HTTP_200_OK)
async def login_admin_endpoint(response: Response, admin_data: AdminUpdate):
    """
    Authenticates an admin and issues a JWT. Handles 2FA if enabled.
    """
    try:
        admin, token = await authenticate_admin(
            email=admin_data.email, password=admin_data.password
        )
        response.headers["Authorization"] = f"Bearer {token}"
        return {"message": f"Admin {admin.name} successfully logged in"}
    except HTTPException as e:
        raise e


@Admin_Router.post("/logout", status_code=status.HTTP_200_OK)
async def logout_admin_endpoint(
    authorization: str = Header(None),
    payload: dict = Depends(verify_jwt),
):
    """
    Logs out the admin by blacklisting the JWT token.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot verify admin",
        )
    return await logout_admin(authorization)


@Admin_Router.patch("/update", status_code=status.HTTP_200_OK)
async def update_admin_endpoint(
    update_data: AdminUpdate, payload=Depends(verify_jwt)
):
    """
    Updates admin details.
    """
    return await update_admin(
        update_data.model_dump(exclude_unset=True), payload
    )


@Admin_Router.delete("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_endpoint(
    authorization: str = Header(None),
    payload: dict = Depends(verify_jwt),
):
    """
    Deletes the admin account and blacklists the JWT token.
    """
    return await delete_admin(payload, authorization)


@Admin_Router.get("/2fa/status", status_code=status.HTTP_200_OK)
async def get_2fa_status_endpoint(payload=Depends(verify_jwt)):
    """
    Retrieves the current 2FA status for the authenticated admin.
    """
    return await get_admin_2fa_status(payload)


@Admin_Router.patch("/2fa/toggle", status_code=status.HTTP_200_OK)
async def toggle_2fa_status_endpoint(
    request: Toggle2FARequest, payload=Depends(verify_jwt)
):
    """
    Toggles the 2FA status for the authenticated admin.
    """
    return await toggle_2fa_status(
        payload, entered_password=request.entered_password
    )


@Admin_Router.post("/2fa/verify", status_code=status.HTTP_200_OK)
async def verify_2fa_login_endpoint(
    response: Response, two_fa_data: TwoFARequest
):
    """
    Verifies the OTP for 2FA and logs in the admin.
    """
    token, admin = await verify_2fa_and_login(
        email=two_fa_data.email, otp_code=two_fa_data.otp_code
    )
    response.headers["Authorization"] = f"Bearer {token}"
    return {
        "message": f"2FA verification successful. Admin {admin.name} is now logged in."
    }


@Admin_Router.post("/password-reset/request", status_code=status.HTTP_200_OK)
async def request_password_reset_endpoint(
    request_data: PasswordResetRequest,
):
    """
    Sends a password reset OTP to the admin's email.
    """
    return await request_admin_password_reset(request_data.email)


@Admin_Router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
async def confirm_password_reset_endpoint(
    request_data: PasswordResetConfirm,
):
    """
    Resets the admin's password after verifying the OTP.
    """
    return await reset_admin_password(
        email=request_data.email,
        otp_code=request_data.otp_code,
        new_password=request_data.new_password,
    )


@Admin_Router.get("/profile", status_code=status.HTTP_200_OK)
async def get_admin_profile(payload=Depends(verify_jwt)):
    """
    Retrieves the profile data for the authenticated admin.
    """
    return await get_admin_data(payload)


@Admin_Router.post(
    "/profile-picture/upload", status_code=status.HTTP_201_CREATED
)
async def upload_profile_picture_endpoint(
    payload: dict = Depends(verify_jwt), file: UploadFile = File(...)
):
    """
    Uploads a profile picture for the admin.
    """
    return await upload_admin_profile_picture(payload, file)


@Admin_Router.get("/profile-picture", status_code=status.HTTP_200_OK)
async def get_profile_picture_endpoint(payload=Depends(verify_jwt)):
    """
    Retrieves the Base64 encoded profile picture for the admin.
    """
    return await get_admin_profile_picture(payload)


@Admin_Router.get("/view-users", status_code=status.HTTP_200_OK)
async def view_users_endpoint(
    payload: dict = Depends(verify_jwt),
    view_users_request: ViewUsersRequest = Body(...),
):
    """
    Allows the admin to view user data. Supports pagination.
    """
    return await view_user_data(
        payload, view_users_request.user_id, view_users_request.limit
    )


@Admin_Router.post("/otp/verify/email", status_code=status.HTTP_200_OK)
async def verify_email_otp_endpoint(
    otp_request: OTPRequest, payload=Depends(verify_jwt)
):
    """
    Verifies the OTP for email verification.
    """
    verified = await verify_email_otp(payload, otp_request.otp_code)
    if verified:
        return {"message": "Email verification successful"}
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired OTP for email verification",
    )


@Admin_Router.post("/otp/generate", status_code=status.HTTP_200_OK)
async def generate_otp_endpoint(otp_request: OTPRequest):
    """
    Generates and sends an OTP for the specified purpose.
    """
    return await generate_and_send_otp(otp_request.email, otp_request.purpose)

@Admin_Router.get("/retrain/status")
async def get_training_status_api(payload: dict = Depends(verify_jwt)):
    """
    API to fetch the current training status of the electricity consumption model.
    """
    try:
        # Call the method to fetch training status
        status = await get_training_status_from_file(payload)
        return status
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@Admin_Router.post("/retrain")
async def retrain_model_api(payload: dict = Depends(verify_jwt)):
    """
    API to retrain the electricity consumption prediction model.
    """
    admin_id = payload.get("user_id")
    admin = await Admin.get_or_none(id=admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins are authorized to view model training status.",
        )
    try:
        result = await retrain_model()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during model retraining: {str(e)}",
        )
