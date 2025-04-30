from math import prod
from Database_and_ORM.Database_Models import Product, Order

async def product_analytics():
 
    analytics_results = []

    products = await Product.all()

    for product in products:

        orders = await Order.filter(productid=str(product.id))

        total_orders = len(orders)
        total_quantity = 0

        for order in orders:
            try:
                quantity = int(order.ordered_quantity)
            except (ValueError, TypeError):
                quantity = 0
            total_quantity += quantity
        
        total_sales = product.price * total_quantity

        analytics_results.append({
            "product_id": str(product.id),
            "product_name": product.name,
            "product_model": product.model,
            "total_orders": total_orders,
            "total_quantity": total_quantity,
            "total_sales": total_sales
        })

    return analytics_results


    
async def product_stock_analysis():
    stock_results = []
    products_in_stock = await Product.filter(is_listed=True)

    for product in products_in_stock:
        # Get all orders for this product
        orders = await Order.filter(productid=product.id)

        # Sum total ordered quantity
        total_ordered = sum(
            int(order.ordered_quantity or 0)
            for order in orders
            if isinstance(order.ordered_quantity, (int, str))
        )

        # Assume product.quantity is the **current** quantity (i.e. after orders placed)
        # Then, initial stock = current quantity + total ordered
        initial_stock = product.quantity + total_ordered

        remaining_stock = product.quantity  # just the current stock

        stock_results.append({
            "product_id": str(product.id),
            "product_name": product.name,
            "initial_stock": initial_stock,
            "total_ordered": total_ordered,
            "remaining_stock": remaining_stock
        })

    return stock_results



async def total_sales():

    total_sales_amount = 0.0

    products = await Product.all()

    for product in products:
        orders = await Order.filter(productid=str(product.id))
        total_quantity = 0
        for order in orders:
            try:
                quantity = int(order.ordered_quantity)
            except (ValueError, TypeError):
                quantity = 0
            total_quantity += quantity
        total_sales_amount += product.price * total_quantity

    return total_sales_amount



async def user_purchase_summary(user_id: str):
    orders = await Order.filter(userid=user_id)
    purchase_summary = {}
    for order in orders:
        try:
            quantity = int(order.ordered_quantity)
        except (ValueError, TypeError):
            quantity = 0

        pid = order.productid
        if pid not in purchase_summary:
            purchase_summary[pid] = {"total_items": 0}
        purchase_summary[pid]["total_items"] += quantity

    result_summary = []
    for pid, summary in purchase_summary.items():
        product = await Product.get(id=pid)
        total_items = summary["total_items"]
        total_amount = product.price * total_items

        result_summary.append({
            "product_id": pid,
            "product_name": product.name,
            "total_items_purchased": total_items,
            "total_purchase_amount": total_amount
        })

    return result_summary

async def user_total_spent_and_orders(user_id: str):
    orders = await Order.filter(userid=user_id)
    total_spent = 0.0
    total_orders = len(orders)

    for order in orders:
        try:
            quantity = int(order.ordered_quantity)
        except (ValueError, TypeError):
            quantity = 0

        product = await Product.get(id=order.productid)
        total_spent += product.price * quantity

    return {
        "user_id": user_id,
        "total_orders": total_orders,
        "total_spent": total_spent
    }
