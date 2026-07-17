# src/presentation/api/schemas/server.py
# Why: Defines request and response schemas for the Server resource.
# Separates raw database models and domain entities from external representation.
# Implements validation, examples, and descriptions using Pydantic v2.

from datetime import datetime
from pydantic import BaseModel, Field

class RegisterServerRequest(BaseModel):
    hostname: str = Field(
        ...,
        description="Unique hostname of the server (e.g., prod-db-01.local)",
        min_length=1,
        max_length=253,
        json_schema_extra={"example": "prod-db-01.local"}
    )
    ip_address: str = Field(
        ...,
        description="Unique IPv4 or IPv6 address of the server",
        min_length=1,
        json_schema_extra={"example": "192.168.1.50"}
    )
    operating_system: str = Field(
        ...,
        description="Operating system type/version",
        json_schema_extra={"example": "Ubuntu 22.04 LTS"}
    )
    cpu_cores: int = Field(
        ...,
        description="Number of CPU cores available",
        gt=0,
        json_schema_extra={"example": 8}
    )
    memory_gb: float = Field(
        ...,
        description="Total system memory in Gigabytes",
        gt=0.0,
        json_schema_extra={"example": 16.0}
    )


class ServerResponse(BaseModel):
    id: int = Field(..., description="Database generated unique identifier", json_schema_extra={"example": 1})
    hostname: str = Field(..., description="Unique hostname of the server", json_schema_extra={"example": "prod-db-01.local"})
    ip_address: str = Field(..., description="Unique IP address of the server", json_schema_extra={"example": "192.168.1.50"})
    operating_system: str = Field(..., description="Operating system type/version", json_schema_extra={"example": "Ubuntu 22.04 LTS"})
    cpu_cores: int = Field(..., description="Number of CPU cores", json_schema_extra={"example": 8})
    memory_gb: float = Field(..., description="Total system memory in Gigabytes", json_schema_extra={"example": 16.0})
    created_at: datetime = Field(..., description="Server registration timestamp")
    updated_at: datetime = Field(..., description="Last updated timestamp")

    model_config = {
        "from_attributes": True  # In Pydantic v2, this replaces orm_mode=True
    }
