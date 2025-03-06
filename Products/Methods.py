import uuid
from fastapi import HTTPException, status, File, UploadFile
from tortoise.exceptions import DoesNotExist, IntegrityError
from Database_and_ORM.Database_Models import (
    Product,
    ProductInstance,
    Admin,
    ProductStatusEnum,
)
from Products.Data_Schemas import (
    AddProductSchema,
    UpdateProductSchema,
    ToggleProductListingSchema,
    CreateBulkUnitsSchema,
    UpdateProductUnitSchema,
)
import re
import numpy as np
from collections import defaultdict
from vptree import VPTree
from typing import List
import os
import shutil
from decouple import config


async def verify_admin(payload: dict):
    """Ensures that only admins can perform the operation."""
    admin_id = payload.get("user_id")
    admin = await Admin.get_or_none(id=admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Only admins can perform this action.",
        )
    return admin


async def add_product(payload: dict, product_data: AddProductSchema) -> dict:
    """Creates a new product (Admin only)."""
    await verify_admin(payload)
    product = await Product.create(
        id=uuid.uuid4(), **product_data.model_dump()
    )
    return product_data.model_dump() | {"id": str(product.id)}


def get_product_media_path(product_id: str) -> str:
    """Returns the full media path for a given product."""
    return os.path.join(config("PRODUCTS_MEDIA_PATH"), product_id)


async def upload_product_images(
    product_id: str,
    payload: dict,
    files: List[UploadFile] = File(...),
):
    """🔹 Uploads multiple images for a product (PATCH: replaces existing images if folder exists)."""
    await verify_admin(payload)  # ✅ Ensure only admins can upload

    # ✅ Check if product exists
    product = await Product.get_or_none(id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # ✅ Compute product media directory
    product_path = get_product_media_path(product_id)

    # ✅ If folder exists and is not empty, delete existing files
    if (
        os.path.exists(product_path)
        and os.path.isdir(product_path)
        and os.listdir(product_path)
    ):
        shutil.rmtree(
            product_path
        )  # Delete old images before uploading new ones

    # ✅ Ensure new directory exists
    os.makedirs(product_path, exist_ok=True)

    saved_files = []
    for file in files:
        # ✅ Enforce file size limit
        if file.size > config("MAXIMUM_FILE_SIZE"):
            raise HTTPException(
                status_code=413,
                detail=f"File {file.filename} exceeds size limit ({config("MAXIMUM_FILE_SIZE")} bytes)",
            )

        # ✅ Save new file
        file_path = os.path.join(product_path, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        saved_files.append(file.filename)

    return {"message": "Images uploaded successfully", "files": saved_files}


async def remove_product_images(product_id: str, payload: dict):
    """🔹 Removes all images for a product (Deletes the product's folder)."""
    await verify_admin(payload)  # ✅ Ensure only admins can delete

    # ✅ Ensure product exists
    product = await Product.get_or_none(id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # ✅ Compute folder path
    product_path = get_product_media_path(product_id)

    # ✅ Check if folder exists
    if os.path.exists(product_path) and os.path.isdir(product_path):
        shutil.rmtree(product_path)  # Deletes entire folder
        return {"message": "All product images deleted successfully"}

    raise HTTPException(
        status_code=404, detail="No images found for this product"
    )


def get_product_images(product_id: str) -> list:
    """Returns a list of image paths for a product, if any exist."""
    product_path = os.path.join(config("PRODUCTS_MEDIA_PATH"), product_id)
    if os.path.exists(product_path) and os.path.isdir(product_path):
        return [
            os.path.join(product_path, f)
            for f in os.listdir(product_path)
            if os.path.isfile(os.path.join(product_path, f))
        ]
    return []


async def get_product(product_id: uuid) -> dict:
    """Retrieves a product by its ID, includes the number of available units, and skips delisted products."""
    try:
        product = await Product.get(
            id=product_id, is_listed=True
        )  # Ensure only listed products are fetched
        available_count = await ProductInstance.filter(
            product_id=product_id, status=ProductStatusEnum.available
        ).count()
        image_paths = get_product_images(product_id)

        return {
            "id": str(product.id),
            "name": product.name,
            "model": product.model,
            "details": product.details,
            "available_units": available_count,  # Count of available product instances
            "is_listed": product.is_listed,
            "image_paths": image_paths,
        }
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or is delisted",
        )


async def update_product(
    payload: dict, product_data: UpdateProductSchema
) -> dict:
    """Updates an existing product (Admin only)."""
    await verify_admin(payload)
    try:
        product = await Product.get(id=product_data.product_id)
        update_data = product_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        await product.save()
        return update_data | {"id": str(product.id)}
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )


async def toggle_product_listing(
    payload: dict, product_data: ToggleProductListingSchema
) -> dict:
    """Toggles the listing status of a product (Admin only)."""
    await verify_admin(payload)
    try:
        product = await Product.get(id=product_data.product_id)
        product.is_listed = not product.is_listed
        await product.save()
        return {
            "id": str(product.id),
            "name": product.name,
            "model": product.model,
            "is_listed": product.is_listed,
            "message": f"Product listing {'enabled' if product.is_listed else 'disabled'} successfully",
        }
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )


async def create_bulk_units(
    payload: dict, unit_data: CreateBulkUnitsSchema
) -> dict:
    """Creates multiple product units in bulk (Admin only)."""
    await verify_admin(payload)
    try:
        product = await Product.get(id=unit_data.product_id, is_listed=True)
        units = [
            ProductInstance(
                id=uuid.uuid4(),
                product=product,
                serial_number=sn,
                status=ProductStatusEnum.available,
            )
            for sn in unit_data.serial_numbers
        ]
        await ProductInstance.bulk_create(units)
        return {
            "message": f"{len(unit_data.serial_numbers)} units created successfully"
        }
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or is delisted",
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate serial number detected",
        )


async def update_product_unit(
    payload: dict, unit_data: UpdateProductUnitSchema
) -> dict:
    """Updates the status of a specific product unit (Admin only)."""
    await verify_admin(payload)
    try:
        product_unit = await ProductInstance.get(id=unit_data.unit_id)
        product_unit.status = unit_data.status
        await product_unit.save()
        return {
            "id": str(product_unit.id),
            "product_id": str(product_unit.product_id),
            "status": product_unit.status.value,
        }
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product unit not found",
        )


async def get_delisted_products(payload: dict, limit: str) -> dict:
    """Retrieves delisted products with pagination, Admin only."""
    await verify_admin(payload)  # Ensure the user is an admin

    # Validate and extract the limit range
    match = re.match(r"^(\d+)-(\d+)$", limit)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid limit format. Use 'start-end'.",
        )

    start, end = map(int, match.groups())
    if start > end or start < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid limit range.",
        )

    # Fetch delisted products within range
    products = (
        await Product.filter(is_listed=False)
        .offset(start - 1)
        .limit(end - start + 1)
    )

    return {
        "products": [
            {
                "id": str(product.id),
                "name": product.name,
                "model": product.model,
                "details": product.details,
                "is_listed": product.is_listed,
                "image_paths": get_product_images(
                    str(product.id)
                ),  # ✅ Fetch image paths
            }
            for product in products
        ],
        "range": f"{start}-{end}",
    }


# Below contains methods to search products


class ProductSearchEngine:
    def __init__(self):
        self.vp_tree = None
        self.product_vectors = []
        self.product_data = {}
        self.hash_index = defaultdict(list)

    def flatten_json(self, json_obj):
        """Flattens deeply nested JSON into key-value pairs."""
        flat_dict = {}

        def recursive_flatten(obj, parent_key=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{parent_key}.{key}" if parent_key else key
                    recursive_flatten(value, new_key)
            elif isinstance(obj, list):
                for index, value in enumerate(obj):
                    new_key = f"{parent_key}[{index}]"
                    recursive_flatten(value, new_key)
            else:
                flat_dict[parent_key] = str(obj).lower()

        recursive_flatten(json_obj)
        return flat_dict

    def tokenize(self, value):
        """Splits values into searchable tokens."""
        return re.split(r"[\s.,-_]+", value.lower())

    async def index_products(self):
        """Indexes all products from the database."""
        self.product_vectors = []
        self.product_data = {}
        self.hash_index = defaultdict(list)

        products = await Product.filter(is_listed=True)
        for product in products:
            product_id = str(product.id)
            flat_details = self.flatten_json(product.details)

            # Extract searchable terms
            tokens = self.tokenize(product.name) + self.tokenize(product.model)

            # Prioritize rated power (wattage)
            rated_power = 0
            for key, value in flat_details.items():
                if (
                    "power" in key
                    or "wattage" in key
                    or "rated_power"
                    or "rated_for"
                    or "rated" in key
                ):
                    rated_power = (
                        int(re.search(r"\d+", value).group())
                        if re.search(r"\d+", value)
                        else 0
                    )
                    tokens.append(value)

            # Convert tokens into a vector
            vector = np.array([len(tokens), rated_power])
            self.product_vectors.append(vector)
            self.product_data[product_id] = (
                product.name,
                product.model,
                rated_power,
                flat_details,
            )

            # Hash indexing for exact lookups
            self.hash_index[product.model].append(product_id)
            self.hash_index[str(rated_power)].append(product_id)

        # Build the VP-Tree for nearest neighbor search
        self.vp_tree = VPTree(
            self.product_vectors, lambda x, y: np.linalg.norm(x - y)
        )

    async def search_products(self, query: str, limit: str):
        """Performs a fully optimized product search and returns sorted product IDs."""
        if not self.vp_tree:
            await self.index_products()

        # Validate limit range
        match = re.match(r"^(\d+)-(\d+)$", limit)
        if not match:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid limit format. Use 'start-end'.",
            )
        start, end = map(int, match.groups())
        if start > end or start < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid limit range.",
            )

        query_tokens = self.tokenize(query)
        query_vector = np.array([len(query_tokens), 0])

        # Step 1: VP-Tree Nearest Neighbor Search (Uncapped)
        nearest_neighbors = self.vp_tree.get_nearest_neighbors(
            query_vector, 1000
        )  # Large limit to get all matches

        # Step 2: Rank results based on weighted scoring
        scores = defaultdict(int)

        for product_id, distance in nearest_neighbors:
            name, model, rated_power, flat_details = self.product_data[
                product_id
            ]

            for token in query_tokens:
                if token in name:
                    scores[product_id] += 10
                if token in model:
                    scores[product_id] += 8
                if token in str(rated_power):
                    scores[product_id] += 6
                if any(token in v for v in flat_details.values()):
                    scores[product_id] += 4

        # Step 3: Sort by score (Descending)
        sorted_results = sorted(scores.items(), key=lambda x: -x[1])

        # Step 4: Apply final limit range
        final_results = [res[0] for res in sorted_results[start - 1 : end]]

        return final_results


class DelistedProductSearchEngine:
    def __init__(self):
        self.vp_tree = None
        self.product_vectors = []
        self.product_data = {}
        self.hash_index = defaultdict(list)

    def flatten_json(self, json_obj):
        """Flattens deeply nested JSON into key-value pairs."""
        flat_dict = {}

        def recursive_flatten(obj, parent_key=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{parent_key}.{key}" if parent_key else key
                    recursive_flatten(value, new_key)
            elif isinstance(obj, list):
                for index, value in enumerate(obj):
                    new_key = f"{parent_key}[{index}]"
                    recursive_flatten(value, new_key)
            else:
                flat_dict[parent_key] = str(obj).lower()

        recursive_flatten(json_obj)
        return flat_dict

    def tokenize(self, value):
        """Splits values into searchable tokens."""
        return re.split(r"[\s.,-_]+", value.lower())

    async def index_products(self):
        """Indexes only delisted products from the database (Admin Only)."""
        self.product_vectors = []
        self.product_data = {}
        self.hash_index = defaultdict(list)

        # ✅ Fetch only delisted products (is_listed=False)
        products = await Product.filter(is_listed=False)

        for product in products:
            product_id = str(product.id)
            flat_details = self.flatten_json(product.details)

            # Extract searchable terms
            tokens = self.tokenize(product.name) + self.tokenize(product.model)

            # Prioritize rated power (wattage)
            rated_power = 0
            for key, value in flat_details.items():
                if (
                    "power" in key
                    or "wattage" in key
                    or "rated_power"
                    or "rated_for"
                    or "rated" in key
                ):
                    rated_power = (
                        int(re.search(r"\d+", value).group())
                        if re.search(r"\d+", value)
                        else 0
                    )
                    tokens.append(value)

            # Convert tokens into a vector
            vector = np.array([len(tokens), rated_power])
            self.product_vectors.append(vector)
            self.product_data[product_id] = (
                product  # Store full product object
            )

            # Hash indexing for exact lookups
            self.hash_index[product.model].append(product_id)
            self.hash_index[str(rated_power)].append(product_id)

        # Build the VP-Tree for nearest neighbor search
        self.vp_tree = VPTree(
            self.product_vectors, lambda x, y: np.linalg.norm(x - y)
        )

    async def search_products(self, payload: dict, query: str, limit: str):
        """Performs a fully optimized product search for delisted products (Admin Only)."""
        await verify_admin(payload)  # ✅ Ensure only admins can access this

        if not self.vp_tree:
            await self.index_products()

        # Validate limit range
        match = re.match(r"^(\d+)-(\d+)$", limit)
        if not match:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid limit format. Use 'start-end'.",
            )
        start, end = map(int, match.groups())
        if start > end or start < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid limit range.",
            )

        query_tokens = self.tokenize(query)
        query_vector = np.array([len(query_tokens), 0])

        # Step 1: VP-Tree Nearest Neighbor Search (Uncapped)
        nearest_neighbors = self.vp_tree.get_nearest_neighbors(
            query_vector, 1000
        )  # Large limit to get all matches

        # Step 2: Rank results based on weighted scoring
        scores = defaultdict(int)

        for product_id, distance in nearest_neighbors:
            product = self.product_data[product_id]
            name, model, rated_power, flat_details = (
                product.name,
                product.model,
                0,
                self.flatten_json(product.details),
            )

            # Extract rated power from flattened details
            for key, value in flat_details.items():
                if (
                    "power" in key
                    or "wattage" in key
                    or "rated_power"
                    or "rated_for"
                    or "rated" in key
                ):
                    rated_power = (
                        int(re.search(r"\d+", value).group())
                        if re.search(r"\d+", value)
                        else 0
                    )

            for token in query_tokens:
                if token in name:
                    scores[product_id] += 10
                if token in model:
                    scores[product_id] += 8
                if token in str(rated_power):
                    scores[product_id] += 6
                if any(token in v for v in flat_details.values()):
                    scores[product_id] += 4

        # Step 3: Sort by score (Descending)
        sorted_results = sorted(scores.items(), key=lambda x: -x[1])

        # Step 4: Apply final limit range
        final_results = [
            self.product_data[res[0]]
            for res in sorted_results[start - 1 : end]
        ]

        return final_results
