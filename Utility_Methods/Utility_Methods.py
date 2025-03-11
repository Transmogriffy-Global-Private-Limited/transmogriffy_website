from fastapi import HTTPException, status, Header
from Users.Data_Schemas import OTPTypeEnum
from Database_and_ORM.Database_Models import Blacklisted_Tokens, AdminOTP, OTP
from decouple import config
import jwt
import uuid
from datetime import datetime, timedelta, timezone
from passlib.hash import bcrypt
from uuid import UUID
import base64
import os
from typing import Union, Dict
from mimetypes import guess_type
from typing import Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend


async def get_token_from_authorization_header_value(
    authorization_header_value: str,
):
    token = authorization_header_value.split(" ")[1]
    return token


async def decode_jwt(token):
    payload = jwt.decode(
        token, config("JWT_SECRET_STRING"), algorithms=["HS256"]
    )
    return payload


async def encrypt_jwt(jwt_token: str) -> str:
    """
    Encrypts a JWT token using AES encryption.
    """
    SECRET_KEY = config("SYMMETRIC_ENCRYPTION_KEY").encode()[:32]
    iv = iv = os.urandom(16)
    cipher = Cipher(
        algorithms.AES(SECRET_KEY), modes.CBC(iv), backend=default_backend()
    )
    encryptor = cipher.encryptor()

    # Add padding to the JWT token to make it AES-block compatible
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(jwt_token.encode()) + padder.finalize()

    # Encrypt the padded data
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    # Encode the encrypted data and IV as Base64 for safe transport
    return base64.b64encode(iv + encrypted_data).decode("utf-8")


async def decrypt_jwt(encrypted_jwt: str) -> str:
    """
    Decrypts an encrypted JWT token using AES decryption.
    """
    # Decode the encrypted data from Base64
    SECRET_KEY = config("SYMMETRIC_ENCRYPTION_KEY").encode()[:32]
    encrypted_data = base64.b64decode(encrypted_jwt)

    # Extract the IV and the actual encrypted message
    iv = encrypted_data[:16]  # First 16 bytes are the IV
    ciphertext = encrypted_data[16:]

    # Set up the AES decryption
    cipher = Cipher(
        algorithms.AES(SECRET_KEY), modes.CBC(iv), backend=default_backend()
    )
    decryptor = cipher.decryptor()

    # Decrypt the ciphertext
    decrypted_padded_data = decryptor.update(ciphertext) + decryptor.finalize()

    # Remove padding from the decrypted data
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    decrypted_data = (
        unpadder.update(decrypted_padded_data) + unpadder.finalize()
    )

    return decrypted_data.decode("utf-8")


async def verify_jwt(authorization: str = Header(None)):
    """
    Dependency that verifies the JWT token and checks if it's blacklisted.
    """
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in",
        )

    try:
        token = await get_token_from_authorization_header_value(authorization)
        decrypted_token = await decrypt_jwt(token)
        payload = await decode_jwt(decrypted_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired, Please login again",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Check if the token is blacklisted
    if await Blacklisted_Tokens.get_or_none(Blacklisted_Tokens=token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You have already logged out. Please log in again.",
        )

    return payload  # Return the decoded payload if the token is valid


async def generate_random_otp() -> str:
    """Generates a random OTP of specified length."""
    return str(uuid.uuid4())[: int(config("OTP_DIGITS"))]


async def create_jwt(user_id: str, expiration_duration: int) -> str:
    """
    Generates a JWT token containing the user ID and expiration date.
    """
    if isinstance(user_id, UUID):
        user_id = str(user_id)

    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=expiration_duration),  # Token valid for 1 day
    }
    token = jwt.encode(payload, config("JWT_SECRET_STRING"), algorithm="HS256")
    encrypted_token = await encrypt_jwt(token)
    return encrypted_token


async def verify_otp(
    user_id: str, otp_code: str, purpose: OTPTypeEnum
) -> bool:
    """
    Verifies an OTP for a specific user and purpose. If valid, deletes the OTP.
    """
    otp_entry = await OTP.get_or_none(
        user_id=user_id, otp_code=otp_code, purpose=purpose
    )

    # Check OTP existence and expiration
    if otp_entry and otp_entry.expiration > datetime.now(timezone.utc):
        # OTP is valid; delete it after successful verification
        await otp_entry.delete()
        return True
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP",
        )


async def verify_admin_otp(
    admin_id: str, otp_code: str, purpose: OTPTypeEnum
) -> bool:
    """
    Verifies an OTP for a specific user and purpose. If valid, deletes the OTP.
    """
    otp_entry = await AdminOTP.get_or_none(
        admin_id=admin_id, otp_code=otp_code, purpose=purpose
    )

    # Check OTP existence and expiration
    if otp_entry and otp_entry.expiration > datetime.now(timezone.utc):
        # OTP is valid; delete it after successful verification
        await otp_entry.delete()
        return True
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP",
        )


async def verify_user_password(entered_password, user_password):
    verified = bcrypt.verify(entered_password, user_password)
    return verified


async def get_hashed_password(password):
    return str(bcrypt.hash(password))


async def encode_path_to_base64(
    path: str,
) -> Union[str, Dict[str, str]]:
    """
    Encodes the file or all files in the directory at the given path to Base64 with MIME type.
    If the path is a file, returns a Base64 string.
    If the path is a directory, returns a dictionary with filenames as keys and Base64 strings as values.
    Returns appropriate messages if the directory is empty or the path is invalid.
    """
    # Check if path is a file
    if os.path.isfile(path):
        mime_type, _ = guess_type(path)
        if mime_type is None:
            return "Could not determine MIME type for the file."

        with open(path, "rb") as file:
            encoded_string = base64.b64encode(file.read()).decode("utf-8")

        return f"data:{mime_type};base64,{encoded_string}"

    # Check if path is a directory
    elif os.path.isdir(path):
        files = os.listdir(path)
        if not files:
            return "Path provided is an empty directory."

        encoded_files = {}
        for file_name in files:
            file_path = os.path.join(path, file_name)
            if os.path.isfile(file_path):
                mime_type, _ = guess_type(file_path)
                if mime_type is None:
                    encoded_files[file_name] = "Could not determine MIME type"
                    continue

                with open(file_path, "rb") as file:
                    encoded_string = base64.b64encode(file.read()).decode(
                        "utf-8"
                    )
                    encoded_files[file_name] = (
                        f"data:{mime_type};base64,{encoded_string}"
                    )

        return encoded_files

    # Path is neither a file nor a directory
    return "Invalid path provided. Path is neither a file nor a directory, or doesn't exist."


async def parse_limit_to_years(limit: Optional[str]) -> list:
    """
    Parses the `limit` parameter into a sorted list of valid years.
    Supports:
        - Single years: "2021"
        - Year ranges: "2021-2025"
        - Combinations: "2021,2023-2025"
    """
    if not limit:
        return []

    years = []
    current_year = datetime.now().year

    try:
        for part in limit.split(","):
            if "-" in part:  # Handle ranges like "2021-2025"
                start, end = map(int, part.split("-"))

                # Validate range boundaries
                if start > end:
                    raise ValueError(f"Invalid range: {start}-{end}")
                if start < 2000 or end > current_year:
                    raise ValueError(
                        f"Year range out of bounds: {start}-{end} (Valid: 1900-{current_year})"
                    )

                years.extend(range(start, end + 1))

            else:  # Handle single years like "2021"
                year = int(part)

                # Validate single year boundaries
                if year < 1900 or year > current_year:
                    raise ValueError(
                        f"Year out of bounds: {year} (Valid: 1900-{current_year})"
                    )
                years.append(year)

        return sorted(set(years))  # Remove duplicates and sort

    except ValueError as e:
        raise ValueError(f"Invalid limit format or year range: {e}")
