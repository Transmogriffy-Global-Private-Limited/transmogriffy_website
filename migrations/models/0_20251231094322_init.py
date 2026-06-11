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
    "price" DOUBLE PRECISION NOT NULL,
    "payment_method" VARCHAR(100) NOT NULL,
    "order_status" VARCHAR(100) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "buynow"."user_id" IS 'ID of the user';
COMMENT ON COLUMN "buynow"."product_id" IS 'ID of the product';
COMMENT ON COLUMN "buynow"."address_id" IS 'ID of the delivery address';
COMMENT ON COLUMN "buynow"."quantity" IS 'Quantity of the product';
COMMENT ON COLUMN "buynow"."price" IS 'Total price for the purchase';
COMMENT ON COLUMN "buynow"."payment_method" IS 'Payment method used';
COMMENT ON COLUMN "buynow"."order_status" IS 'Current status of the order';
CREATE TABLE IF NOT EXISTS "cart" (
    "id" UUID NOT NULL PRIMARY KEY,
    "userid" VARCHAR(600) NOT NULL,
    "productid" VARCHAR(600) NOT NULL,
    "quantity" INT NOT NULL,
    "price" DOUBLE PRECISION NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
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
CREATE TABLE IF NOT EXISTS "contactus" (
    "id" UUID NOT NULL PRIMARY KEY,
    "firstname" VARCHAR(1200) NOT NULL,
    "lastname" VARCHAR(1200) NOT NULL,
    "telephone" VARCHAR(1200) NOT NULL,
    "email" VARCHAR(1200) NOT NULL,
    "message" TEXT NOT NULL,
    "contacted_at" TIMESTAMPTZ NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "order" (
    "id" UUID NOT NULL PRIMARY KEY,
    "userid" VARCHAR(600) NOT NULL,
    "productid" VARCHAR(600) NOT NULL,
    "totalamount" VARCHAR(600) NOT NULL,
    "paymentoption" VARCHAR(600) NOT NULL,
    "orderstatus" VARCHAR(600) NOT NULL,
    "ordered_quantity" VARCHAR(600) NOT NULL,
    "deliveryaddress" VARCHAR(600) NOT NULL,
    "reasonforcancel" VARCHAR(600),
    "otherreasonforcancel" VARCHAR(600),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "payments" (
    "id" UUID NOT NULL PRIMARY KEY,
    "userid" VARCHAR(600) NOT NULL,
    "productid" VARCHAR(600) NOT NULL,
    "paymentid" VARCHAR(600) NOT NULL,
    "price" DOUBLE PRECISION NOT NULL,
    "currency" VARCHAR(600) NOT NULL,
    "receipt" VARCHAR(600) NOT NULL,
    "notes" VARCHAR(600) NOT NULL,
    "paymentstatus" VARCHAR(600) NOT NULL,
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
CREATE TABLE IF NOT EXISTS "transactions" (
    "id" UUID NOT NULL PRIMARY KEY,
    "razorpaypaymentid" VARCHAR(600) NOT NULL,
    "userid" VARCHAR(600) NOT NULL,
    "productid" VARCHAR(600) NOT NULL,
    "price" VARCHAR(655) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "User" (
    "id" UUID NOT NULL PRIMARY KEY,
    "user_number" INT NOT NULL UNIQUE,
    "name" VARCHAR(100) NOT NULL,
    "email" VARCHAR(100) NOT NULL UNIQUE,
    "email_verified" BOOL NOT NULL DEFAULT False,
    "phone_number" BIGINT,
    "password" VARCHAR(128) NOT NULL,
    "two_fa_status" BOOL NOT NULL DEFAULT False,
    "role" VARCHAR(5) NOT NULL DEFAULT 'user',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
CREATE TABLE IF NOT EXISTS "otp" (
    "otp_code" VARCHAR(8) NOT NULL PRIMARY KEY,
    "purpose" VARCHAR(25) NOT NULL,
    "expiration" TIMESTAMPTZ NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" UUID NOT NULL REFERENCES "User" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "otp"."purpose" IS 'Purpose of the OTP';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
