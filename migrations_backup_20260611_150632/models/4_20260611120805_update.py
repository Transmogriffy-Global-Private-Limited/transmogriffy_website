from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    -- =========================
    -- INVENTORY RESERVATION
    -- =========================

    CREATE TABLE IF NOT EXISTS inventory_reservation (
        id UUID PRIMARY KEY,
        quantity INT NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL,
        converted BOOLEAN NOT NULL DEFAULT FALSE,
        released BOOLEAN NOT NULL DEFAULT FALSE,
        released_at TIMESTAMPTZ,
        expired BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        product_id UUID REFERENCES product(id) ON DELETE CASCADE,
        user_id UUID REFERENCES "User"(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_inventory_product
    ON inventory_reservation(product_id);

    CREATE INDEX IF NOT EXISTS idx_inventory_user
    ON inventory_reservation(user_id);

    CREATE INDEX IF NOT EXISTS idx_inventory_expiry
    ON inventory_reservation(expires_at);

    CREATE INDEX IF NOT EXISTS idx_inventory_converted
    ON inventory_reservation(converted);

    -- removed released index (causing migration failure)



    -- =========================
    -- PRODUCT
    -- =========================

    ALTER TABLE product
    ADD COLUMN IF NOT EXISTS price_paise INT;

    ALTER TABLE product
    ADD COLUMN IF NOT EXISTS mrp_paise INT;

    ALTER TABLE product
    ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'INR';



    -- =========================
    -- USER
    -- =========================

    ALTER TABLE "User"
    ADD COLUMN IF NOT EXISTS profile_picture_url VARCHAR(500);



    -- =========================
    -- BUYNOW
    -- =========================

    ALTER TABLE buynow
    ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'INR';



    -- =========================
    -- WEBHOOK EVENTS
    -- =========================

    CREATE TABLE IF NOT EXISTS webhook_events (
        id UUID PRIMARY KEY,
        provider VARCHAR(50),
        event_id VARCHAR(255) UNIQUE,
        event_type VARCHAR(255),
        payload JSONB,
        processed BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );



    -- =========================
    -- CART FK (safe)
    -- =========================

    DO $$
    BEGIN

        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname='fk_cart_User_b0fc81c0'
        ) THEN
            ALTER TABLE cart
            ADD CONSTRAINT fk_cart_User_b0fc81c0
            FOREIGN KEY (user_id)
            REFERENCES "User"(id)
            ON DELETE CASCADE;
        END IF;

        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname='fk_cart_product_92186a63'
        ) THEN
            ALTER TABLE cart
            ADD CONSTRAINT fk_cart_product_92186a63
            FOREIGN KEY (product_id)
            REFERENCES product(id)
            ON DELETE CASCADE;
        END IF;

    END $$;

    CREATE UNIQUE INDEX IF NOT EXISTS uid_cart_user_id_d2f7dd
    ON cart(user_id, product_id);

    """
    

async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    DROP INDEX IF EXISTS uid_cart_user_id_d2f7dd;

    ALTER TABLE cart
    DROP CONSTRAINT IF EXISTS fk_cart_User_b0fc81c0;

    ALTER TABLE cart
    DROP CONSTRAINT IF EXISTS fk_cart_product_92186a63;

    DROP TABLE IF EXISTS inventory_reservation;

    DROP TABLE IF EXISTS webhook_events;

    ALTER TABLE product
    DROP COLUMN IF EXISTS price_paise;

    ALTER TABLE product
    DROP COLUMN IF EXISTS mrp_paise;

    ALTER TABLE product
    DROP COLUMN IF EXISTS currency;

    ALTER TABLE buynow
    DROP COLUMN IF EXISTS currency;

    ALTER TABLE "User"
    DROP COLUMN IF EXISTS profile_picture_url;
    """
