import uuid
from fastapi import HTTPException, status
from Database_and_ORM.Database_Models import Cart, Product
from .Database_Schemas import CartSchema, ManagementQuantity, GetCartOfauser
from typing import Dict
import logging

logger = logging.getLogger("cart_methods")
logger.setLevel(logging.DEBUG)


async def add_to_cart(payload: Dict, cart_data: CartSchema):
    userid = cart_data.user_id
    productid = cart_data.productid

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

    unit_price = float(product.price)
    existing = await Cart.filter(userid=userid, productid=productid).first()
    
    try:
        if existing:
            new_qty = existing.quantity + 1
            await Cart.filter(userid=userid, productid=productid).update(
                quantity=new_qty,
                price=float(existing.price) + unit_price
            )
            await Product.filter(id=productid).update(quantity=product.quantity - 1)
            updated_entry = await Cart.filter(userid=userid, productid=productid).first()
            return updated_entry
        else:
            await Product.filter(id=productid).update(quantity=product.quantity - 1)
            new_entry = await Cart.create(
                id=uuid.uuid4(),
                userid=userid,
                productid=productid,
                quantity=1,
                price=unit_price,
            )
            return new_entry

    except Exception as e:
        logger.error(f"Error adding to cart during database execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add to cart: {str(e)}",
        )


async def get_cart(payload: Dict, management_data: GetCartOfauser):
    userid = management_data.user_id
    logger.debug(f"Fetching cart for user ID: {userid}")

    try:
        items = await Cart.filter(userid=userid).all()
        
        # ✅ FIXED: Enforce returning an explicit dictionary containing "cart_items" 
        # to prevent frontend response.data.cart_items reading crashes
        cart_list = [
            {
                "productid": str(i.productid), 
                "quantity": int(i.quantity), 
                "price": float(i.price)
            }
            for i in items
        ]
        return {"user_id": userid, "cart_items": cart_list}

    except Exception as e:
        logger.error(f"Error fetching cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cart: {str(e)}",
        )


async def increase_quantity(payload: Dict, management_data: ManagementQuantity):
    userid = management_data.user_id
    productid = management_data.productid

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

    try:
        cart_entry = await Cart.filter(userid=userid, productid=productid).first()
        if not cart_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart entry not found",
            )

        product = await Product.get(id=productid)

        if cart_entry.quantity <= 1:
            await Cart.filter(userid=userid, productid=productid).delete()
            await Product.filter(id=productid).update(quantity=product.quantity + 1)
            return {"message": "Item removed from cart"}
        else:
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

    try:
        cart_entry = await Cart.filter(userid=userid, productid=productid).first()
        if not cart_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart entry not found",
            )

        product = await Product.get(id=productid)
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