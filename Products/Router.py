from fastapi import (
    APIRouter,
    Depends,
    Header,
    status,
    HTTPException,
    File,
    Query,
    UploadFile,
)
from Utility_Methods.Utility_Methods import verify_jwt
from Products.Methods import (
    add_product,
    update_product,
    toggle_product_listing,
    get_product,
    upload_product_images,
    remove_product_images,
    get_all_products,
)
from Products.Methods import ProductSearchEngine, DelistedProductSearchEngine
from Products.Data_Schemas import (
    AddProductSchema,
    UpdateProductSchema,
    ToggleProductListingSchema,
    SearchProductsSchema,
    ProductResponse,
)
from typing import List

Products_Router = APIRouter()

# ✅ Search Engine Instances
product_search_engine = ProductSearchEngine()
delisted_product_search_engine = DelistedProductSearchEngine()


@Products_Router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_product_endpoint(
    product_data: AddProductSchema, payload: dict = Depends(verify_jwt)
):
    return await add_product(payload, product_data)


@Products_Router.put("/update", status_code=status.HTTP_200_OK)
async def update_product_endpoint(
    product_data: UpdateProductSchema, payload: dict = Depends(verify_jwt)
):
    """🔹 Updates a product (Admin Only)."""
    return await update_product(payload, product_data)


@Products_Router.put("/toggle-listing", status_code=status.HTTP_200_OK)
async def toggle_product_listing_endpoint(
    product_data: ToggleProductListingSchema,
    payload: dict = Depends(verify_jwt),
):
    """🔹 Toggles a product's listing status (Admin Only)."""
    return await toggle_product_listing(payload, product_data)


@Products_Router.get("/{product_id}", status_code=status.HTTP_200_OK)
async def get_product_endpoint(product_id: str):
    return await get_product(product_id)


@Products_Router.get(
    "/all",
    status_code=status.HTTP_200_OK,
)
async def get_all_products_endpoint():
    """
    Retrieve listed products within a specified range provided as a URL parameter.
    Example: /products/range/1-10
    """
    return await get_all_products()


@Products_Router.post("/search", status_code=status.HTTP_200_OK)
async def search_products_endpoint(search_data: SearchProductsSchema):
    """🔹 Searches for products (Only listed ones)."""
    return await product_search_engine.search_products(
        search_data.query, search_data.limit
    )


@Products_Router.post("/admin/search-delisted", status_code=status.HTTP_200_OK)
async def search_delisted_products_endpoint(
    search_data: SearchProductsSchema, payload: dict = Depends(verify_jwt)
):
    """🔹 Searches delisted products (Admin Only)."""
    return await delisted_product_search_engine.search_products(
        payload, search_data.query, search_data.limit
    )


@Products_Router.get(
    "/admin/get-delisted/{limit}", status_code=status.HTTP_200_OK
)
async def get_delisted_products_endpoint(
    limit: str,
    payload: dict = Depends(verify_jwt),
):
    """🔹 Fetches all delisted products (Admin Only) with pagination support."""
    return await delisted_product_search_engine.search_products(
        payload, limit=limit
    )


@Products_Router.patch("/admin/upload-images/{product_id}", status_code=status.HTTP_200_OK)
async def upload_product_images_endpoint(
    product_id: str,
    files: List[UploadFile] = File(...),
    payload: dict = Depends(verify_jwt),
):
    """🔹 Uploads images for a product (PATCH: replaces existing images if folder exists)."""
    return await upload_product_images(product_id, payload, files)


@Products_Router.delete("/admin/remove-images/{product_id}", status_code=status.HTTP_200_OK)
async def remove_product_images_endpoint(
    product_id: str, payload: dict = Depends(verify_jwt)
):
    """🔹 Removes all images for a product."""
    return await remove_product_images(product_id, payload)
