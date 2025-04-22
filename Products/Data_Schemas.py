from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, UUID4, Field, field_validator

class ProductDetailsSchema(BaseModel):
    voltage: Optional[str] = Field(
        None, description="Voltage rating (e.g., '230V')"
    )
    phase: Optional[str] = Field(
        None, description="Phase type (e.g., 'Single', 'Three')"
    )
    current: Optional[str] = Field(
        None, description="Current rating (e.g., '16A')"
    )
    frequency: Optional[str] = Field(
        None, description="Frequency (e.g., '50Hz')"
    )
    rated_power: Optional[str] = Field(
        None, description="Rated power (e.g., '250W')"
    )
    fast_charger: Optional[str] = Field(
        None, description="Fast charger support ('yes' or 'no')"
    )
    protection: Optional[str] = Field(
        None, description="Protection type (e.g., 'Overload, Short Circuit')"
    )
    communication: Optional[str] = Field(
        None, description="Communication protocol (e.g., 'Modbus, CAN')"
    )
    minimum_operating_temperature: Optional[int] = Field(
        None, description="Minimum operating temperature (°C), nullable"
    )
    maximum_operating_temperature: Optional[int] = Field(
        None, description="Maximum operating temperature (°C)"
    )
    cooling: Optional[str] = Field(
        None, description="Cooling method (e.g., 'Air cooled')"
    )
    ingress_protection: Optional[str] = Field(
        None, description="Ingress protection rating (e.g., 'IP65')"
    )
    length: Optional[float] = Field(
        None, description="Length in meters"
    )
    breadth: Optional[float] = Field(
        None, description="Breadth in meters"
    )
    height: Optional[float] = Field(
        None, description="Height in meters"
    )
    weight_in_kgs: Optional[float] = Field(
        None, description="Weight in kilograms"
    )
    noise_level: Optional[str] = Field(
        None, description="Noise level (e.g., '55dB')"
    )
    efficiency_in_percentage: Optional[float] = Field(
        None,
        alias="efficiency_in_percentage",
        description="Efficiency in percentage (e.g., 95.5)",
    )
    additional_details: Optional[str] = None

    @field_validator("fast_charger")
    def validate_fast_charger(cls, v):
        if v is None:
            return v
        v_lower = v.strip().lower()
        if v_lower not in ["yes", "no"]:
            raise ValueError("fast_charger must be 'yes' or 'no'")
        return v_lower

    @field_validator("efficiency_in_percentage")
    def validate_efficiency(cls, v):
        if v is None:
            return v
        if not (0 <= v <= 100):
            raise ValueError(
                "efficiency_in_percentage must be between 0 and 100"
            )
        return v

    @field_validator("length", "breadth", "height", "weight_in_kgs")
    def validate_positive_floats(cls, v, field):
        if v is None:
            return v
        if v <= 0:
            raise ValueError(f"{field.name} must be a positive value")
        return v

    @field_validator("maximum_operating_temperature")
    def validate_temperature(cls, v):
        if v is None:
            return v
        if v < -100 or v > 200:
            raise ValueError(
                "maximum_operating_temperature must be in a reasonable range (-100 to 200 °C)"
            )
        return v


class AddProductSchema(BaseModel):
    name: str
    model: str
    details: ProductDetailsSchema
    quantity: Optional[int] = None
    price: float


class UpdateProductSchema(BaseModel):
    id: str
    name: Optional[str] = None
    model: Optional[str] = None
    details: Optional[ProductDetailsSchema] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    removed_images: Optional[List[str]] = None


class ToggleProductListingSchema(BaseModel):
    product_id: UUID4


class GetDelistedProductsSchema(BaseModel):
    limit: str = Field(
        ...,
        pattern=r"^\d+-\d+$",
        description="Range of results in the format 'start-end'",
    )


class SearchProductsSchema(BaseModel):
    query: str
    limit: str


class ProductResponse(BaseModel):
    id: str
    name: str
    model: str
    details: dict
    is_listed: bool
    image_paths: List[str]
    quantity: int
    price: float
