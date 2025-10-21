"""
Base models and configurations for workflow system.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field
from uuid import UUID, uuid4


class BaseModel(PydanticBaseModel):
    """Base model with common fields and methods."""
    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When the record was created"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When the record was last updated"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        json_encoders={
            UUID: str,
            datetime: lambda dt: dt.isoformat()
        },
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z"
            }
        }
    )
    
    def model_dump_with_metadata(self, **kwargs) -> Dict[str, Any]:
        """Dump model with additional metadata."""
        data = self.model_dump(**kwargs)
        data["__metadata__"] = {
            "model": self.__class__.__name__,
            "version": "1.0"
        }
        return data
