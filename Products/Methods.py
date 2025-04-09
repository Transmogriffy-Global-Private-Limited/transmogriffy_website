import uuid
from fastapi import HTTPException, status, File, UploadFile
from tortoise.exceptions import DoesNotExist
import base64
from Database_and_ORM.Database_Models import (
    Product,
    Admin,
)
from Products.Data_Schemas import (
    AddProductSchema,
    UpdateProductSchema,
    ToggleProductListingSchema,
)
import re
import numpy as np
from collections import defaultdict
from vptree import VPTree
from typing import List, Optional
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


async def add_product(
    payload: dict,
    product_data: AddProductSchema,
    files: List[UploadFile] = None,
) -> dict:
    """Creates a new product with optional images (Admin only)."""
    await verify_admin(payload)

    product_id = str(uuid.uuid4())
    image_data_list = []
    image_names = []

    if files:
        for file in files:
            content = await file.read()

            # Detect MIME
            mime_type = file.content_type or "image/png"
            base64_data = base64.b64encode(content).decode("utf-8")
            full_data_uri = f"data:{mime_type};base64,{base64_data}"

            image_data_list.append(
                {"filename": file.filename, "data": full_data_uri}
            )
            image_names.append(file.filename)

    product = await Product.create(
        id=product_id, **product_data.model_dump(), images=image_data_list
    )

    return product_data.model_dump() | {
        "id": product_id,
        "imagePath": image_names,  # Just return names, as requested
    }


def get_product_media_path(product_id: str) -> str:
    """Returns the full media path for a given product."""
    return os.path.join(config("PRODUCTS_MEDIA_PATH"), product_id)


def get_product_images(product_id: str) -> list:
    """Returns a list of image paths for a product, if any exist."""
    product_path = os.path.join(config("PRODUCTS_MEDIA_PATH"), str(product_id))
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
        image_paths = get_product_images(product_id)

        return {
            "id": str(product.id),
            "name": product.name,
            "model": product.model,
            "details": product.details,
            "is_listed": product.is_listed,
            "image_paths": product.images,
            "quantity": product.quantity,
            "price": product.price,
        }
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or is delisted",
        )


async def get_all_products():
    """
    Retrieves all listed products within a specified range.

    Returns:
        product.images: List of product data.
    """
    try:

        # Query products
        query = Product.filter(is_listed=True).order_by("quantity")
        products = await query

        if not products:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No products found.",
            )

        # Build response
        product_list = []
        for product in products:
            product_list.append(
                {
                    "id": str(product.id),
                    "name": product.name,
                    "model": product.model,
                    "details": product.details,
                    "is_listed": product.is_listed,
                    "image_paths": product.images,
                    "quantity": product.quantity,
                    "price": product.price,
                }
            )

        return product_list

    except HTTPException:
        raise  # Re-raise HTTP errors directly
    except Exception as e:
        # Optional: Log error `e`
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


async def update_product(
    payload: dict,
    product_data: UpdateProductSchema,
    files: Optional[List[UploadFile]] = None,  # Optional images to ADD
) -> dict:
    """Updates an existing product with optional image additions and deletions (Admin only)."""
    await verify_admin(payload)

    try:
        product = await Product.get(id=product_data.product_id)
        current_images = product.images or []

        # ------------------- IMAGE REMOVAL LOGIC -------------------
        removed_images = set(product_data.removed_images or [])
        updated_images = [
            img
            for img in current_images
            if img not in removed_images
        ]

        # ------------------- IMAGE ADDITION LOGIC -------------------
        if files:
            for file in files:
                content = await file.read()

                # Infer MIME
                mime_type = file.content_type or "image/png"
                base64_data = base64.b64encode(content).decode("utf-8")
                full_data_uri = f"data:{mime_type};base64,{base64_data}"

                updated_images.append(
                    {"filename": file.filename, "data": full_data_uri}
                )

        # ------------------- DYNAMIC FIELD UPDATE -------------------
        update_data = product_data.model_dump(
            exclude_unset=True, exclude={"product_id", "removed_images"}
        )
        update_data["images"] = updated_images

        await Product.filter(id=product_data.id).update(**update_data)

        return {
            "id": str(product.id),
            **update_data,
            "imagePath": [
                img for img in updated_images
            ],  # Maintain return contract
        }

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Product not found")


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
            "price": product.price,
            "message": f"Product listing {'enabled' if product.is_listed else 'disabled'} successfully",
        }
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
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
                "price": product.price,
                "image_paths": product.images,
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

            type_value = flat_details.get("type", "").lower()
            fast_charger_value = flat_details.get("fast_charger", "").lower()

            # Normalize fast_charger to boolean-like values
            if fast_charger_value in [
                "yes",
                "true",
                "1",
            ]:  # Flexible matching for 'yes', 'true', '1'
                if "dc" in type_value:
                    tokens.extend(["dc", "fast", "charger", "dc fast charger"])
                elif "ac" in type_value:
                    tokens.extend(["ac", "fast", "charger", "ac fast charger"])

            # Prioritize rated power (wattage)
            rated_power = 0
            for key, value in flat_details.items():
                if (
                    "power" in key
                    or "wattage" in key
                    or "rated_power" in key
                    or "rated_for" in key
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
        nearest_neighbors = self.vp_tree.get_nearest_neighbor(
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

            type_value = flat_details.get("type", "").lower()
            fast_charger_value = flat_details.get("fast_charger", "").lower()

            # Normalize fast_charger to boolean-like values
            if fast_charger_value in [
                "yes",
                "true",
                "1",
            ]:  # Flexible matching for 'yes', 'true', '1'
                if "dc" in type_value:
                    tokens.extend(["dc", "fast", "charger", "dc fast charger"])
                elif "ac" in type_value:
                    tokens.extend(["ac", "fast", "charger", "ac fast charger"])

            # Prioritize rated power (wattage)
            rated_power = 0
            for key, value in flat_details.items():
                if (
                    "power" in key
                    or "wattage" in key
                    or "rated_power" in key
                    or "rated_for" in key
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
        nearest_neighbors = self.vp_tree.get_nearest_neighbor(
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
                    or "rated_power" in key
                    or "rated_for" in key
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
