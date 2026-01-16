email_templates = {
    "password_reset": {
        "subject": "Password Reset Request for {username}",
        "body": (
            "Hello {username},\n\n"
            "You requested a password reset. Use the OTP below to reset your password.:\n"
            "{otp_code}\n\n"
            "The OTP will be valid for 10 mins \n\n"
            "If you did not request this, please ignore this email."
        ),
    },
    "2fa_verification": {
        "subject": "Your 2FA Verification Code",
        "body": (
            "Hi {username},\n\n"
            "Your 2FA code is: {otp_code}\n\n"
            "Please enter this code to complete your login process. This will be valid for 10 minutes"
        ),
    },
    "email_verification": {
        "subject": "Verify Your Email Address",
        "body": (
            "Hello {username},\n\n"
            "Thank you for signing up! Please use the following OTP to verify your email address:\n"
            "OTP: {otp_code}\n\n"
            "This code will expire in 10 minutes. If you did not sign up, please ignore this email."
        ),
    },
        "ordercreated": {
        "subject": "Order placed successfully (User: {username})",
        "body": (
            "Hi {username},\n\n"
            "Your order has been placed successfully.\n\n"
            "Order summary:\n"
            "{order_summary}\n\n"
            "Delivery address: {delivery_address}\n"
            "Payment option: {payment_option}\n\n"
            "Thanks,\n"
            "Team"
        ),
    },

    "updatedorder": {
        "subject": "Order status update: {order_id}",
        "body": (
            "Hi {username},\n\n"
            "Your order status has been updated.\n\n"
            "Order ID: {order_id}\n"
            "Product: {product_name} ({product_model})\n"
            "Quantity: {quantity}\n"
            "Old status: {old_status}\n"
            "New status: {new_status}\n\n"
            "Thanks,\n"
            "Team"
        ),
    },

    "canceledorder": {
        "subject": "Order canceled: {order_id}",
        "body": (
            "Hi {username},\n\n"
            "Your order has been canceled.\n\n"
            "Order ID: {order_id}\n"
            "Product: {product_name} ({product_model})\n"
            "Quantity: {quantity}\n"
            "Reason: {reason}\n\n"
            "Thanks,\n"
            "Team"
        ),
    },

    "deletedorder": {
        "subject": "Order deleted: {order_id}",
        "body": (
            "Hi {username},\n\n"
            "Your order record has been deleted.\n\n"
            "Order ID: {order_id}\n"
            "If you believe this was a mistake, please contact support.\n\n"
            "Thanks,\n"
            "Team"
        ),
    },
    "adordercreated": {
        "subject": "🛒 New Order Placed by {customer_name}",
        "body": (
            "New order has been placed.\n\n"
            "Customer:\n"
            "- Name: {customer_name}\n"
            "- Email: {customer_email}\n\n"
            "Order IDs:\n"
            "{order_ids}\n\n"
            "Order Summary:\n"
            "{order_summary}\n\n"
            "Payment option: {payment_option}\n"
            "Delivery address: {delivery_address}\n"
            "Total amount: {total_amount}\n\n"
            "Please check the admin panel for details."
        ),
    },
}
