import uuid
from fastapi import HTTPException, status
from Database_and_ORM.Database_Models import Cart, Product
from .Database_Schemas import CartSchema, ManagementQuantity
from typing import Dict
import logging

# Creating an object
logger = logging.getLogger()

# Setting the threshold of logger to DEBUG
logger.setLevel(logging.DEBUG)

async def add_to_cart(payload: Dict, cart_data: CartSchema):

    userid = cart_data.user_id
    productid = cart_data.productid
    price = cart_data.price

    try:
        new_cart_entry = await Cart.create(
            id=uuid.uuid4(),
            userid=userid,
            productid=productid,
            quantity=1,
            price=price,
        )
        return new_cart_entry
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add to cart: {str(e)}",
        )

async def increase_quantity(payload: Dict, management_data: ManagementQuantity):
    productid = management_data.productid
    if not productid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields",
        )

    try:
        # Retrieve the product to check availability
        product = await Product.get(id=productid)
        if product.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product is out of stock",
            )

        # Retrieve the cart entry to update
        cart_entry = await Cart.get(productid=productid)
        if not cart_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart entry not found",
            )

        # Update product quantity
        await Product.filter(id=productid).update(quantity=product.quantity - 1)

        # Update cart entry with correct price handling
        await Cart.filter(productid=productid).update(
            quantity=cart_entry.quantity + 1,
            price=float(cart_entry.price) + float(product.price),  # Corrected line
        )

        return {"message": "Quantity increased successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to increase quantity: {str(e)}",
        )
async def decrease_quantity(payload: Dict, management_data: ManagementQuantity):
    productid = management_data.productid
    logger.debug("incoming productid", productid)
    
    if not productid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields",
        )

    try:
        # Retrieve the cart entry to update
        cart_entry = await Cart.get(productid=productid)
        logger.debug("cart entry", cart_entry)

        if not cart_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart entry not found",
            )

        # Retrieve the product once
        product = await Product.get(id=productid)
        logger.debug("received product", product)

        # Check if quantity in cart is 1 or less
        if cart_entry.quantity <= 1:
            # Remove the cart entry if quantity is 1 or less
            await Cart.filter(productid=productid).delete()
            await Product.filter(id=productid).update(
                quantity=product.quantity + 1
            )
            return {
                "message": "Quantity decreased to zero and cart entry removed"
            }
        else:
            # Update cart entry with decreased quantity and price
            await Cart.filter(productid=productid).update(
                quantity=cart_entry.quantity - 1,
                price=float(cart_entry.price) - float(product.price),
            )
            # Update product quantity in stock
            await Product.filter(id=productid).update(
                quantity=product.quantity + 1
            )
            return {"message": "Quantity decreased successfully"}

    except HTTPException as http_exc:
        raise http_exc  # Re-raise HTTP exceptions to preserve status code and message
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decrease quantity: {str(e)}",
        )
