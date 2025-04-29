from base64 import standard_b64decode
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

    breadth: Optional[float] = Field(
        None, description="Breadth in meters"
    )

    weight_in_kgs: Optional[float] = Field(
        None, description="Weight in kilograms"
    )
    efficiency_in_percentage: Optional[float] = Field(
        None,
        alias="efficiency_in_percentage",
        description="Efficiency in percentage (e.g., 95.5)",
    )
    dimensions: Optional[str] = Field(
        None, description="Dimensions (e.g., 'W x D x H - 100x100x100mm')"
    )
    additional_details: Optional[str] = None
    gun_details: Optional[str] = Field(
        None, description="Gun details (e.g., 'Two gun or one gun')"
    )
    gun_type: Optional[str] = Field(
        None, description="Gun type (e.g., 'CCS2', 'CCS1')"
    )
    material: Optional[str] = Field(
        None, description="Material type (e.g., 'Aluminum','Plasic')"
    )
    ouput_voltage: Optional[str] = Field(
        None, description="Output voltage (e.g., '7.7 KW' or '30KW')"
    )
    display: Optional[str] = Field(
        None, description="Does it have a display? (e.g., 'Yes', 'No')"
    )
    push_button: Optional[str] = Field(
        None, description="Does it have a push button? (e.g., 'Yes', 'No')"
    )
    operatingtemps: Optional[str] = Field(
        None,description="Operating temperature range (e.g., '-10°C to 150°C')"
    )
    chargingoperation: Optional[str] = Field(
        None, description="Charging operation details (e.g., 'Charging operation details')"
    )
    safetyregulation: Optional[str] = Field(
        None, description="Safety regulation (e.g., 'IEC 61000-2-2')"
    )
    mountingtype: Optional[str] = Field(
        None, description="Mounting type (e.g., 'Fixed', 'Wall mounted')"
    )
    cable_length: Optional[str] = Field(
        None, description="Cable length (e.g., '10m', '20m')"
    )
    

    @field_validator("fast_charger")
    def validate_fast_charger(cls, v):
        if v is None:
            return v
        v_lower = v.strip().lower()
        if v_lower not in ["yes", "no"]:
            raise ValueError("fast_charger must be 'yes' or 'no'")
        return v_lower



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
