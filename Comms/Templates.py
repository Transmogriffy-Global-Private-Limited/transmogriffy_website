email_templates = {
    "Password_Reset": {
        "subject": "Password Reset Request for {username}",
        "body": (
            "Hello {username},\n\n"
            "You requested a password reset. Use the OTP below to reset your password.:\n"
            "{otp_code}\n\n"
            "The OTP will be valid for 10 mins \n\n"
            "If you did not request this, please ignore this email."
        ),
    },
    "2FA": {
        "subject": "Your 2FA Verification Code",
        "body": (
            "Hi {username},\n\n"
            "Your 2FA code is: {otp_code}\n\n"
            "Please enter this code to complete your login process. This will be valid for 10 minutes"
        ),
    },
    "Mail Verification": {
        "subject": "Verify Your Email Address",
        "body": (
            "Hello {username},\n\n"
            "Thank you for signing up! Please use the following OTP to verify your email address:\n"
            "OTP: {otp_code}\n\n"
            "This code will expire in 10 minutes. If you did not sign up, please ignore this email."
        ),
    },
}
