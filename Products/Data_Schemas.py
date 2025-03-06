from enum import Enum


class ProductStatusEnum(str, Enum):
    in_cart = "inCart"
    in_order = "inanOrder"
    available = "available"
