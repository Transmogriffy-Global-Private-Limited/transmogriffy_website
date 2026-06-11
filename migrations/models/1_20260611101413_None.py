from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "api_activity_log" (
    "id" UUID NOT NULL PRIMARY KEY,
    "requesting_ip" VARCHAR(45) NOT NULL,
    "request" JSONB NOT NULL,
    "response" JSONB,
    "endpoint_hit" VARCHAR(255) NOT NULL,
    "time_taken" DOUBLE PRECISION NOT NULL,
    "time_requested" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "time_responded" TIMESTAMPTZ,
    "error" TEXT,
    "error_location" VARCHAR(255)
);
COMMENT ON TABLE "api_activity_log" IS 'Model to track API activity details such as IP address, request, response,';
CREATE TABLE IF NOT EXISTS "admin" (
    "id" UUID NOT NULL PRIMARY KEY,
    "role" VARCHAR(5) NOT NULL DEFAULT 'admin',
    "name" VARCHAR(255) NOT NULL,
    "email" VARCHAR(100) NOT NULL UNIQUE,
    "email_verified" BOOL NOT NULL DEFAULT False,
    "password" VARCHAR(255) NOT NULL,
    "two_fa_status" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "admin"."role" IS 'Role of the admin';
COMMENT ON COLUMN "admin"."name" IS 'Name of the admin';
COMMENT ON COLUMN "admin"."password" IS 'Hashed password for admin login';
COMMENT ON COLUMN "admin"."created_at" IS 'Timestamp when the admin was created';
COMMENT ON COLUMN "admin"."updated_at" IS 'Timestamp when the admin was last updated';
CREATE TABLE IF NOT EXISTS "admin_otp" (
    "otp_code" VARCHAR(8) NOT NULL PRIMARY KEY,
    "purpose" VARCHAR(25) NOT NULL,
    "expiration" TIMESTAMPTZ NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "admin_id" UUID NOT NULL REFERENCES "admin" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "admin_otp"."purpose" IS 'Purpose of the OTP';
CREATE TABLE IF NOT EXISTS "Blacklisted_Tokens" (
    "Blacklisted_Tokens" VARCHAR(512) NOT NULL PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS "buynow" (
    "id" UUID NOT NULL PRIMARY KEY,
    "user_id" VARCHAR(600) NOT NULL,
    "product_id" VARCHAR(600) NOT NULL,
    "address_id" VARCHAR(600) NOT NULL,
    "quantity" INT NOT NULL DEFAULT 1,
    "price" INT NOT NULL,
    "currency" VARCHAR(10) NOT NULL DEFAULT 'INR',
    "payment_method" VARCHAR(100) NOT NULL,
    "order_status" VARCHAR(100) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "buynow"."user_id" IS 'ID of the user';
COMMENT ON COLUMN "buynow"."product_id" IS 'ID of the product';
COMMENT ON COLUMN "buynow"."address_id" IS 'ID of the delivery address';
COMMENT ON COLUMN "buynow"."quantity" IS 'Quantity of the product';
COMMENT ON COLUMN "buynow"."price" IS 'Total price for the purchase in paise';
COMMENT ON COLUMN "buynow"."payment_method" IS 'Payment method used';
COMMENT ON COLUMN "buynow"."order_status" IS 'Current status of the order';
CREATE TABLE IF NOT EXISTS "click_events" (
    "id" UUID NOT NULL PRIMARY KEY,
    "user_id" VARCHAR(100),
    "session_id" VARCHAR(100),
    "page_url" TEXT NOT NULL,
    "element_id" VARCHAR(255),
    "element_class" VARCHAR(255),
    "element_text" TEXT,
    "click_x" INT,
    "click_y" INT,
    "referrer" TEXT,
    "user_agent" TEXT,
    "ip_address" VARCHAR(45),
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "contact_us" (
    "id" UUID NOT NULL PRIMARY KEY,
    "firstname" VARCHAR(1200),
    "lastname" VARCHAR(1200),
    "telephone" VARCHAR(1200),
    "email" VARCHAR(1200),
    "message" TEXT,
    "contacted_at" TIMESTAMPTZ NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "order" (
    "id" UUID NOT NULL PRIMARY KEY,
    "userid" VARCHAR(600),
    "productid" VARCHAR(600),
    "totalamount" VARCHAR(600),
    "paymentoption" VARCHAR(600),
    "rzp_payment_id" VARCHAR(600) NOT NULL DEFAULT 'default_id',
    "rzp_order_id" VARCHAR(600) NOT NULL DEFAULT 'default_id',
    "orderstatus" VARCHAR(600),
    "ordered_quantity" VARCHAR(600),
    "deliveryaddress" VARCHAR(600),
    "reasonforcancel" VARCHAR(600),
    "otherreasonforcancel" VARCHAR(600),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "payments" (
    "id" UUID NOT NULL PRIMARY KEY,
    "userid" VARCHAR(600),
    "productid" VARCHAR(600),
    "paymentid" VARCHAR(600),
    "price" DOUBLE PRECISION,
    "currency" VARCHAR(600),
    "receipt" VARCHAR(600),
    "notes" VARCHAR(600),
    "paymentstatus" VARCHAR(600),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "product" (
    "id" UUID NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "model" VARCHAR(255) NOT NULL,
    "details" JSONB NOT NULL,
    "quantity" INT NOT NULL DEFAULT 1,
    "product_color" VARCHAR(255) NOT NULL,
    "is_listed" BOOL NOT NULL DEFAULT True,
    "price" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "mrp" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "price_paise" INT,
    "mrp_paise" INT,
    "currency" VARCHAR(10) NOT NULL DEFAULT 'INR',
    "images" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "product_instance" (
    "id" UUID NOT NULL PRIMARY KEY,
    "serial_number" VARCHAR(255) NOT NULL UNIQUE,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "product_id" UUID NOT NULL REFERENCES "product" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "product_instance"."serial_number" IS 'Unique Serial Number of the Product Instance';
CREATE TABLE IF NOT EXISTS "refund_instances" (
    "id" UUID NOT NULL PRIMARY KEY,
    "rzp_payment_id" VARCHAR(600) NOT NULL,
    "rzp_refund_id" VARCHAR(600) UNIQUE,
    "order_id" VARCHAR(600) NOT NULL,
    "total_order_amount_paise" INT NOT NULL,
    "refund_amount_paise" INT NOT NULL,
    "refund_status" VARCHAR(20) NOT NULL DEFAULT 'created',
    "failure_reason" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "refund_instances"."refund_status" IS 'CREATED: created\nPENDING: pending\nPROCESSED: processed\nFAILED: failed';
CREATE TABLE IF NOT EXISTS "transactions" (
    "id" UUID NOT NULL PRIMARY KEY,
    "razorpaypaymentid" VARCHAR(600),
    "userid" VARCHAR(600),
    "productid" VARCHAR(600),
    "price" VARCHAR(655),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "User" (
    "id" UUID NOT NULL PRIMARY KEY,
    "user_number" BIGINT NOT NULL UNIQUE,
    "name" VARCHAR(100) NOT NULL,
    "email" VARCHAR(100) NOT NULL UNIQUE,
    "email_verified" BOOL NOT NULL DEFAULT False,
    "phone_number" BIGINT,
    "password" VARCHAR(128) NOT NULL,
    "two_fa_status" BOOL NOT NULL DEFAULT False,
    "role" VARCHAR(5) NOT NULL DEFAULT 'user',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "profile_picture_url" VARCHAR(500),
    "profile_picture" BYTEA
);
COMMENT ON COLUMN "User"."role" IS 'user: user\nadmin: admin';
CREATE TABLE IF NOT EXISTS "address" (
    "id" UUID NOT NULL PRIMARY KEY,
    "type" VARCHAR(5) NOT NULL,
    "custom_type_name" VARCHAR(100),
    "house_building" VARCHAR(255) NOT NULL,
    "locality_street" VARCHAR(255) NOT NULL,
    "landmark" VARCHAR(255),
    "city" VARCHAR(100) NOT NULL,
    "po_ps" VARCHAR(100) NOT NULL,
    "district" VARCHAR(100) NOT NULL,
    "state" VARCHAR(100) NOT NULL,
    "pin" VARCHAR(6) NOT NULL,
    "country" VARCHAR(100) NOT NULL,
    "is_default" BOOL NOT NULL DEFAULT True,
    "user_id" UUID NOT NULL REFERENCES "User" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "address"."type" IS 'Type of Address (Home, Work, Other)';
COMMENT ON COLUMN "address"."custom_type_name" IS 'Custom name if type is ''Other''';
COMMENT ON COLUMN "address"."house_building" IS 'House/Building Number or Name';
COMMENT ON COLUMN "address"."locality_street" IS 'Locality or Street Name';
COMMENT ON COLUMN "address"."landmark" IS 'Landmark';
COMMENT ON COLUMN "address"."city" IS 'City Name';
COMMENT ON COLUMN "address"."po_ps" IS 'Post Office or Police Station';
COMMENT ON COLUMN "address"."district" IS 'District Name';
COMMENT ON COLUMN "address"."state" IS 'State Name';
COMMENT ON COLUMN "address"."pin" IS 'PIN Code';
COMMENT ON COLUMN "address"."country" IS 'Country Name';
COMMENT ON COLUMN "address"."is_default" IS 'Is this the default address?';
CREATE TABLE IF NOT EXISTS "cart" (
    "id" UUID NOT NULL PRIMARY KEY,
    "quantity" INT NOT NULL DEFAULT 1,
    "unit_price_paise" INT NOT NULL,
    "added_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "product_id" UUID NOT NULL REFERENCES "product" ("id") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "User" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_cart_user_id_d2f7dd" UNIQUE ("user_id", "product_id")
);
CREATE TABLE IF NOT EXISTS "inventory_reservation" (
    "id" UUID NOT NULL PRIMARY KEY,
    "quantity" INT NOT NULL,
    "expires_at" TIMESTAMPTZ NOT NULL,
    "converted" BOOL NOT NULL DEFAULT False,
    "released" BOOL NOT NULL DEFAULT False,
    "released_at" TIMESTAMPTZ,
    "expired" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "product_id" UUID NOT NULL REFERENCES "product" ("id") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "User" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_inventory_r_product_159b65" ON "inventory_reservation" ("product_id");
CREATE INDEX IF NOT EXISTS "idx_inventory_r_user_id_ddb26e" ON "inventory_reservation" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_inventory_r_expires_5fc654" ON "inventory_reservation" ("expires_at");
CREATE INDEX IF NOT EXISTS "idx_inventory_r_convert_170eea" ON "inventory_reservation" ("converted");
CREATE INDEX IF NOT EXISTS "idx_inventory_r_release_e0d2c8" ON "inventory_reservation" ("released");
CREATE TABLE IF NOT EXISTS "otp" (
    "otp_code" VARCHAR(8) NOT NULL PRIMARY KEY,
    "purpose" VARCHAR(25) NOT NULL,
    "expiration" TIMESTAMPTZ NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" UUID NOT NULL REFERENCES "User" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "otp"."purpose" IS 'Purpose of the OTP';
CREATE TABLE IF NOT EXISTS "orders_v2" (
    "id" UUID NOT NULL PRIMARY KEY,
    "status" VARCHAR(15) NOT NULL DEFAULT 'payment_pending',
    "payment_status" VARCHAR(14) NOT NULL DEFAULT 'pending',
    "subtotal_paise" INT NOT NULL,
    "total_paise" INT NOT NULL,
    "currency" VARCHAR(10) NOT NULL DEFAULT 'INR',
    "checkout_hash" VARCHAR(255) UNIQUE,
    "razorpay_order_id" VARCHAR(255) UNIQUE,
    "razorpay_payment_id" VARCHAR(255) UNIQUE,
    "paid_at" TIMESTAMPTZ,
    "cancelled_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "address_id" UUID NOT NULL REFERENCES "address" ("id") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "User" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_orders_v2_user_id_cc3e46" ON "orders_v2" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_orders_v2_status_631a96" ON "orders_v2" ("status");
CREATE INDEX IF NOT EXISTS "idx_orders_v2_razorpa_1bdfc4" ON "orders_v2" ("razorpay_order_id");
CREATE INDEX IF NOT EXISTS "idx_orders_v2_razorpa_d8cb0f" ON "orders_v2" ("razorpay_payment_id");
COMMENT ON COLUMN "orders_v2"."status" IS 'PAYMENT_PENDING: payment_pending\nPAID: paid\nCONFIRMED: confirmed\nPROCESSING: processing\nSHIPPED: shipped\nDELIVERED: delivered\nCANCELLED: cancelled\nREFUND_PENDING: refund_pending\nREFUNDED: refunded';
COMMENT ON COLUMN "orders_v2"."payment_status" IS 'PENDING: pending\nPAID: paid\nFAILED: failed\nREFUND_PENDING: refund_pending\nREFUNDED: refunded';
CREATE TABLE IF NOT EXISTS "order_items" (
    "id" UUID NOT NULL PRIMARY KEY,
    "product_name_snapshot" VARCHAR(255) NOT NULL,
    "product_model_snapshot" VARCHAR(255) NOT NULL,
    "product_details_snapshot" JSONB,
    "currency" VARCHAR(10) NOT NULL DEFAULT 'INR',
    "unit_price_paise" INT NOT NULL,
    "quantity" INT NOT NULL,
    "line_total_paise" INT NOT NULL,
    "order_id" UUID NOT NULL REFERENCES "orders_v2" ("id") ON DELETE CASCADE,
    "product_id" UUID REFERENCES "product" ("id") ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS "payments_v2" (
    "id" UUID NOT NULL PRIMARY KEY,
    "provider" VARCHAR(50) NOT NULL DEFAULT 'razorpay',
    "razorpay_order_id" VARCHAR(255) NOT NULL,
    "razorpay_payment_id" VARCHAR(255) UNIQUE,
    "razorpay_signature" TEXT,
    "amount_paise" INT NOT NULL,
    "currency" VARCHAR(10) NOT NULL,
    "status" VARCHAR(8) NOT NULL DEFAULT 'created',
    "raw_payload" JSONB,
    "provider_response" JSONB,
    "verified_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "order_id" UUID NOT NULL UNIQUE REFERENCES "orders_v2" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_payments_v2_razorpa_a4041e" ON "payments_v2" ("razorpay_order_id");
CREATE INDEX IF NOT EXISTS "idx_payments_v2_razorpa_7cabfe" ON "payments_v2" ("razorpay_payment_id");
CREATE INDEX IF NOT EXISTS "idx_payments_v2_status_1a3bbf" ON "payments_v2" ("status");
COMMENT ON COLUMN "payments_v2"."status" IS 'CREATED: created\nVERIFIED: verified\nFAILED: failed\nREFUNDED: refunded';
CREATE TABLE IF NOT EXISTS "product_review" (
    "id" UUID NOT NULL PRIMARY KEY,
    "rating" INT NOT NULL,
    "review" TEXT,
    "is_visible" BOOL NOT NULL DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "product_id" UUID NOT NULL REFERENCES "product" ("id") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "User" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_product_rev_product_d5fc5a" UNIQUE ("product_id", "user_id")
);
CREATE INDEX IF NOT EXISTS "idx_product_rev_product_51e92b" ON "product_review" ("product_id", "is_visible");
CREATE INDEX IF NOT EXISTS "idx_product_rev_user_id_d02d7c" ON "product_review" ("user_id");
COMMENT ON COLUMN "product_review"."rating" IS 'Rating from 1 to 5';
CREATE TABLE IF NOT EXISTS "refunds_v2" (
    "id" UUID NOT NULL PRIMARY KEY,
    "razorpay_refund_id" VARCHAR(255) UNIQUE,
    "amount_paise" INT NOT NULL,
    "processed_amount_paise" INT NOT NULL DEFAULT 0,
    "reason" TEXT,
    "status" VARCHAR(9) NOT NULL,
    "raw_payload" JSONB,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "order_id" UUID NOT NULL REFERENCES "orders_v2" ("id") ON DELETE CASCADE,
    "payment_id" UUID NOT NULL REFERENCES "payments_v2" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_refunds_v2_order_i_538cbe" ON "refunds_v2" ("order_id");
CREATE INDEX IF NOT EXISTS "idx_refunds_v2_payment_e688c5" ON "refunds_v2" ("payment_id");
CREATE INDEX IF NOT EXISTS "idx_refunds_v2_status_17b6b4" ON "refunds_v2" ("status");
COMMENT ON COLUMN "refunds_v2"."status" IS 'CREATED: created\nPENDING: pending\nPROCESSED: processed\nFAILED: failed';
CREATE TABLE IF NOT EXISTS "webhook_events" (
    "id" UUID NOT NULL PRIMARY KEY,
    "provider" VARCHAR(50) NOT NULL,
    "event_id" VARCHAR(255) NOT NULL UNIQUE,
    "event_type" VARCHAR(255) NOT NULL,
    "payload" JSONB NOT NULL,
    "processed" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
