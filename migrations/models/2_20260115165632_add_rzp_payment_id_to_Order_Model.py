from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
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
COMMENT ON COLUMN "refund_instances"."refund_status" IS 'CREATED: created\nPENDING: pending\nPROCESSED: processed\nFAILED: failed';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "refund_instances";"""
