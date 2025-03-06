import uuid
from fastapi import HTTPException, status
from Database_and_ORM.Database_Models import Cart, Product
from .Database_Schemas import CartSchema,ManagementQuantity
from typing import Dict


async def add_to_cart(payload: Dict, cart_data: CartSchema):

    userid = cart_data.userid
    productid = cart_data.productid
    price = cart_data.price

    if not all([userid, productid, price]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields",
        )

    try:
        new_cart_entry = await Cart.create(
            id=uuid.uuid4(),
            userid=userid,
            productid=productid,
            quantity = 1,
            price=price
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

        # Update cart entry
        await Cart.filter(productid=productid).update(
            quantity=cart_entry.quantity + 1,
            price=str(float(cart_entry.price) + float(product.details['price']))
        )

        return {"message": "Quantity increased successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to increase quantity: {str(e)}",
        )

async def decrease_quantity(payload: Dict, management_data: ManagementQuantity):
    productid = management_data.productid
    if not productid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields",
        )

    try:
        # Retrieve the cart entry to update
        cart_entry = await Cart.get(productid=productid)
        if not cart_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart entry not found",
            )

        if cart_entry.quantity <= 1:
            # Remove cart entry if quantity reaches zero
            await Cart.filter(productid=productid).delete()
            # Update product quantity
            product = await Product.get(id=productid)
            await Product.filter(id=productid).update(quantity=product.quantity + 1)
            return {"message": "Quantity decreased to zero and cart entry removed"}
        else:
            # Update cart entry
            await Cart.filter(productid=productid).update(
                quantity=cart_entry.quantity - 1,
                price=str(float(cart_entry.price) - float(product.details['price']))
            )
            # Update product quantity
            product = await Product.get(id=productid)
            await Product.filter(id=productid).update(quantity=product.quantity + 1)
            return {"message": "Quantity decreased successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decrease quantity: {str(e)}",
        )