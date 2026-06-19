import uuid
import logging

from typing import Dict
from fastapi import HTTPException, status

from Database_and_ORM.Database_Models import (
    Cart,
    Product,
)

from .Database_Schemas import (
    CartSchema,
    ManagementQuantity,
    GetCartOfauser,
)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


# -------------------------------------------------
# ADD TO CART
# NO STOCK DEDUCTION HERE
# -------------------------------------------------
async def add_to_cart(
    payload: Dict,
    cart_data: CartSchema
):
    userid = cart_data.user_id
    productid = cart_data.productid

    try:

        product = await Product.get(
            id=productid
        )

        if product.quantity <= 0:

            raise HTTPException(
                status_code=400,
                detail="Product out of stock"
            )

        existing = await Cart.filter(
            userid=userid,
            productid=productid
        ).first()

        if existing:

            raise HTTPException(
                status_code=400,
                detail="Product already in cart"
            )

        total_price = float(product.price)

        cart = await Cart.create(

            id=uuid.uuid4(),

            userid=userid,

            productid=productid,

            quantity=1,

            price=total_price,
        )

        return {
            "message": "Added to cart",
            "cart_id": str(cart.id)
        }

    except HTTPException:
        raise

    except Exception as e:

        logger.error(e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# -------------------------------------------------
# GET CART
# -------------------------------------------------
async def get_cart(
    payload: Dict,
    management_data: GetCartOfauser
):

    try:

        items = await Cart.filter(
            userid=management_data.user_id
        ).all()

        result = []

        for item in items:

            product = await Product.get(
                id=item.productid
            )

            result.append({

                "productid":
                str(item.productid),

                "quantity":
                item.quantity,

                "price":
                item.price,

                "product_name":
                product.name
            })

        return {

            "user_id":
            management_data.user_id,

            "cart_items":
            result
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# -------------------------------------------------
# INCREASE QUANTITY
# NO STOCK CHANGE
# -------------------------------------------------
async def increase_quantity(
    payload: Dict,
    management_data: ManagementQuantity
):

    userid = management_data.user_id
    productid = management_data.productid

    try:

        cart = await Cart.filter(
            userid=userid,
            productid=productid
        ).first()

        if not cart:

            raise HTTPException(
                status_code=404,
                detail="Cart item not found"
            )

        product = await Product.get(
            id=productid
        )

        new_quantity = cart.quantity + 1

        await Cart.filter(
            id=cart.id
        ).update(

            quantity=new_quantity,

            price=(
                float(product.price)
                * new_quantity
            )
        )

        return {
            "message":
            "Quantity increased"
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# -------------------------------------------------
# DECREASE QUANTITY
# NO STOCK CHANGE
# -------------------------------------------------
async def decrease_quantity(
    payload: Dict,
    management_data: ManagementQuantity
):

    userid = management_data.user_id
    productid = management_data.productid

    try:

        cart = await Cart.filter(
            userid=userid,
            productid=productid
        ).first()

        if not cart:

            raise HTTPException(
                status_code=404,
                detail="Cart item not found"
            )

        product = await Product.get(
            id=productid
        )

        if cart.quantity <= 1:

            await Cart.filter(
                id=cart.id
            ).delete()

            return {
                "message":
                "Item removed"
            }

        new_quantity = (
            cart.quantity
            - 1
        )

        await Cart.filter(
            id=cart.id
        ).update(

            quantity=new_quantity,

            price=(
                float(product.price)
                * new_quantity
            )
        )

        return {
            "message":
            "Quantity decreased"
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# -------------------------------------------------
# REMOVE CART ITEM
# NO STOCK CHANGE
# -------------------------------------------------
async def remove_from_cart(
    payload: Dict,
    management_data: ManagementQuantity
):

    try:

        deleted = await Cart.filter(
            userid=management_data.user_id,
            productid=management_data.productid
        ).delete()

        if not deleted:

            raise HTTPException(
                status_code=404,
                detail="Cart item not found"
            )

        return {

            "message":
            "Removed successfully"
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )