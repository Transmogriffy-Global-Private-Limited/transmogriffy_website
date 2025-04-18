import uuid
from fastapi import HTTPException, status
from Database_and_ORM.Database_Models import Cart, Product
from .Database_Schemas import CartSchema, ManagementQuantity, GetCartOfauser
from typing import Dict
import logging

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

async def add_to_cart(payload: Dict, cart_data: CartSchema):
    userid = cart_data.user_id
    productid = cart_data.productid
    price = float(cart_data.price)

    # Verify product exists and is in stock
    try:
        product = await Product.get(id=productid)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    if product.quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is out of stock",
        )

    # Check if already in cart
    existing = await Cart.filter(userid=userid, productid=productid).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is already in the cart.",
        )

    try:
        # Decrement stock
        await Product.filter(id=productid).update(quantity=product.quantity - 1)
        # Add to cart with quantity 1
        new_entry = await Cart.create(
            id=uuid.uuid4(),
            userid=userid,
            productid=productid,
            quantity=1,
            price=price,
        )
        return new_entry

    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add to cart: {str(e)}",
        )

async def get_cart(payload: Dict, management_data: GetCartOfauser):
    userid = management_data.user_id
    logger.debug(f"Fetching cart for user ID: {userid}")

    try:
        items = await Cart.filter(userid=userid).all()
        if not items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No items in cart for this user",
            )

        cart_list = [
            {"productid": i.productid, "quantity": i.quantity, "price": i.price}
            for i in items
        ]
        return {"user_id": userid, "cart_items": cart_list}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cart: {str(e)}",
        )

async def increase_quantity(payload: Dict, management_data: ManagementQuantity):
    userid = management_data.user_id
    productid = management_data.productid

    if not userid or not productid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields",
        )

    try:
        product = await Product.get(id=productid)
        if product.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product is out of stock",
            )

        cart_entry = await Cart.filter(userid=userid, productid=productid).first()
        if not cart_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart entry not found",
            )

        # Adjust stock and cart
        await Product.filter(id=productid).update(quantity=product.quantity - 1)
        await Cart.filter(userid=userid, productid=productid).update(
            quantity=cart_entry.quantity + 1,
            price=float(cart_entry.price) + float(product.price)
        )

        return {"message": "Quantity increased successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error increasing quantity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to increase quantity: {str(e)}",
        )

async def decrease_quantity(payload: Dict, management_data: ManagementQuantity):
    userid = management_data.user_id
    productid = management_data.productid
    logger.debug(f"Decreasing quantity for product: {productid}")

    if not userid or not productid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields",
        )

    try:
        cart_entry = await Cart.filter(userid=userid, productid=productid).first()
        if not cart_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart entry not found",
            )

        product = await Product.get(id=productid)

        if cart_entry.quantity <= 1:
            # Remove entry and restock completely
            await Cart.filter(userid=userid, productid=productid).delete()
            await Product.filter(id=productid).update(quantity=product.quantity + 1)
            return {"message": "Item removed from cart"}
        else:
            # Decrement cart and restock one unit
            await Cart.filter(userid=userid, productid=productid).update(
                quantity=cart_entry.quantity - 1,
                price=float(cart_entry.price) - float(product.price)
            )
            await Product.filter(id=productid).update(quantity=product.quantity + 1)
            return {"message": "Quantity decreased successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error decreasing quantity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decrease quantity: {str(e)}",
        )

async def remove_from_cart(payload: Dict, management_data: ManagementQuantity):
    userid = management_data.user_id
    productid = management_data.productid
    logger.debug(f"Removing product from cart: {productid}")

    if not userid or not productid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields",
        )

    try:
        cart_entry = await Cart.filter(userid=userid, productid=productid).first()
        if not cart_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart entry not found",
            )

        product = await Product.get(id=productid)
        # Remove and restock
        await Cart.filter(userid=userid, productid=productid).delete()
        await Product.filter(id=productid).update(quantity=product.quantity + cart_entry.quantity)

        return {"message": "Product removed from cart successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing product from cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove product: {str(e)}",
        )
