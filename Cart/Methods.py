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


# -----------------------------------------
# ADD TO CART
# -----------------------------------------
async def add_to_cart(
    payload: Dict,
    cart_data: CartSchema
):

    try:

        userid = cart_data.user_id
        productid = cart_data.productid

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

        cart = await Cart.create(

            id=uuid.uuid4(),

            userid=userid,

            productid=productid,

            quantity=1,

            price=float(
                product.price
            )
        )

        return {
            "message":
            "Added to cart",

            "cart_id":
            str(cart.id)
        }

    except HTTPException:
        raise

    except Exception as e:

        logger.exception(e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# -----------------------------------------
# GET CART
# -----------------------------------------
async def get_cart(
    payload: Dict,
    management_data: GetCartOfauser
):

    try:

        carts = await Cart.filter(
            userid=management_data.user_id
        ).all()

        output = []

        for item in carts:

            product = await Product.get(
                id=item.productid
            )

            output.append({

                "productid":
                str(item.productid),

                "product_name":
                product.name,

                "available_stock":
                product.quantity,

                "cart_quantity":
                item.quantity,

                "price":
                item.price
            })

        return {

            "user_id":
            management_data.user_id,

            "cart_items":
            output
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# -----------------------------------------
# INCREASE QUANTITY
# CHECK STOCK LIMIT
# -----------------------------------------
async def increase_quantity(
    payload: Dict,
    management_data: ManagementQuantity
):

    try:

        userid = management_data.user_id
        productid = management_data.productid

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

        if cart.quantity >= product.quantity:

            raise HTTPException(
                status_code=400,
                detail=(
         #           f"Only "
          #          f"{product.quantity} "
                    f"Out of stock"
                )
            )

        new_qty = (
            cart.quantity
            + 1
        )

        await Cart.filter(
            id=cart.id
        ).update(

            quantity=new_qty,

            price=(
                float(product.price)
                * new_qty
            )
        )

        return {

            "message":
            "Quantity increased",

            "quantity":
            new_qty
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# -----------------------------------------
# DECREASE QUANTITY
# -----------------------------------------
async def decrease_quantity(
    payload: Dict,
    management_data: ManagementQuantity
):

    try:

        cart = await Cart.filter(
            userid=management_data.user_id,
            productid=management_data.productid
        ).first()

        if not cart:

            raise HTTPException(
                status_code=404,
                detail="Cart not found"
            )

        if cart.quantity == 1:

            await cart.delete()

            return {
                "message":
                "Item removed"
            }

        product = await Product.get(
            id=cart.productid
        )

        qty = (
            cart.quantity
            - 1
        )

        await Cart.filter(
            id=cart.id
        ).update(

            quantity=qty,

            price=(
                float(product.price)
                * qty
            )
        )

        return {

            "message":
            "Quantity decreased",

            "quantity":
            qty
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# -----------------------------------------
# REMOVE FROM CART
# -----------------------------------------
async def remove_from_cart(
    payload: Dict,
    management_data: ManagementQuantity
):

    try:

        deleted = await Cart.filter(

            userid=management_data.user_id,

            productid=management_data.productid

        ).delete()

        if deleted == 0:

            raise HTTPException(
                status_code=404,
                detail="Cart item not found"
            )

        return {
            "message":
            "Removed from cart"
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )