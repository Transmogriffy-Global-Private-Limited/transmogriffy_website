from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, UUID4, Field, field_validator


class ProductDetailsSchema(BaseModel):
    voltage: str = Field(..., description="Voltage rating (e.g., '230V')")
    phase: str = Field(..., description="Phase type (e.g., 'Single', 'Three')")
    current: str = Field(..., description="Current rating (e.g., '16A')")
    frequency: str = Field(..., description="Frequency (e.g., '50Hz')")
    rated_power: str = Field(..., description="Rated power (e.g., '250W')")
    fast_charger: str = Field(
        ..., description="Fast charger support ('yes' or 'no')"
    )
    protection: str = Field(
        ..., description="Protection type (e.g., 'Overload, Short Circuit')"
    )
    communication: str = Field(
        ..., description="Communication protocol (e.g., 'Modbus, CAN')"
    )
    minimum_operating_temperature: Optional[int] = Field(
        None, description="Minimum operating temperature (°C), nullable"
    )
    maximum_operating_temperature: int = Field(
        ..., description="Maximum operating temperature (°C)"
    )
    cooling: str = Field(
        ..., description="Cooling method (e.g., 'Air cooled')"
    )
    ingress_protection: str = Field(
        ..., description="Ingress protection rating (e.g., 'IP65')"
    )
    length: float = Field(..., description="Length in meters")
    breadth: float = Field(..., description="Breadth in meters")
    height: float = Field(..., description="Height in meters")
    weight_in_kgs: float = Field(..., description="Weight in kilograms")
    noise_level: str = Field(..., description="Noise level (e.g., '55dB')")
    effiiency_in_percentage: float = Field(
        ...,
        alias="efficiency_in_percentage",
        description="Efficiency in percentage (e.g., 95.5)",
    )
    additional_details: Optional[str] = None

    @field_validator("fast_charger")
    def validate_fast_charger(cls, v):
        v_lower = v.strip().lower()
        if v_lower not in ["yes", "no"]:
            raise ValueError("fast_charger must be 'yes' or 'no'")
        return v_lower

    @field_validator("effiiency_in_percentage")
    def validate_efficiency(cls, v):
        if not (0 <= v <= 100):
            raise ValueError(
                "efficiency_in_percentage must be between 0 and 100"
            )
        return v

    @field_validator("length", "breadth", "height", "weight_in_kgs")
    def validate_positive_floats(cls, v, field):
        if v <= 0:
            raise ValueError(f"{field.name} must be a positive value")
        return v

    @field_validator("maximum_operating_temperature")
    def validate_temperature(cls, v):
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
    product_id: str
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
