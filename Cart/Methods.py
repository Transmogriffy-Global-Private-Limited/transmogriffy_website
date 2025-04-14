import uuid
from fastapi import HTTPException, status
from Database_and_ORM.Database_Models import Cart, Product
from .Database_Schemas import CartSchema, ManagementQuantity,GetCartOfauser
from typing import Dict
import logging

# Creating an object
logger = logging.getLogger()

# Setting the threshold of logger to DEBUG
logger.setLevel(logging.DEBUG)

async def add_to_cart(payload: Dict, cart_data: CartSchema):

    userid = cart_data.user_id
    productid = cart_data.productid
    price = float(cart_data.price)
  # Check if the product is already in the user's cart
    existing_cart_entry = await Cart.filter(userid=userid, productid=productid).first()
        
    if existing_cart_entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product is already in the cart.",
            )
    try:    
        # If the product isn't in the cart, create a new entry
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


async def get_cart(payload: Dict, management_data: GetCartOfauser):
    userid = management_data.user_id
    logger.debug(f"Fetching cart for user ID: {userid}")

    try:
        # Retrieve all cart entries for the given user
        user_cart = await Cart.filter(userid=userid).all()
        
        if not user_cart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No items found in the cart for this user",
            )

        # Convert the cart entries to a list of dictionaries for easier serialization
        cart_items = [
            {
                "productid": item.productid,
                "quantity": item.quantity,
                "price": item.price,
            }
            for item in user_cart
        ]
        
        return {"user_id": userid, "cart_items": cart_items}

    except Exception as e:
        logger.error(f"Error fetching cart: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cart: {str(e)}",
        )

async def increase_quantity(payload: Dict, management_data: ManagementQuantity):
    productid = management_data.productid
    userid = management_data.user_id  # Assuming user_id is passed in management_data
    if not productid or not userid:
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

        # Retrieve the cart entry for the specific user and product
        cart_entry = await Cart.filter(userid=userid, productid=productid).first()
        if not cart_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart entry not found for this user and product",
            )

        # Update product quantity (decrease by 1)
        await Product.filter(id=productid).update(quantity=product.quantity - 1)

        # Update cart entry with correct price and increased quantity
        await Cart.filter(userid=userid, productid=productid).update(
            quantity=cart_entry.quantity + 1,
            price=float(cart_entry.price) + float(product.price),  # Corrected price handling
        )

        return {"message": "Quantity increased successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to increase quantity: {str(e)}",
        )

    
async def decrease_quantity(payload: Dict, management_data: ManagementQuantity):
    productid = management_data.productid
    userid = management_data.user_id  # Assuming user_id is passed in management_data
    logger.debug("Incoming productid for decrease", productid)
    
    if not productid or not userid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields",
        )

    try:
        # Retrieve the cart entry for the given user and product
        cart_entry = await Cart.filter(userid=userid, productid=productid).first()
        logger.debug("Cart entry", cart_entry)

        if not cart_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart entry not found for this user and product",
            )

        # Retrieve the product details
        product = await Product.get(id=productid)
        logger.debug("Received product", product)

        # Check if quantity in cart is 1 or less
        if cart_entry.quantity <= 1:
            # Remove the cart entry if quantity is 1 or less
            await Cart.filter(userid=userid, productid=productid).delete()
            await Product.filter(id=productid).update(
                quantity=product.quantity + 1
            )
            return {
                "message": "Quantity decreased to zero and cart entry removed"
            }
        else:
            # Update cart entry with decreased quantity and price
            await Cart.filter(userid=userid, productid=productid).update(
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
        logger.error(f"Error decreasing product quantity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decrease quantity: {str(e)}",
        )



async def remove_from_cart(payload: Dict, management_data: ManagementQuantity):
    productid = management_data.productid
    userid = management_data.user_id  # Assuming user_id is passed in management_data
    logger.debug("Incoming productid for removal", productid)

    if not productid or not userid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields",
        )

    try:
        # Retrieve the cart entry for the given user and product
        cart_entry = await Cart.filter(userid=userid, productid=productid).first()
        
        if not cart_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart entry not found for this user and product",
            )

        # Retrieve the product details
        product = await Product.get(id=productid)

        # Remove the cart entry
        await Cart.filter(userid=userid, productid=productid).delete()

        # Update the product quantity in stock
        await Product.filter(id=productid).update(
            quantity=product.quantity + cart_entry.quantity
        )

        return {"message": "Product removed from cart successfully"}

    except HTTPException as http_exc:
        raise http_exc  # Re-raise HTTP exceptions to preserve status code and message
    except Exception as e:
        logger.error(f"Error removing product from cart: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove product from cart: {str(e)}",
        )
