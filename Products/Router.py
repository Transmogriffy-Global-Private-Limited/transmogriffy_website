from fastapi import (
    APIRouter,
    Depends,
    Header,
    status,
    File,
    Query,
    UploadFile,
)
from Utility_Methods.Utility_Methods import verify_jwt, ParsetoJSONObject
from Products.Methods import (
    add_product,
    update_product,
    toggle_product_listing,
    get_product,
    get_all_products,
)
from Products.Methods import ProductSearchEngine, DelistedProductSearchEngine
from Products.Data_Schemas import (
    AddProductSchema,
    UpdateProductSchema,
    ToggleProductListingSchema,
    SearchProductsSchema,
)
from typing import List

Products_Router = APIRouter()

# ✅ Search Engine Instances
product_search_engine = ProductSearchEngine()
delisted_product_search_engine = DelistedProductSearchEngine()


@Products_Router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_product_endpoint(
    product_data_form: ParsetoJSONObject = Depends(),
    files: List[UploadFile] = File(None),
    payload: dict = Depends(verify_jwt),
):
    # ✅ Parse and validate product data with nested details
    product_data = product_data_form.as_model(AddProductSchema)
    return await add_product(payload, product_data, files)


@Products_Router.put("/update", status_code=status.HTTP_200_OK)
async def update_product_endpoint(
    product_data_form: ParsetoJSONObject = Depends(),  # product_data as JSON string in form-data
    files: List[UploadFile] = File(None),  # Optional images to add
    payload: dict = Depends(verify_jwt),
):
    # ✅ Parse the entire product_data (including removed_images)
    product_data = product_data_form.as_model(UpdateProductSchema)

    # ✅ Pass everything to business logic
    return await update_product(payload, product_data, files)


@Products_Router.put("/toggle-listing", status_code=status.HTTP_200_OK)
async def toggle_product_listing_endpoint(
    product_data: ToggleProductListingSchema,
    payload: dict = Depends(verify_jwt),
):
    """🔹 Toggles a product's listing status (Admin Only)."""
    return await toggle_product_listing(payload, product_data)


@Products_Router.get("/get_by_id/{product_id}", status_code=status.HTTP_200_OK)
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
