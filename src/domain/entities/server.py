# src/domain/entities/server.py
# Why: This file defines the Server domain entity, representing a physical
# or virtual server in our architecture. It encapsulates the core data
# properties and factory methods, decoupling business logic from any database model.

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Server(BaseModel):
    """Domain entity representing a physical or virtual server instance."""

    id: Optional[int] = None
    hostname: str = Field(..., description="Unique hostname of the server")
    ip_address: str = Field(..., description="Unique IP address of the server")
    operating_system: str = Field(..., description="Operating system type/version")
    cpu_cores: int = Field(..., description="Number of CPU cores")
    memory_gb: float = Field(..., description="Total system memory in Gigabytes")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        hostname: str,
        ip_address: str,
        operating_system: str,
        cpu_cores: int,
        memory_gb: float,
    ) -> "Server":
        """Factory method to create a new Server entity."""
        return cls(
            hostname=hostname,
            ip_address=ip_address,
            operating_system=operating_system,
            cpu_cores=cpu_cores,
            memory_gb=memory_gb,
        )
