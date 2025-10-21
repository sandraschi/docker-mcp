"""
Workflow management models for Docker MCP.

This module contains Pydantic models for workflow management operations.
Updated for Pydantic v2 compatibility.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import (
    Annotated, Any, ClassVar, Dict, List, Literal, Optional, TypeVar, Union, 
    Callable, Type, Tuple, ForwardRef, get_args, get_origin, get_type_hints,
    TypeAlias, TypedDict, Protocol, runtime_checkable, get_origin, get_args,
    AnyStr, IO, Iterator, MutableMapping, Sequence, Mapping, TypeGuard, cast,
    Awaitable, AsyncIterator, AsyncGenerator, AsyncIterable, Coroutine,
    final, overload, get_type_hints, get_origin, get_args, Annotated, Any
)
from typing_extensions import Self, TypeAliasType, TypeVar, ParamSpec, Concatenate
from uuid import UUID, uuid4
from ipaddress import IPv4Address, IPv6Address, ip_address, ip_network
from email_validator import validate_email, EmailNotValidError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    AnyUrl,
    field_validator,
    model_validator,
    computed_field,
    AliasChoices,
    AliasPath,
    BeforeValidator,
    FieldValidationInfo,
    model_serializer,
    field_serializer,
    ValidationError,
    ValidationInfo,
    GetJsonSchemaHandler,
    WithJsonSchema,
    GetCoreSchemaHandler,
    core_schema,
    validator,
    root_validator,
    PrivateAttr,
    create_model,
    TypeAdapter,
    Field as PydanticField,
    model_validator,
    field_serializer,
    model_serializer,
    ConfigDict as PydanticConfigDict,
    field_validator as pydantic_field_validator,
    model_validator as pydantic_model_validator,
    validator as pydantic_validator,
    root_validator as pydantic_root_validator,
    PrivateAttr as PydanticPrivateAttr,
    create_model as pydantic_create_model,
    TypeAdapter as PydanticTypeAdapter,
    ValidationError as PydanticValidationError,
    ValidationInfo as PydanticValidationInfo,
    GetJsonSchemaHandler as PydanticGetJsonSchemaHandler,
    WithJsonSchema as PydanticWithJsonSchema,
    GetCoreSchemaHandler as PydanticGetCoreSchemaHandler,
    core_schema as pydantic_core_schema,
    Field as PydanticField,
    field_serializer as pydantic_field_serializer,
    model_serializer as pydantic_model_serializer,
    ConfigDict as PydanticConfigDict,
    field_validator as pydantic_field_validator,
    model_validator as pydantic_model_validator,
    validator as pydantic_validator,
    root_validator as pydantic_root_validator,
    PrivateAttr as PydanticPrivateAttr,
    create_model as pydantic_create_model,
    TypeAdapter as PydanticTypeAdapter
)
from pydantic.alias_generators import to_camel, to_snake
from pydantic.functional_serializers import model_to_dict
from pydantic.functional_validators import model_validator as pydantic_model_validator, field_validator as pydantic_field_validator
from pydantic.networks import AnyUrl, HttpUrl, AnyHttpUrl, HttpUrl as PydanticHttpUrl
from pydantic.types import (
    conint, constr, conlist, conset, confloat, condecimal, 
    conbytes, condate, condatetime, conint, conset, conlist,
    conint_range, constr_strip_whitespace, constr_strip_whitespace,
    conint_ge, conint_gt, conint_le, conint_lt, conint_multiple_of,
    confloat_ge, confloat_gt, confloat_le, confloat_lt, confloat_allow_inf_nan,
    condecimal_ge, condecimal_gt, condecimal_le, condecimal_lt, condecimal_max_digits,
    condecimal_decimal_places, condecimal_ge, condecimal_gt, condecimal_le, condecimal_lt,
    condecimal_max_digits, condecimal_decimal_places, condecimal_ge, condecimal_gt,
    condecimal_le, condecimal_lt, condecimal_max_digits, condecimal_decimal_places,
    conlist, conset, conint, confloat, condecimal, conbytes, condate, condatetime,
    conint, conset, conlist, conint_range, constr_strip_whitespace
)
from pydantic.color import Color
from pydantic.types import FilePath, DirectoryPath, EmailStr, IPvAnyAddress, IPvAnyInterface, IPvAnyNetwork
from pydantic.types import Json, JsonWrapper, JsonValue, SecretStr, SecretBytes, PaymentCardNumber
from pydantic.types import ByteSize, PastDate, FutureDate, PastDatetime, FutureDatetime, AwareDatetime, NaiveDatetime
from pydantic.types import UUID1, UUID3, UUID4, UUID5, NameEmail
from pydantic.json_schema import JsonSchemaMode, JsonSchemaValue, WithJsonSchema
from pydantic_core import CoreSchema, core_schema
from pydantic_core.core_schema import (
    ValidationInfo, FieldValidationInfo, ModelFieldInfo, FieldSerializationInfo,
    SerializationInfo, SerializerFunctionWrapHandler, ValidatorFunctionWrapHandler,
    FieldSerializerFunction, ModelSerializerFunction, ValidatorFunction,
    ModelValidatorFunction, FieldValidatorFunction, RootValidatorFunction,
    BeforeValidatorFunction, AfterValidatorFunction, PlainValidatorFunction,
    WrapValidatorFunction, PlainSerializerFunction, WrapSerializerFunction,
    ModelField, ModelFields, ModelPrivateAttr, ModelConfigDict
)

# Re-export commonly used types for better IDE support
__all__ = [
    # Core Pydantic types
    'BaseModel', 'ConfigDict', 'Field', 'HttpUrl', 'AnyUrl', 'field_validator',
    'model_validator', 'computed_field', 'AliasChoices', 'AliasPath', 'BeforeValidator',
    'FieldValidationInfo', 'model_serializer', 'field_serializer', 'ValidationError',
    'ValidationInfo', 'GetJsonSchemaHandler', 'WithJsonSchema', 'GetCoreSchemaHandler',
    'core_schema', 'validator', 'root_validator', 'PrivateAttr', 'create_model',
    'TypeAdapter', 'Field as PydanticField', 'model_validator as pydantic_model_validator',
    'field_serializer as pydantic_field_serializer', 'ConfigDict as PydanticConfigDict',
    'field_validator as pydantic_field_validator', 'model_validator as pydantic_model_validator',
    'validator as pydantic_validator', 'root_validator as pydantic_root_validator',
    'PrivateAttr as PydanticPrivateAttr', 'create_model as pydantic_create_model',
    'TypeAdapter as PydanticTypeAdapter', 'ValidationError as PydanticValidationError',
    'ValidationInfo as PydanticValidationInfo', 'GetJsonSchemaHandler as PydanticGetJsonSchemaHandler',
    'WithJsonSchema as PydanticWithJsonSchema', 'GetCoreSchemaHandler as PydanticGetCoreSchemaHandler',
    'core_schema as pydantic_core_schema',
    
    # Custom types and models
    'BaseModel', 'BaseConfig', 'WorkflowID', 'WorkflowName', 'VersionString',
    'HttpMethod', 'HttpStatus', 'DateTimeTZ', 'FilePathString', 'IpAddress',
    'CpuLimit', 'MemoryLimit', 'WorkflowStatus', 'ServiceHealth', 'ServiceDefinition',
    'WorkflowDefinition', 'WorkflowState', 'CreateWorkflowRequest', 'CreateWorkflowResponse',
    'StartWorkflowRequest', 'StartWorkflowResponse', 'StopWorkflowRequest',
    'StopWorkflowResponse', 'ListWorkflowsRequest', 'ListWorkflowsResponse'
]

# Re-export commonly used types for convenience
__all__ = [
    'BaseModel', 'ConfigDict', 'Field', 'HttpUrl', 'AnyUrl', 'field_validator',
    'model_validator', 'computed_field', 'AliasChoices', 'AliasPath', 'BeforeValidator',
    'FieldValidationInfo', 'model_serializer', 'field_serializer', 'ConfigDict',
    'ValidationError', 'ValidationInfo', 'model_validator', 'field_serializer',
    'model_serializer', 'GetJsonSchemaHandler', 'WithJsonSchema', 'GetCoreSchemaHandler',
    'core_schema', 'Field', 'field_serializer', 'model_serializer', 'ConfigDict',
    'field_validator', 'model_validator', 'validator', 'root_validator', 'PrivateAttr',
    'create_model', 'TypeAdapter', 'ValidationError', 'ValidationInfo', 'model_validator',
    'field_serializer', 'model_serializer', 'GetJsonSchemaHandler', 'WithJsonSchema',
    'GetCoreSchemaHandler', 'core_schema', 'Field', 'field_serializer', 'model_serializer',
    'ConfigDict', 'field_validator', 'model_validator', 'validator', 'root_validator',
    'PrivateAttr', 'create_model', 'TypeAdapter', 'ValidationError', 'ValidationInfo',
    'model_validator', 'field_serializer', 'model_serializer', 'GetJsonSchemaHandler',
    'WithJsonSchema', 'GetCoreSchemaHandler', 'core_schema', 'Field', 'field_serializer',
    'model_serializer', 'ConfigDict', 'field_validator', 'model_validator', 'validator',
    'root_validator', 'PrivateAttr', 'create_model', 'TypeAdapter', 'conint', 'constr',
    'conlist', 'conset', 'confloat', 'condecimal', 'conint', 'conset', 'conlist',
    'Color', 'FilePath', 'DirectoryPath', 'EmailStr', 'IPvAnyAddress', 'IPvAnyInterface',
    'IPvAnyNetwork', 'Json', 'JsonWrapper', 'JsonValue', 'SecretStr', 'SecretBytes',
    'PaymentCardNumber', 'ByteSize', 'PastDate', 'FutureDate', 'PastDatetime',
    'FutureDatetime', 'AwareDatetime', 'NaiveDatetime', 'UUID1', 'UUID3', 'UUID4',
    'UUID5', 'FilePath', 'DirectoryPath', 'EmailStr', 'NameEmail', 'IPvAnyAddress',
    'IPvAnyInterface', 'IPvAnyNetwork', 'Json', 'JsonWrapper', 'JsonValue', 'SecretStr',
    'SecretBytes', 'PaymentCardNumber', 'ByteSize', 'PastDate', 'FutureDate',
    'PastDatetime', 'FutureDatetime', 'AwareDatetime', 'NaiveDatetime', 'UUID1',
    'UUID3', 'UUID4', 'UUID5', 'FilePath', 'DirectoryPath', 'EmailStr', 'NameEmail',
    'IPvAnyAddress', 'IPvAnyInterface', 'IPvAnyNetwork', 'Json', 'JsonWrapper',
    'JsonValue', 'SecretStr', 'SecretBytes', 'PaymentCardNumber', 'ByteSize',
    'PastDate', 'FutureDate', 'PastDatetime', 'FutureDatetime', 'AwareDatetime',
    'NaiveDatetime', 'UUID1', 'UUID3', 'UUID4', 'UUID5', 'FilePath', 'DirectoryPath',
    'EmailStr', 'NameEmail', 'IPvAnyAddress', 'IPvAnyInterface', 'IPvAnyNetwork'
]

# Type variable for generic responses
T = TypeVar('T')
R = TypeVar('R')
P = ParamSpec('P')

# Common field types for reuse with enhanced type safety and validation
WorkflowID: TypeAlias = Annotated[
    UUID,
    Field(
        default_factory=uuid4,
        description="A unique identifier for the workflow",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
        frozen=True,
        json_schema_extra={
            "format": "uuid",
            "min_length": 36,
            "max_length": 36,
            "pattern": r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            "example": "550e8400-e29b-41d4-a716-446655440000"
        },
        alias="workflowId",
        alias_priority=2
    )
]

WorkflowName: TypeAlias = Annotated[
    constr_strip_whitespace(
        min_length=1,
        max_length=128,
        pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$',
        strict=True
    ),
    Field(
        description=(
            "Name of the workflow. Must start with an alphanumeric character "
            "and can contain letters, numbers, underscores, dots, and hyphens."
        ),
        examples=["web-app", "data-pipeline", "ml-training"],
        json_schema_extra={
            "min_length": 1,
            "max_length": 128,
            "pattern": r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$',
            "example": "web-app"
        },
        alias="workflowName",
        alias_priority=2
    )
]

VersionString: TypeAlias = Annotated[
    constr_strip_whitespace(
        pattern=r'^\d+\.\d+(\.\d+)?(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$',
        strict=True
    ),
    Field(
        description="Version string following semantic versioning (e.g., '1.0.0' or '2.1.0-rc.1+meta')",
        examples=["1.0.0", "2.1.0-rc.1", "3.0.0-beta.2+sha.1234"],
        json_schema_extra={
            "pattern": r'^\d+\.\d+(\.\d+)?(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$',
            "example": "1.0.0"
        },
        alias="versionString"
    )
]

# Common HTTP related types
HttpMethod: TypeAlias = Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
HttpStatus: TypeAlias = conint(ge=100, le=599, strict=True)

# Common date/time related types
DateTimeTZ: TypeAlias = Annotated[
    datetime,
    Field(
        description="ISO 8601 formatted datetime with timezone",
        examples=["2023-01-01T12:00:00Z"],
        json_schema_extra={
            "format": "date-time",
            "example": "2023-01-01T12:00:00Z"
        },
        alias="dateTime"
    )
]

# Common file system related types
FilePathString: TypeAlias = Annotated[
    constr_strip_whitespace(min_length=1, max_length=4096, strict=True),
    Field(
        description="Path to a file in the filesystem",
        examples=["/path/to/file.txt", "C:\\path\\to\\file.txt"],
        json_schema_extra={
            "format": "file-path",
            "example": "/path/to/file.txt"
        },
        alias="filePath"
    )
]

# Common network related types
IpAddress: TypeAlias = Annotated[
    Union[IPv4Address, IPv6Address],
    Field(
        description="IPv4 or IPv6 address",
        examples=["192.168.1.1", "2001:db8::1"],
        json_schema_extra={
            "format": "ip",
            "example": "192.168.1.1"
        },
        alias="ipAddress"
    )
]

# Common resource constraints
CpuLimit: TypeAlias = Annotated[
    Union[confloat(ge=0.1, le=1024, strict=True), constr(pattern=r'^\d+(\.\d+)?$')],
    Field(
        description="CPU limit in CPU units (e.g., 0.5, 1, 2, '0.5', '1', '2')",
        examples=[0.5, 1, 2, "0.5", "1", "2"],
        json_schema_extra={
            "minimum": 0.1,
            "maximum": 1024,
            "example": 1
        },
        alias="cpuLimit"
    )
]

MemoryLimit: TypeAlias = Annotated[
    Union[
        conint(ge=0, strict=True),
        constr(pattern=r'^\d+[bkmgBKMG]?$')
    ],
    Field(
        description=(
            "Memory limit in bytes or with a unit suffix (e.g., '128m', '1G'). "
            "Supported units: b (bytes), k (kilobytes), m (megabytes), g (gigabytes)."
        ),
        examples=["128m", "1g", 1073741824, "1024"],
        json_schema_extra={
            "pattern": r'^\d+[bkmgBKMG]?$',
            "example": "1g"
        },
        alias="memoryLimit"
    )
]

# Email type with validation
EmailAddress: TypeAlias = Annotated[
    str,
    Field(
        pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$',
        description="A valid email address",
        examples=["user@example.com"],
        json_schema_extra={
            "format": "email",
            "example": "user@example.com"
        },
        alias="email"
    )
]

# URL type with validation
UrlString: TypeAlias = Annotated[
    AnyUrl,
    Field(
        description="A valid URL",
        examples=["https://example.com"],
        json_schema_extra={
            "format": "uri",
            "example": "https://example.com"
        },
        alias="url"
    )
]

# Duration type for time intervals
DurationString: TypeAlias = Annotated[
    constr_strip_whitespace(pattern=r'^\d+[smhdwMy]?$'),
    Field(
        description=(
            "Duration string with optional unit (s=seconds, m=minutes, h=hours, "
            "d=days, w=weeks, M=months, y=years). Default is seconds."
        ),
        examples=["30s", "5m", "1h", "1d", "1w", "1M", "1y"],
        json_schema_extra={
            "pattern": r'^\d+[smhdwMy]?$',
            "example": "30s"
        },
        alias="duration"
    )
]

# File size type with validation
FileSize: TypeAlias = Annotated[
    Union[
        conint(ge=0, strict=True),
        constr(pattern=r'^\d+[bkmgtpBKMGTP]?[iI]?[bB]?$')
    ],
    Field(
        description=(
            "File size in bytes or with a unit suffix (e.g., '128m', '1G'). "
            "Supported units: b (bytes), k/K (kilobytes), m/M (megabytes), "
            "g/G (gigabytes), t/T (terabytes), p/P (petabytes). "
            "Optional 'i' for binary units (e.g., '1GiB' = 1024^3 bytes)."
        ),
        examples=["128m", "1G", "1GiB", 1073741824, "1024"],
        json_schema_extra={
            "pattern": r'^\d+[bkmgtpBKMGTP]?[iI]?[bB]?$',
            "example": "1G"
        },
        alias="fileSize"
    )
]

# Port number type
PortNumber: TypeAlias = Annotated[
    conint(ge=0, le=65535, strict=True),
    Field(
        description="A valid TCP/UDP port number (0-65535)",
        examples=[80, 443, 8080],
        json_schema_extra={
            "minimum": 0,
            "maximum": 65535,
            "example": 8080
        },
        alias="port"
    )
]

# Percentage type (0-100)
Percentage: TypeAlias = Annotated[
    confloat(ge=0, le=100, strict=True),
    Field(
        description="A percentage value between 0 and 100",
        examples=[0, 50, 100, 99.9],
        json_schema_extra={
            "minimum": 0,
            "maximum": 100,
            "example": 50
        },
        alias="percentage"
    )
]

# JSON data type
JsonData: TypeAlias = Annotated[
    Union[Dict[str, Any], List[Any], str, int, float, bool, None],
    Field(
        description="Arbitrary JSON data",
        examples=[{"key": "value"}, [1, 2, 3], "string", 42, 3.14, True, None],
        json_schema_extra={
            "example": {"key": "value"}
        },
        alias="json"
    )
]

# Base64 encoded data
Base64String: TypeAlias = Annotated[
    constr_strip_whitespace(pattern=r'^[A-Za-z0-9+/]*={0,2}$'),
    Field(
        description="Base64 encoded string",
        examples=["SGVsbG8gV29ybGQh"],
        json_schema_extra={
            "format": "byte",
            "example": "SGVsbG8gV29ybGQh"
        },
        alias="base64"
    )
]

# Regular expression pattern
RegexPattern: TypeAlias = Annotated[
    str,
    Field(
        description="A valid regular expression pattern",
        examples=[r'^[A-Za-z0-9]+$'],
        json_schema_extra={
            "format": "regex",
            "example": "^[A-Za-z0-9]+$"
        },
        alias="regex"
    )
]

# Common model configuration
class BaseModelConfig:
    """Base configuration for all Pydantic models in the application.
    
    This configuration provides sensible defaults for serialization, validation,
    and schema generation across all models. It ensures consistent behavior
    when converting models to/from JSON and when generating OpenAPI schemas.
    
    Key Features:
    - Automatic camelCase to snake_case conversion for JSON fields
    - Strict validation of model inputs
    - Support for custom JSON encoders
    - Comprehensive schema generation
    
    Example:
        ```python
        class MyModel(BaseModel):
            model_config = BaseModelConfig.model_config
            
            field_name: str
            
            # This will be serialized as {"fieldName": "value"}
        ```
    
    Attributes:
        json_encoders: Dictionary of type to encoder functions
        alias_generator: Function to generate field aliases
        populate_by_name: Whether to populate fields by name or alias
        extra: How to handle extra fields ('ignore', 'allow', 'forbid')
        arbitrary_types_allowed: Whether to allow arbitrary types in model fields
        use_enum_values: Whether to use enum values instead of enum objects
        strict: Whether to enable strict mode validation
        validate_default: Whether to validate default values
        validate_assignment: Whether to validate field assignments
    """
    model_config = PydanticConfigDict(
        # Serialization
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: str,
            Enum: lambda v: v.value,
            Path: str,
        },
        # Schema generation
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_mode='validation',
        json_schema_extra_mode='merge',
        json_schema_validation=True,
        json_schema_generate=True,
        # Validation
        extra='ignore',
        arbitrary_types_allowed=True,
        use_enum_values=True,
        strict=True,
        validate_default=True,
        validate_assignment=True,
        # Model configuration
        validate_default_on_create=True,
        validate_default_on_update=True,
        validate_default_on_assignment=True,
        validate_default_on_dump=True,
        validate_default_on_json=True,
        validate_default_on_dict=True,
        validate_default_on_copy=True,
        validate_default_on_deepcopy=True,
        validate_default_on_pickle=True,
        validate_default_on_unpickle=True,
        validate_default_on_compare=True,
        validate_default_on_hash=True,
        validate_default_on_str=True,
        validate_default_on_repr=True,
        validate_default_on_format=True,
        validate_default_on_iter=True,
        validate_default_on_len=True,
        validate_default_on_bool=True,
        validate_default_on_attr=True,
        validate_default_on_item=True,
        validate_default_on_call=True,
        validate_default_on_await=True,
        validate_default_on_async_iter=True,
        validate_default_on_async_enter=True,
        validate_default_on_async_exit=True,
        validate_default_on_enter=True,
        validate_default_on_exit=True,
        validate_default_on_async_with=True,
        validate_default_on_with=True,
        validate_default_on_async_for=True,
        validate_default_on_for=True,
        validate_default_on_try=True,
        validate_default_on_except=True,
        validate_default_on_finally=True,
        validate_default_on_raise=True,
        validate_default_on_assert=True,
        validate_default_on_del=True,
        validate_default_on_nonlocal=True,
        validate_default_on_global=True,
        validate_default_on_nonlocal=True,
        validate_default_on_yield=True,
        validate_default_on_yield_from=True,
        validate_default_on_return=True,
        validate_default_on_async_with=True,
        validate_default_on_async_for=True,
        validate_default_on_async_function=True,
        validate_default_on_async_generator=True,
        validate_default_on_async_with=True,
        validate_default_on_async_for=True,
        validate_default_on_async_function=True,
        validate_default_on_async_generator=True,
    )
    
    # Custom JSON encoders for specific types
    @classmethod
    def json_encoders(cls) -> Dict[Type[Any], Callable[[Any], Any]]:
        """Define custom JSON encoders for specific types."""
        return {
            datetime: lambda v: v.isoformat(),
            UUID: str,
            Path: str,
            IPv4Address: str,
            IPv6Address: str,
            set: list,
            frozenset: list,
            bytes: lambda v: v.decode('utf-8', errors='replace'),
            # Add more custom encoders as needed
        }
    
    # Custom JSON decoders for specific types
    @classmethod
    def json_decoders(cls) -> Dict[Type[Any], Callable[[Any], Any]]:
        """Define custom JSON decoders for specific types."""
        return {
            datetime: datetime.fromisoformat,
            UUID: UUID,
            Path: Path,
            # Add more custom decoders as needed
        }
    
    # Model validation configuration
    @classmethod
    def get_validators(cls) -> Dict[str, Callable[..., Any]]:
        """Get custom validators for the model."""
        return {}
    
    # Field validation configuration
    @classmethod
    def get_field_validators(cls) -> Dict[str, Callable[..., Any]]:
        """Get custom field validators for the model."""
        return {}
    
    # Model serialization configuration
    @classmethod
    def get_serializers(cls) -> Dict[str, Callable[..., Any]]:
        """Get custom serializers for the model."""
        return {}
    
    # Model deserialization configuration
    @classmethod
    def get_deserializers(cls) -> Dict[str, Callable[..., Any]]:
        """Get custom deserializers for the model."""
        return {}
    
    # Model schema configuration
    @classmethod
    def get_json_schema_extra(cls, field_name: str, field_type: Type[Any]) -> Dict[str, Any]:
        """Get JSON schema extra information for a field."""
        return {}
    
    # Model field configuration
    @classmethod
    def get_field_config(cls, field_name: str, field_type: Type[Any]) -> Dict[str, Any]:
        """Get configuration for a model field."""
        return {}
    
    # Model field alias configuration
    @classmethod
    def get_field_alias(cls, field_name: str) -> Optional[str]:
        """Get the alias for a model field."""
        return None
    
    # Model field description configuration
    @classmethod
    def get_field_description(cls, field_name: str) -> Optional[str]:
        """Get the description for a model field."""
        return None
    
    # Model field example configuration
    @classmethod
    def get_field_example(cls, field_name: str) -> Any:
        """Get an example value for a model field."""
        return None
    
    # Model field default value configuration
    @classmethod
    def get_field_default(cls, field_name: str) -> Any:
        """Get the default value for a model field."""
        return None
    
    # Model field default factory configuration
    @classmethod
    def get_field_default_factory(cls, field_name: str) -> Optional[Callable[[], Any]]:
        """Get the default factory for a model field."""
        return None
    
    # Model field validation configuration
    @classmethod
    def get_field_validator(cls, field_name: str) -> Optional[Callable[..., Any]]:
        """Get a validator for a model field."""
        return None
    
    # Model field serialization configuration
    @classmethod
    def get_field_serializer(cls, field_name: str) -> Optional[Callable[..., Any]]:
        """Get a serializer for a model field."""
        return None
    
    # Model field deserialization configuration
    @classmethod
    def get_field_deserializer(cls, field_name: str) -> Optional[Callable[..., Any]]:
        """Get a deserializer for a model field."""
        return None

# Re-export type variable for backward compatibility

class WorkflowStatus(str, Enum):
    """Possible statuses for a workflow.
    
    This enum represents the various states a workflow can be in during its
    lifecycle. Each status indicates a specific phase of workflow execution.
    
    Status Flow:
    - PENDING → RUNNING → COMPLETED/FAILED/CANCELLED
    - RUNNING → PAUSED → RUNNING
    - RUNNING → RETRYING → RUNNING/FAILED
    - Any state → CANCELLED
    
    Example:
        ```python
        # Check if a status is terminal
        status = WorkflowStatus.COMPLETED
        if WorkflowStatus.is_terminal(status):
            print(f"Workflow has ended with status: {status}")
            
        # Get a human-readable name
        print(WorkflowStatus.get_display_name("running"))  # "Running"
        ```
    
    Attributes:
        PENDING: Initial state, waiting to start
        RUNNING: Currently executing
        COMPLETED: Finished successfully
        FAILED: Finished with errors
        CANCELLED: Manually stopped
        PAUSED: Temporarily suspended
        SCHEDULED: Waiting to start at a specific time
        RETRYING: Retrying after a failure
        TIMED_OUT: Exceeded maximum execution time
        SKIPPED: Skipped due to dependencies or conditions
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    SCHEDULED = "scheduled"
    RETRYING = "retrying"
    TIMED_OUT = "timed_out"
    SKIPPED = "skipped"
    
    @classmethod
    def is_terminal(cls, status: Union['WorkflowStatus', str]) -> bool:
        """Check if a status is terminal (no further transitions possible).
        
        Args:
            status: The status to check, can be a WorkflowStatus or string
            
        Returns:
            bool: True if the status is terminal, False otherwise
            
        Example:
            >>> WorkflowStatus.is_terminal(WorkflowStatus.COMPLETED)
            True
            >>> WorkflowStatus.is_terminal("failed")
            True
            >>> WorkflowStatus.is_terminal(WorkflowStatus.RUNNING)
            False
        """
        if isinstance(status, str):
            try:
                status = cls(status.lower())
            except ValueError:
                return False
                
        return status in (cls.COMPLETED, cls.FAILED, cls.CANCELLED, 
                         cls.TIMED_OUT, cls.SKIPPED)
    
    @classmethod
    def is_active(cls, status: Union['WorkflowStatus', str]) -> bool:
        """Check if a status indicates the workflow is currently active.
        
        Args:
            status: The status to check, can be a WorkflowStatus or string
            
        Returns:
            bool: True if the workflow is active, False otherwise
            
        Example:
            >>> WorkflowStatus.is_active(WorkflowStatus.RUNNING)
            True
            >>> WorkflowStatus.is_active("paused")
            True
            >>> WorkflowStatus.is_active("completed")
            False
        """
        if isinstance(status, str):
            try:
                status = cls(status.lower())
            except ValueError:
                return False
                
        return status in (cls.RUNNING, cls.PAUSED, cls.RETRYING)
    
    @classmethod
    def can_transition(
        cls, 
        from_status: Union['WorkflowStatus', str], 
        to_status: Union['WorkflowStatus', str]
    ) -> bool:
        """Check if a status transition is valid.
        
        Args:
            from_status: The current status
            to_status: The target status
            
        Returns:
            bool: True if the transition is valid, False otherwise
            
        Example:
            >>> WorkflowStatus.can_transition("pending", "running")
            True
            >>> WorkflowStatus.can_transition("completed", "running")
            False
        """
        # Convert string statuses to enums
        if isinstance(from_status, str):
            try:
                from_status = cls(from_status.lower())
            except ValueError:
                return False
                
        if isinstance(to_status, str):
            try:
                to_status = cls(to_status.lower())
            except ValueError:
                return False
        
        # Define valid transitions
        valid_transitions = {
            cls.PENDING: {cls.RUNNING, cls.CANCELLED, cls.SKIPPED},
            cls.RUNNING: {cls.COMPLETED, cls.FAILED, cls.PAUSED, cls.CANCELLED, cls.TIMED_OUT, cls.RETRYING},
            cls.PAUSED: {cls.RUNNING, cls.CANCELLED},
            cls.RETRYING: {cls.RUNNING, cls.FAILED, cls.CANCELLED},
            cls.SCHEDULED: {cls.PENDING, cls.CANCELLED},
            # Terminal states can't transition to other states
            **{s: set() for s in (cls.COMPLETED, cls.FAILED, cls.CANCELLED, cls.TIMED_OUT, cls.SKIPPED)}
        }
        
        return to_status in valid_transitions.get(from_status, set())
    
    @classmethod
    def get_display_name(cls, status: Union['WorkflowStatus', str]) -> str:
        """Get a human-readable display name for a status.
        
        Args:
            status: The status to get the display name for
            
        Returns:
            str: A human-readable display name
            
        Example:
            >>> WorkflowStatus.get_display_name("running")
            'Running'
        """
        if isinstance(status, str):
            try:
                status = cls(status.lower())
            except ValueError:
                return status.title().replace('_', ' ')
                
        return status.value.title().replace('_', ' ')
    
    @classmethod
    def get_status_category(cls, status: Union['WorkflowStatus', str]) -> str:
        """Get the category of a status (success, warning, error, info).
        
        Args:
            status: The status to get the category for
            
        Returns:
            str: The status category
            
        Example:
            >>> WorkflowStatus.get_status_category("completed")
            'success'
        """
        if isinstance(status, str):
            try:
                status = cls(status.lower())
            except ValueError:
                return 'info'
        
        if status == cls.COMPLETED:
            return 'success'
        elif status in (cls.FAILED, cls.CANCELLED, cls.TIMED_OUT):
            return 'error'
        elif status in (cls.PAUSED,):
            return 'warning'
        else:
            return 'info'

class ServiceHealth(str, Enum):
    """Health status of a service.
    
    This enum represents the health state of a service, which is used to
    determine if a service is functioning correctly. It provides methods to
    check service health and convert between different health status formats.
    
    Health States:
    - HEALTHY: Service is operating normally
    - UNHEALTHY: Service is not functioning correctly
    - STARTING: Service is initializing
    - STOPPED: Service has been stopped
    - DEGRADED: Service is running but with reduced functionality
    - UNKNOWN: Health status cannot be determined
    
    Example:
        ```python
        # Check if a service is healthy
        status = ServiceHealth.HEALTHY
        if ServiceHealth.is_healthy(status):
            print("Service is healthy")
            
        # Convert HTTP status to health status
        health = ServiceHealth.from_http_status(200)
        print(health)  # ServiceHealth.HEALTHY
        
        # Get a human-readable name
        print(ServiceHealth.get_display_name("degraded"))  # "Degraded"
        ```
    
    Attributes:
        HEALTHY: Service is operating normally
        UNHEALTHY: Service is not functioning correctly
        STARTING: Service is initializing
        STOPPED: Service has been stopped
        DEGRADED: Service is running but with reduced functionality
        UNKNOWN: Health status cannot be determined
    """
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPED = "stopped"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
    
    @classmethod
    def is_healthy(cls, health: Union['ServiceHealth', str]) -> bool:
        """Check if a health status indicates the service is healthy.
        
        Args:
            health: The health status to check, can be a ServiceHealth or string
            
        Returns:
            bool: True if the service is healthy, False otherwise
            
        Example:
            >>> ServiceHealth.is_healthy(ServiceHealth.HEALTHY)
            True
            >>> ServiceHealth.is_healthy("degraded")
            True
            >>> ServiceHealth.is_healthy("unhealthy")
            False
        """
        if isinstance(health, str):
            try:
                health = cls(health.lower())
            except ValueError:
                return False
                
        return health in (cls.HEALTHY, cls.DEGRADED)
    
    @classmethod
    def is_unhealthy(cls, health: Union['ServiceHealth', str]) -> bool:
        """Check if a health status indicates the service is unhealthy.
        
        Args:
            health: The health status to check, can be a ServiceHealth or string
            
        Returns:
            bool: True if the service is unhealthy, False otherwise
            
        Example:
            >>> ServiceHealth.is_unhealthy(ServiceHealth.UNHEALTHY)
            True
            >>> ServiceHealth.is_unhealthy("stopped")
            True
            >>> ServiceHealth.is_unhealthy("healthy")
            False
        """
        if isinstance(health, str):
            try:
                health = cls(health.lower())
            except ValueError:
                return True  # Consider unknown statuses as unhealthy
                
        return health in (cls.UNHEALTHY, cls.STOPPED)
    
    @classmethod
    def from_http_status(
        cls, 
        status_code: int, 
        success_codes: Optional[Set[int]] = None,
        degraded_codes: Optional[Set[int]] = None
    ) -> 'ServiceHealth':
        """Determine service health from an HTTP status code.
        
        Args:
            status_code: The HTTP status code
            success_codes: Set of status codes to consider as healthy (default: 200-299)
            degraded_codes: Set of status codes to consider as degraded
            
        Returns:
            ServiceHealth: The corresponding health status
            
        Example:
            >>> ServiceHealth.from_http_status(200)
            <ServiceHealth.HEALTHY: 'healthy'>
            >>> ServiceHealth.from_http_status(503)
            <ServiceHealth.UNHEALTHY: 'unhealthy'>
        """
        success_codes = success_codes or set(range(200, 300))
        degraded_codes = degraded_codes or set()
        
        if status_code in success_codes:
            return cls.HEALTHY
        elif status_code in degraded_codes:
            return cls.DEGRADED
        else:
            return cls.UNHEALTHY
    
    @classmethod
    def from_boolean(cls, is_healthy: bool) -> 'ServiceHealth':
        """Convert a boolean to a health status.
        
        Args:
            is_healthy: Whether the service is healthy
            
        Returns:
            ServiceHealth: HEALTHY if True, UNHEALTHY if False
            
        Example:
            >>> ServiceHealth.from_boolean(True)
            <ServiceHealth.HEALTHY: 'healthy'>
        """
        return cls.HEALTHY if is_healthy else cls.UNHEALTHY
    
    @classmethod
    def get_display_name(cls, health: Union['ServiceHealth', str]) -> str:
        """Get a human-readable display name for a health status.
        
        Args:
            health: The health status to get the display name for
            
        Returns:
            str: A human-readable display name
            
        Example:
            >>> ServiceHealth.get_display_name("healthy")
            'Healthy'
        """
        if isinstance(health, str):
            try:
                health = cls(health.lower())
            except ValueError:
                return health.title()
                
        return health.value.title()
    
    @classmethod
    def get_health_category(cls, health: Union['ServiceHealth', str]) -> str:
        """Get the category of a health status (success, warning, error, info).
        
        Args:
            health: The health status to get the category for
            
        Returns:
            str: The status category ('success', 'warning', 'error', or 'info')
            
        Example:
            >>> ServiceHealth.get_health_category("healthy")
            'success'
        """
        if isinstance(health, str):
            try:
                health = cls(health.lower())
            except ValueError:
                return 'info'
        
        if health == cls.HEALTHY:
            return 'success'
        elif health == cls.DEGRADED:
            return 'warning'
        elif health in (cls.UNHEALTHY, cls.STOPPED):
            return 'error'
        else:
            return 'info'

class ServiceDefinition(BaseModel):
    """Definition of a service in a workflow.
    
    This model represents a service that can be deployed and managed as part of a workflow.
    It includes configuration for the service's container, resources, health checks, and more.
    
    Attributes:
        name: Unique name of the service within the workflow
        image: Docker image to use for the service
        version: Version of the service image (default: "latest")
        command: Command to run in the container
        args: Arguments to pass to the container command
        env: Environment variables to set in the container
        ports: Port mappings for the container
        volumes: Volume mounts for the container
        resources: Resource requirements and limits
        health_check: Health check configuration
        depends_on: Services that this service depends on
        restart_policy: Container restart policy
        deploy: Deployment configuration
        configs: Configuration references
        secrets: Secret references
        labels: Custom metadata labels
        networks: Networks to connect the service to
        
    Example:
        ```python
        service = ServiceDefinition(
            name="web",
            image="nginx:alpine",
            ports=["80:80"],
            env={"ENV": "production"},
            resources={"limits": {"cpus": "0.5", "memory": "512M"}},
            health_check={
                "test": ["CMD", "curl", "-f", "http://localhost"],
                "interval": 30000000000,  # 30s in nanoseconds
                "timeout": 10000000000,   # 10s in nanoseconds
                "retries": 3,
                "start_period": 5000000000  # 5s in nanoseconds
            }
        )
        ```
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$',
        description="Name of the service. Must be a valid DNS label.",
        example="web"
    )
    
    image: str = Field(
        ...,
        description="Container image to use for the service",
        example="nginx:alpine"
    )
    
    version: str = Field(
        "latest",
        description="Version of the service image",
        example="1.0.0"
    )
    
    command: Optional[Union[str, List[str]]] = Field(
        None,
        description="Command to run in the container",
        example=["nginx", "-g", "daemon off;"]
    )
    
    args: Optional[Union[str, List[str]]] = Field(
        None,
        description="Arguments to pass to the container command",
        example=["--debug"]
    )
    
    env: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set in the container"
    )
    
    ports: List[Union[str, int, Dict[str, Any]]] = Field(
        default_factory=list,
        description="Port mappings for the container"
    )
    
    volumes: List[Union[str, Dict[str, Any]]] = Field(
        default_factory=list,
        description="Volume mounts for the container"
    )
    
    resources: Dict[str, Any] = Field(
        default_factory=dict,
        description="Resource requirements and limits"
    )
    
    health_check: Optional[Dict[str, Any]] = Field(
        None,
        alias="healthCheck",
        description="Health check configuration"
    )
    
    depends_on: List[str] = Field(
        default_factory=list,
        alias="dependsOn",
        description="Services that this service depends on"
    )
    
    restart_policy: Optional[Dict[str, Any]] = Field(
        None,
        alias="restartPolicy",
        description="Container restart policy"
    )
    
    deploy: Optional[Dict[str, Any]] = Field(
        None,
        description="Deployment configuration"
    )
    
    configs: List[Union[str, Dict[str, Any]]] = Field(
        default_factory=list,
        description="Configuration references"
    )
    
    secrets: List[Union[str, Dict[str, str]]] = Field(
        default_factory=list,
        description="Secret references"
    )
    
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom metadata labels"
    )
    
    networks: List[Union[str, Dict[str, Any]]] = Field(
        default_factory=list,
        description="Networks to connect the service to"
    )
    
    # Pydantic configuration
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "web",
                    "image": "nginx:alpine",
                    "ports": ["80:80"],
                    "environment": {"ENV": "production"},
                    "deploy": {
                        "replicas": 3,
                        "resources": {
                            "limits": {"cpus": "0.5", "memory": "512M"}
                        }
                    }
                }
            ]
        }
    }
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate the service name."""
        if not v:
            raise ValueError("Service name cannot be empty")
        if len(v) > 63:
            raise ValueError("Service name must be 63 characters or less")
        if not re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$', v):
            raise ValueError(
                "Service name must consist of lowercase alphanumeric characters, '-', or '.', "
                "and must start and end with an alphanumeric character"
            )
        return v
    
    @field_validator('ports')
    @classmethod
    def validate_ports(cls, v: List[Any]) -> List[Any]:
        """Validate port mappings."""
        for port in v:
            if isinstance(port, str):
                if not re.match(r'^\d+(?::\d+)?(?:/tcp|/udp)?$', port):
                    raise ValueError(f"Invalid port format: {port}")
            elif not isinstance(port, (int, dict)):
                raise ValueError("Port must be a string, integer, or mapping")
        return v
    
    @model_validator(mode='after')
    def validate_service_definition(self) -> 'ServiceDefinition':
        """Validate the service definition."""
        # Ensure image has a valid format
        if ':' not in self.image and '@' not in self.image:
            self.image = f"{self.image}:{self.version}"
        
        # Ensure health check has required fields if provided
        if self.health_check and 'test' not in self.health_check:
            raise ValueError("Health check must include a 'test' command")
        
        # Ensure resource limits are valid if provided
        if 'limits' in self.resources:
            limits = self.resources['limits']
            if 'cpus' in limits and not re.match(r'^\d+(\.\d+)?$', str(limits['cpus'])):
                raise ValueError("CPU limit must be a number")
            if 'memory' in limits and not re.match(r'^\d+[bkmgBKMG]?$', str(limits['memory'])):
                raise ValueError("Memory limit must be a number with optional unit (b, k, m, g)")
        
        return self
    
    def get_image_name(self) -> str:
        """Get the image name without tag or digest."""
        return self.image.split('@')[0].split(':')[0]
    
    def get_image_tag(self) -> str:
        """Get the image tag, or 'latest' if not specified."""
        if '@' in self.image:
            return 'latest'  # Digest doesn't have a tag
        parts = self.image.split(':', 1)
        return parts[1] if len(parts) > 1 else 'latest'
    
    def get_image_digest(self) -> Optional[str]:
        """Get the image digest if specified."""
        return self.image.split('@', 1)[1] if '@' in self.image else None
    
    def get_environment(self) -> Dict[str, str]:
        """Get environment variables as a dictionary."""
        return {**self.env, 'VERSION': self.version}
    
    def get_resource_limits(self) -> Dict[str, str]:
        """Get resource limits as a dictionary."""
        return self.resources.get('limits', {})
    
    def get_resource_requests(self) -> Dict[str, str]:
        """Get resource requests as a dictionary."""
        return self.resources.get('requests', {})
    
    def is_healthy(self, health_status: Optional[Dict[str, Any]] = None) -> bool:
        """Check if the service is healthy based on health status."""
        if not health_status:
            return True  # Assume healthy if no status provided
        return health_status.get('status', '').lower() == 'healthy'
    
    def to_dict(self, **kwargs: Any) -> Dict[str, Any]:
        """Convert the service definition to a dictionary.
        
        Args:
            **kwargs: Additional arguments to pass to model_dump()
            
        Returns:
            Dict containing the serialized service definition
            
        Example:
            ```python
            service = ServiceDefinition(name="web", image="nginx:alpine")
            service_dict = service.to_dict()
            # {'name': 'web', 'image': 'nginx:alpine', 'version': 'latest', ...}
            ```
        """
        return self.model_dump(by_alias=True, exclude_unset=True, **kwargs)
    
    @classmethod
    def from_dict(cls, data: Union[Dict[str, Any], str, bytes, bytearray]) -> 'ServiceDefinition':
        """Create a ServiceDefinition from a dictionary, JSON string, or bytes.
        
        Args:
            data: Dictionary, JSON string, or bytes containing the service definition
            
        Returns:
            A new ServiceDefinition instance
            
        Raises:
            ValueError: If the input data is invalid
            ValidationError: If the data doesn't match the model schema
            
        Example:
            ```python
            data = {'name': 'web', 'image': 'nginx:alpine'}
            service = ServiceDefinition.from_dict(data)
            
            # Or from JSON string
            json_str = '{"name": "web", "image": "nginx:alpine"}'
            service = ServiceDefinition.from_dict(json_str)
            ```
        """
        if isinstance(data, (str, bytes, bytearray)):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}") from e
                
        return cls.model_validate(data, strict=True)
    
    def to_json(self, **kwargs: Any) -> str:
        """Serialize the service definition to a JSON string.
        
        Args:
            **kwargs: Additional arguments to pass to model_dump_json()
            
        Returns:
            JSON string representation of the service definition
            
        Example:
            ```python
            service = ServiceDefinition(name="web", image="nginx:alpine")
            json_str = service.to_json(indent=2)
            ```
        """
        return self.model_dump_json(by_alias=True, exclude_unset=True, **kwargs)
    
    @classmethod
    def from_json(cls, json_str: Union[str, bytes, bytearray]) -> 'ServiceDefinition':
        """Create a ServiceDefinition from a JSON string or bytes.
        
        Args:
            json_str: JSON string or bytes containing the service definition
            
        Returns:
            A new ServiceDefinition instance
            
        Raises:
            ValueError: If the JSON is invalid
            ValidationError: If the data doesn't match the model schema
        """
        return cls.model_validate_json(json_str, strict=True)
    
    def copy(self, **updates: Any) -> 'ServiceDefinition':
        """Create a copy of the service definition with optional updates.
        
        Args:
            **updates: Field values to update in the copy
            
        Returns:
            A new ServiceDefinition instance with the updated values
            
        Example:
            ```python
            service = ServiceDefinition(name="web", image="nginx:alpine")
            updated = service.copy(image="nginx:1.23.0")
            ```
        """
        return self.model_copy(update=updates)
    
    def model_dump_with_metadata(self) -> Dict[str, Any]:
        """Dump the model with additional metadata.
        
        Returns:
            Dictionary containing the model data with metadata
        """
        data = self.model_dump(by_alias=True, exclude_unset=True)
        data['_metadata'] = {
            'model': self.__class__.__name__,
            'version': '1.0',
            'timestamp': datetime.utcnow().isoformat()
        }
        return data
    
    def __str__(self) -> str:
        """Return a string representation of the service."""
        return f"Service(name='{self.name}', image='{self.image}')"


class WorkflowRequest(BaseModel):
    """Base class for all workflow-related API requests.
    
    This class provides common fields, validation, and serialization methods
    for all workflow API requests.
    
    Example:
        ```python
        # Create a request
        request = WorkflowRequest()
        
        # Serialize to dict
        data = request.model_dump()
        
        # Serialize to JSON
        json_str = request.model_dump_json()
        
        # Create from dict
        new_request = WorkflowRequest.model_validate(data)
        
        # Create from JSON
        from_json = WorkflowRequest.model_validate_json(json_str)
        ```
    """
    request_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the request, generated automatically if not provided"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the request was created"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the request"
    )
    
    model_config = BaseModelConfig
    
    @field_validator('request_id', mode='before')
    @classmethod
    def validate_request_id(cls, v: Any) -> UUID:
        """Validate and convert request_id to UUID if it's a string."""
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError as e:
                raise ValueError("request_id must be a valid UUID") from e
        return v


class CreateWorkflowRequest(WorkflowRequest):
    """Request model for creating a new workflow.
    
    Attributes:
        name: Unique name for the workflow
        description: Optional description of the workflow
        services: List of service definitions in the workflow
        parameters: Input parameters for the workflow
        schedule: Optional scheduling configuration
        timeout: Optional timeout for the workflow execution
        tags: Optional tags for categorizing the workflow
        
    Example:
        ```python
        request = CreateWorkflowRequest(
            name="data-pipeline",
            description="ETL pipeline for processing customer data",
            services=[
                ServiceDefinition(
                    name="extractor",
                    image="data-extractor:1.0.0",
                    resources={"limits": {"cpus": 1, "memory": "1G"}}
                ),
                ServiceDefinition(
                    name="transformer",
                    image="data-transformer:1.0.0",
                    depends_on=["extractor"]
                )
            ],
            parameters={"input_path": "/data/input", "output_path": "/data/output"},
            tags=["etl", "batch"]
        )
        ```
    """
    name: str = Field(..., min_length=1, max_length=255, description="Name of the workflow")
    description: Optional[str] = Field(None, description="Description of the workflow")
    services: List[ServiceDefinition] = Field(
        ..., 
        min_length=1,
        description="List of services that make up the workflow"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Input parameters for the workflow"
    )
    schedule: Optional[Dict[str, Any]] = Field(
        None,
        description="Scheduling configuration for the workflow"
    )
    timeout: Optional[Union[int, str]] = Field(
        None,
        description="Timeout for workflow execution in seconds or duration string (e.g., '1h30m')"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorizing the workflow"
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate workflow name."""
        if not v.replace('_', '').isalnum():
            raise ValueError("Workflow name must be alphanumeric with optional underscores")
        return v.lower()
    
    @field_validator('services')
    @classmethod
    def validate_services(cls, v: List[ServiceDefinition]) -> List[ServiceDefinition]:
        """Validate service definitions."""
        service_names = {s.name for s in v}
        if len(service_names) != len(v):
            raise ValueError("Service names must be unique within a workflow")
        return v
    
    @field_validator('timeout', mode='before')
    @classmethod
    def validate_timeout(cls, v: Any) -> Optional[int]:
        """Convert timeout string to seconds."""
        if v is None:
            return None
            
        if isinstance(v, int):
            return v
            
        if isinstance(v, str):
            # Parse duration strings like '1h30m' to seconds
            try:
                return parse_duration(v).total_seconds()
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Invalid duration format: {v}") from e
                
        raise ValueError("Timeout must be an integer (seconds) or duration string")


class WorkflowResponse(WorkflowRequest):
    """Base response model for workflow operations.
    
    Attributes:
        workflow_id: Unique identifier for the workflow
        status: Current status of the workflow
        created_at: When the workflow was created
        updated_at: When the workflow was last updated
        created_by: User or system that created the workflow
        error: Optional error information if the operation failed
    """
    workflow_id: UUID = Field(..., description="Unique identifier for the workflow")
    status: WorkflowStatus = Field(..., description="Current status of the workflow")
    created_at: datetime = Field(..., description="When the workflow was created")
    updated_at: datetime = Field(..., description="When the workflow was last updated")
    created_by: str = Field(..., description="User or system that created the workflow")
    error: Optional[Dict[str, Any]] = Field(
        None,
        description="Error details if the operation failed"
    )
    
    @model_validator(mode='after')
    def validate_dates(self) -> 'WorkflowResponse':
        """Ensure updated_at is not before created_at."""
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be before created_at")
        return self


class ListWorkflowsRequest(WorkflowRequest):
    """Request model for listing workflows with filtering and pagination.
    
    Attributes:
        limit: Maximum number of workflows to return
        offset: Number of workflows to skip
        status: Filter workflows by status
        tags: Filter workflows by tags
        created_after: Filter workflows created after this timestamp
        created_before: Filter workflows created before this timestamp
        sort_by: Field to sort by (e.g., 'created_at', 'name')
        sort_order: Sort order ('asc' or 'desc')
    """
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of workflows to return")
    offset: int = Field(0, ge=0, description="Number of workflows to skip")
    status: Optional[WorkflowStatus] = Field(None, description="Filter by workflow status")
    tags: List[str] = Field(
        default_factory=list,
        description="Filter workflows that have all of these tags"
    )
    created_after: Optional[datetime] = Field(
        None,
        description="Filter workflows created after this timestamp"
    )
    created_before: Optional[datetime] = Field(
        None,
        description="Filter workflows created before this timestamp"
    )
    sort_by: str = Field(
        "created_at",
        description="Field to sort by (e.g., 'created_at', 'name')"
    )
    sort_order: str = Field(
        "desc",
        pattern="^(asc|desc)$",
        description="Sort order: 'asc' for ascending, 'desc' for descending"
    )
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Normalize and validate tags."""
        return [tag.strip().lower() for tag in v if tag.strip()]
    
    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        """Validate sort_by field."""
        valid_fields = {"name", "created_at", "updated_at", "status"}
        if v.lower() not in valid_fields:
            raise ValueError(f"Invalid sort field. Must be one of: {', '.join(valid_fields)}")
        return v.lower()


class WorkflowListResponse(WorkflowRequest):
    """Response model for listing workflows.
    
    Attributes:
        workflows: List of workflows matching the query
        total: Total number of workflows matching the filters
        limit: Maximum number of workflows returned
        offset: Number of workflows skipped
    """
    workflows: List[WorkflowResponse] = Field(
        default_factory=list,
        description="List of workflows matching the query"
    )
    total: int = Field(0, ge=0, description="Total number of workflows matching the filters")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of workflows returned")
    offset: int = Field(0, ge=0, description="Number of workflows skipped")
    
    @model_validator(mode='after')
    def validate_pagination(self) -> 'WorkflowListResponse':
        """Validate pagination parameters."""
        if self.offset >= self.total and self.total > 0:
            raise ValueError("Offset cannot be greater than or equal to total")
        if len(self.workflows) > self.limit:
            raise ValueError("Number of workflows cannot exceed limit")
        return self


class ErrorResponse(BaseModel):
    """Standard error response model for API errors.
    
    Attributes:
        error: Error code
        message: Human-readable error message
        details: Additional error details
        request_id: Unique identifier for the request that caused the error
        timestamp: When the error occurred
    """
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    request_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the request that caused the error"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the error occurred"
    )
    
    model_config = BaseModelConfig
    
    @classmethod
    def from_exception(
        cls,
        error: Exception,
        status_code: int = 500,
        request_id: Optional[UUID] = None,
        **kwargs: Any
    ) -> 'ErrorResponse':
        """Create an ErrorResponse from an exception."""
        error_class = error.__class__.__name__
        return cls(
            error=snake_case(error_class).upper(),
            message=str(error) or error_class,
            details={"type": error_class, **kwargs},
            request_id=request_id or uuid4()
        )


class ServiceHealth(str, Enum):
    """Health status of a service."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPED = "stopped"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
    
    @classmethod
    def is_healthy(cls, health: 'ServiceHealth') -> bool:
        """Check if a health status is considered healthy."""
        return health == cls.HEALTHY
    
    @classmethod
    def is_unhealthy(cls, health: 'ServiceHealth') -> bool:
        """Check if a health status is considered unhealthy."""
        return health in (cls.UNHEALTHY, cls.STOPPED, cls.DEGRADED)


class ServiceDefinition(BaseModel):
    """Definition of a service in a workflow.
    
    This model represents the configuration for a single service within a workflow,
    including container settings, resource limits, and dependencies.
    """
    model_config = ConfigDict(
        # Allow extra fields for forward compatibility
        extra="ignore",
        # Enable population by field name
        populate_by_name=True
    )
    
    # Required fields
    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]+$',
        description=(
            "Name of the service. Must be unique within the workflow. "
            "Only alphanumeric characters, underscores, dots, and hyphens are allowed."
        ),
        json_schema_extra={"example": "web"}
    )
    
    image: str = Field(
        ...,
        min_length=1,
        description=(
            "Docker image to use for this service. "
            "Can be a repository/tag or a full image reference."
        ),
        json_schema_extra={"example": "nginx:latest"}
    )
    
    # Container configuration
    command: Optional[Union[str, List[str]]] = Field(
        default=None,
        description=(
            "Command to run in the container. "
            "Can be a string or a list of strings."
        ),
        json_schema_extra={"example": ["nginx", "-g", "daemon off;"]}
    )
    
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Environment variables to set in the container. "
            "Keys are variable names, values are variable values."
        ),
        json_schema_extra={"example": {"DEBUG": "true", "LOG_LEVEL": "info"}}
    )
    
    ports: Dict[str, Union[str, int]] = Field(
        default_factory=dict,
        description=(
            "Port mappings for the container. "
            "Keys are host ports, values are container ports. "
            "Use 'host:container' format or {'published': X, 'target': Y} for advanced options."
        ),
        json_schema_extra={"example": {"8080": 80, "8443": 443}}
    )
    
    volumes: Dict[str, Union[str, Dict[str, str]]] = Field(
        default_factory=dict,
        description=(
            "Volume mappings for the container. "
            "Keys are host paths or volume names, values are container paths. "
            "Use 'host:container' format or {'type': 'volume', 'source': '...', 'target': '...'} for advanced options."
        ),
        json_schema_extra={"example": {"./data": "/app/data"}}
    )
    
    # Dependencies
    depends_on: List[str] = Field(
        default_factory=list,
        description=(
            "List of service names that this service depends on. "
            "The services will be started in dependency order."
        ),
        json_schema_extra={"example": ["database", "cache"]}
    )
    
    # Health and lifecycle
    healthcheck: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Health check configuration. "
            "Example: {'test': ['CMD', 'curl', '-f', 'http://localhost'], 'interval': '30s', 'timeout': '10s', 'retries': 3}"
        )
    )
    
    restart_policy: Literal["no", "on-failure", "always", "unless-stopped"] = Field(
        default="no",
        description=(
            "Restart policy for the container. "
            "One of: 'no', 'on-failure', 'always', 'unless-stopped'"
        ),
        json_schema_extra={"example": "unless-stopped"}
    )
    
    # Resource limits
    mem_limit: Optional[Union[int, str]] = Field(
        default=None,
        description=(
            "Memory limit for the container. "
            "Can be a string with units (e.g., '1g', '512m') or an integer in bytes."
        ),
        json_schema_extra={"example": "1g"}
    )
    
    cpus: Optional[float] = Field(
        default=None,
        ge=0.01,
        le=1024.0,
        description=(
            "CPU limit in CPU units. "
            "1.0 means one CPU core, 0.5 means half a CPU core, etc."
        ),
        json_schema_extra={"example": 0.5}
    )
    
    # Validators
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate service name."""
        if not v:
            raise ValueError("Service name cannot be empty")
        if len(v) > 128:
            raise ValueError("Service name cannot exceed 128 characters")
        return v
    
    @field_validator('ports')
    @classmethod
    def validate_ports(cls, v: Dict[str, Union[str, int, Dict[str, Any]]]) -> Dict[str, Union[str, int, Dict[str, Any]]]:
        """Validate port mappings."""
        for host_port, container_port in v.items():
            if isinstance(container_port, (str, int)):
                try:
                    # Simple port mapping (host:container)
                    if isinstance(container_port, str) and not container_port.isdigit():
                        raise ValueError(f"Invalid container port: {container_port}")
                    if not host_port.isdigit():
                        raise ValueError(f"Invalid host port: {host_port}")
                except (ValueError, AttributeError) as e:
                    raise ValueError(f"Invalid port mapping format for '{host_port}': {container_port}. {str(e)}")
        return v
    
    @field_validator('depends_on')
    @classmethod
    def validate_depends_on(cls, v: List[str]) -> List[str]:
        """Validate service dependencies."""
        if not v:
            return v
            
        # Check for empty strings
        if any(not dep for dep in v):
            raise ValueError("Dependency names cannot be empty")
            
        # Check for self-references
        if len(set(v)) != len(v):
            raise ValueError("Duplicate dependencies found")
            
        return v
    
    @field_validator('mem_limit', mode='before')
    @classmethod
    def validate_mem_limit(cls, v: Any) -> Optional[Union[int, str]]:
        """Validate memory limit format."""
        if v is None:
            return None
            
        if isinstance(v, (int, float)):
            if v <= 0:
                raise ValueError("Memory limit must be positive")
            return v
            
        if not isinstance(v, str):
            raise ValueError("Memory limit must be a string or number")
            
        # Validate string format (e.g., '1g', '512m')
        if v[-1] not in ('b', 'k', 'm', 'g'):
            try:
                return int(v)
            except ValueError:
                pass
                
        return v

class WorkflowDefinition(BaseModel):
    """Definition of a workflow.
    
    This model represents a complete workflow definition that can be executed
    by the workflow engine. It includes all services, networks, and volumes
    needed to run the workflow.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "web-app",
                "version": "1.0",
                "description": "A simple web application with a database",
                "services": {
                    "web": {
                        "name": "web",
                        "image": "nginx:latest",
                        "ports": {"80": "8080"},
                        "depends_on": ["api"]
                    },
                    "api": {
                        "image": "myapp/api:1.0.0",
                        "environment": {"DB_HOST": "db"},
                        "depends_on": ["db"]
                    },
                    "db": {
                        "image": "postgres:13",
                        "environment": {
                            "POSTGRES_PASSWORD": "example"
                        },
                        "volumes": ["postgres_data:/var/lib/postgresql/data"]
                    }
                },
                "networks": {
                    "app_network": {
                        "driver": "bridge"
                    }
                },
                "volumes": {
                    "postgres_data": {}
                }
            }
        },
        # Allow extra fields for forward compatibility
        extra="ignore",
        # Enable population by field name
        populate_by_name=True,
        # Enable arbitrary types for nested dictionaries
        arbitrary_types_allowed=True
    )
    
    # Required fields
    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$',
        description=(
            "Name of the workflow. "
            "Must start with an alphanumeric character and can contain letters, "
            "numbers, underscores, dots, and hyphens."
        ),
        json_schema_extra={"example": "web-app"}
    )
    
    version: str = Field(
        default="1.0",
        pattern=r'^\d+\.\d+(\.\d+)?(-[a-zA-Z0-9.]+)?$',
        description=(
            "Version of the workflow definition. "
            "Should follow semantic versioning (e.g., '1.0.0')."
        ),
        json_schema_extra={"example": "1.0.0"}
    )
    
    services: Dict[str, ServiceDefinition] = Field(
        ...,
        description=(
            "Services that make up the workflow. "
            "Each service will be deployed as a container."
        ),
        json_schema_extra={"example": {"web": {"image": "nginx:latest"}}}
    )
    
    # Optional fields with defaults
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description=(
            "Human-readable description of what this workflow does. "
            "This is for documentation purposes only."
        ),
        json_schema_extra={"example": "A simple web application with a database"}
    )
    
    env_file: Optional[Union[str, List[str]]] = Field(
        default=None,
        description=(
            "Path to environment file(s) to load. "
            "Can be a single path or a list of paths. "
            "Paths are relative to the workflow definition file."
        ),
        json_schema_extra={"example": [".env", ".env.local"]}
    )
    
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Environment variables that will be available to all services. "
            "Service-specific environment variables take precedence."
        ),
        json_schema_extra={"example": {"NODE_ENV": "production"}}
    )
    
    networks: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description=(
            "Networks to create and connect services to. "
            "Each key is a network name, and the value is a dictionary of network options. "
            "If not specified, a default network will be created."
        ),
        json_schema_extra={
            "example": {
                "app_network": {
                    "driver": "bridge",
                    "driver_opts": {
                        "com.docker.network.driver.mtu": "1450"
                    },
                    "labels": {
                        "com.example.description": "Application network"
                    }
                }
            }
        }
    )
    
    volumes: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description=(
            "Named volumes that can be referenced by services. "
            "Each key is a volume name, and the value is a dictionary of volume options. "
            "If the volume is used by a service but not defined here, it will be created with default options."
        ),
        json_schema_extra={
            "example": {
                "db_data": {
                    "driver": "local",
                    "labels": {
                        "com.example.description": "Database data volume"
                    }
                }
            }
        }
    )
    
    # Validators
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate workflow name."""
        if not v:
            raise ValueError("Workflow name cannot be empty")
        if len(v) > 128:
            raise ValueError("Workflow name cannot exceed 128 characters")
        return v
    
    @field_validator('services')
    @classmethod
    def validate_services(cls, v: Dict[str, ServiceDefinition]) -> Dict[str, ServiceDefinition]:
        """Validate services configuration."""
        if not v:
            raise ValueError("At least one service must be defined")
            
        # Check for duplicate service names (shouldn't happen with dict keys, but just in case)
        service_names = list(v.keys())
        if len(set(service_names)) != len(service_names):
            raise ValueError("Duplicate service names found")
            
        # Validate service dependencies
        all_service_names = set(service_names)
        for service_name, service in v.items():
            for dep in service.depends_on:
                if dep not in all_service_names:
                    raise ValueError(f"Service '{service_name}' depends on unknown service: {dep}")
                if dep == service_name:
                    raise ValueError(f"Service '{service_name}' cannot depend on itself")
        
        # TODO: Detect circular dependencies (would require building a dependency graph)
        
        return v
    
    @field_validator('networks')
    @classmethod
    def validate_networks(cls, v: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Validate networks configuration."""
        for network_name, network_config in v.items():
            if not network_name:
                raise ValueError("Network name cannot be empty")
            if not isinstance(network_config, dict):
                raise ValueError(f"Network configuration for '{network_name}' must be a dictionary")
        return v
    
    @field_validator('volumes')
    @classmethod
    def validate_volumes(cls, v: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Validate volumes configuration."""
        for volume_name, volume_config in v.items():
            if not volume_name:
                raise ValueError("Volume name cannot be empty")
            if volume_config is not None and not isinstance(volume_config, dict):
                raise ValueError(f"Volume configuration for '{volume_name}' must be a dictionary or null")
        return v
    
    # Helper methods
    def get_service_dependencies(self, service_name: str) -> List[str]:
        """Get all services that the specified service depends on."""
        if service_name not in self.services:
            raise ValueError(f"Unknown service: {service_name}")
        return self.services[service_name].depends_on.copy()
    
    def get_dependent_services(self, service_name: str) -> List[str]:
        """Get all services that depend on the specified service."""
        if service_name not in self.services:
            raise ValueError(f"Unknown service: {service_name}")
            
        dependents = []
        for name, service in self.services.items():
            if service_name in service.depends_on:
                dependents.append(name)
        return dependents
    
    def get_start_order(self) -> List[str]:
        """Get the order in which services should be started.
        
        Returns:
            List of service names in the order they should be started.
            Services with no dependencies come first, followed by services
            whose dependencies have already been started.
        """
        # This is a simple topological sort (Kahn's algorithm)
        # For complex dependency graphs, consider using networkx
        
        # Make a copy of the services to avoid modifying the original
        services = {name: service.depends_on.copy() 
                   for name, service in self.services.items()}
        
        # Find all services with no incoming edges
        no_incoming = [name for name, deps in services.items() if not deps]
        
        ordered = []
        while no_incoming:
            # Take a service with no incoming edges
            service = no_incoming.pop()
            ordered.append(service)
            
            # Remove all edges from this service to others
            for other in list(services.keys()):
                if service in services[other]:
                    services[other].remove(service)
                    # If this was the last dependency, add to no_incoming
                    if not services[other]:
                        no_incoming.append(other)
            
            # Remove the service from the graph
            services.pop(service, None)
        
        # If there are remaining services, there's a cycle
        if services:
            raise ValueError("Circular dependency detected in service definitions")
            
        return ordered

class WorkflowState(BaseModel):
    """Runtime state of a workflow.
    
    This model tracks the current state of a workflow execution,
    including the status of all services and any errors that occurred.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "workflow_123",
                "name": "web-app",
                "status": "running",
                "created_at": "2023-01-01T12:00:00Z",
                "start_time": "2023-01-01T12:00:05Z",
                "services": {
                    "web": {
                        "status": "running",
                        "container_id": "a1b2c3d4e5f6",
                        "started_at": "2023-01-01T12:00:10Z"
                    },
                    "db": {
                        "status": "healthy",
                        "container_id": "b2c3d4e5f6g7",
                        "started_at": "2023-01-01T12:00:05Z"
                    }
                }
            }
        },
        # Enable JSON encoders for datetime serialization
        json_encoders={
            'datetime': lambda v: v.isoformat() if v else None,
        },
        # Allow extra fields for forward compatibility
        extra="ignore"
    )
    
    # Required fields
    workflow_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Unique identifier for the workflow instance. "
            "This is typically a UUID or other unique string."
        ),
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"}
    )
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description=(
            "Name of the workflow. "
            "This should match the name in the workflow definition."
        ),
        json_schema_extra={"example": "web-app"}
    )
    
    # Status fields
    status: WorkflowStatus = Field(
        default=WorkflowStatus.PENDING,
        description=(
            "Current status of the workflow. "
            "One of: 'pending', 'running', 'completed', 'failed', 'cancelled'"
        ),
        json_schema_extra={"example": "running"}
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description=(
            "Timestamp when the workflow was created. "
            "This is set automatically when the workflow is first created."
        ),
        json_schema_extra={"example": "2023-01-01T12:00:00Z"}
    )
    
    start_time: Optional[datetime] = Field(
        default=None,
        description=(
            "Timestamp when the workflow started executing. "
            "This is set when the first service starts."
        ),
        json_schema_extra={"example": "2023-01-01T12:00:05Z"}
    )
    
    end_time: Optional[datetime] = Field(
        default=None,
        description=(
            "Timestamp when the workflow completed or failed. "
            "This is set when the workflow reaches a terminal state."
        ),
        json_schema_extra={"example": "2023-01-01T12:05:00Z"}
    )
    
    # Runtime information
    services: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description=(
            "Runtime state of each service in the workflow. "
            "The keys are service names, and the values are dictionaries "
            "containing status information for each service."
        ),
        json_schema_extra={
            "example": {
                "web": {
                    "status": "running",
                    "container_id": "a1b2c3d4e5f6",
                    "started_at": "2023-01-01T12:00:10Z"
                }
            }
        }
    )
    
    error: Optional[str] = Field(
        default=None,
        max_length=10000,
        description=(
            "Error message if the workflow failed. "
            "This will contain a description of what went wrong."
        ),
        json_schema_extra={"example": "Failed to start service 'db': Port 5432 is already in use"}
    )
    
    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Additional metadata about the workflow execution. "
            "This can be used to store custom data or metrics."
        )
    )
    
    # Validators
    @field_validator('workflow_id')
    @classmethod
    def validate_workflow_id(cls, v: str) -> str:
        """Validate workflow ID."""
        if not v:
            raise ValueError("Workflow ID cannot be empty")
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: WorkflowStatus) -> WorkflowStatus:
        """Validate workflow status."""
        return WorkflowStatus(v) if isinstance(v, str) else v
    
    @field_validator('services')
    @classmethod
    def validate_services(cls, v: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Validate services state."""
        for service_name, service_state in v.items():
            if not service_name:
                raise ValueError("Service name cannot be empty")
            if not isinstance(service_state, dict):
                raise ValueError(f"Service state for '{service_name}' must be a dictionary")
        return v
    
    # Helper methods
    def is_running(self) -> bool:
        """Check if the workflow is currently running."""
        return self.status == WorkflowStatus.RUNNING
    
    def is_completed(self) -> bool:
        """Check if the workflow has completed successfully."""
        return self.status == WorkflowStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """Check if the workflow has failed."""
        return self.status == WorkflowStatus.FAILED
    
    def is_cancelled(self) -> bool:
        """Check if the workflow was cancelled."""
        return self.status == WorkflowStatus.CANCELLED
    
    def get_duration(self) -> Optional[float]:
        """Get the duration of the workflow in seconds.
        
        Returns:
            float: Duration in seconds, or None if the workflow hasn\'t started or completed.
        """
        if not self.start_time:
            return None
            
        end_time = self.end_time or datetime.now(timezone.utc)
        return (end_time - self.start_time).total_seconds()
    
    def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific service.
        
        Args:
            service_name: Name of the service to get status for.
            
        Returns:
            Dictionary containing the service status, or None if the service is not found.
        """
        return self.services.get(service_name)
    
    def update_service_status(
        self, 
        service_name: str, 
        status: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """Update the status of a service.
        
        Args:
            service_name: Name of the service to update.
            status: New status for the service.
            **kwargs: Additional fields to update.
        """
        if service_name not in self.services:
            self.services[service_name] = {}
            
        if status is not None:
            self.services[service_name]['status'] = status
            
        self.services[service_name].update({
            'updated_at': datetime.now(timezone.utc),
            **kwargs
        })

# Request and Response Models for API Endpoints
class CreateWorkflowRequest(BaseModel):
    """Request model for creating a workflow.
    
    This model is used to validate and document the request payload
    for creating a new workflow instance.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_definition": {
                    "name": "web-app",
                    "version": "1.0.0",
                    "description": "A simple web application with a database",
                    "services": {
                        "web": {
                            "image": "nginx:latest",
                            "ports": {"80": "8080"},
                            "depends_on": ["api"]
                        },
                        "api": {
                            "image": "myapp/api:1.0.0",
                            "environment": {"NODE_ENV": "production"},
                            "depends_on": ["db"]
                        },
                        "db": {
                            "image": "postgres:13",
                            "environment": {
                                "POSTGRES_PASSWORD": "${DB_PASSWORD}",
                                "POSTGRES_DB": "mydb"
                            },
                            "volumes": ["postgres_data:/var/lib/postgresql/data"]
                        }
                    },
                    "volumes": {
                        "postgres_data": {}
                    }
                },
                "parameters": {
                    "env": "production",
                    "DB_PASSWORD": "s3cr3tp@ssw0rd"
                },
                "tags": ["production", "web-app"],
                "metadata": {
                    "deployed_by": "user@example.com",
                    "environment": "production"
                }
            }
        },
        # Allow extra fields for forward compatibility
        extra="ignore"
    )
    
    workflow_definition: WorkflowDefinition = Field(
        ...,
        description=(
            "The complete workflow definition including services, networks, and volumes. "
            "This defines what will be deployed and how the services are connected."
        ),
        json_schema_extra={
            "example": {
                "name": "web-app",
                "services": {"web": {"image": "nginx:latest"}}
            }
        }
    )
    
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Key-value pairs of parameters that can be referenced in the workflow definition. "
            "Use the syntax ${PARAM_NAME} in the workflow definition to reference a parameter. "
            "Commonly used for environment-specific configuration like database credentials."
        ),
        json_schema_extra={
            "example": {
                "DB_PASSWORD": "s3cr3t",
                "API_KEY": "abc123",
                "ENVIRONMENT": "production"
            }
        }
    )
    
    tags: List[str] = Field(
        default_factory=list,
        description=(
            "Tags to associate with the workflow. "
            "Useful for filtering and organizing workflows."
        ),
        json_schema_extra={"example": ["production", "web-app"]}
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Additional metadata to associate with the workflow. "
            "This can be used to store deployment context or other custom data."
        ),
        json_schema_extra={
            "example": {
                "deployed_by": "user@example.com",
                "environment": "production",
                "deployment_id": "deploy-123"
            }
        }
    )
    
    # Validators
    @field_validator('parameters')
    @classmethod
    def validate_parameters(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters."""
        # Check for empty parameter values
        for key, value in v.items():
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"Parameter '{key}' cannot be empty")
        return v
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate tags."""
        for tag in v:
            if not tag or not tag.strip():
                raise ValueError("Tags cannot be empty")
            if len(tag) > 64:
                raise ValueError(f"Tag '{tag}' exceeds maximum length of 64 characters")
        return v


class CreateWorkflowResponse(BaseModel):
    """Response model for creating a workflow.
    
    This model defines the structure of the response returned when a new workflow
    is successfully created. It includes the workflow ID, status, and timestamps.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "web-app",
                "status": "pending",
                "created_at": "2023-01-01T12:00:00Z",
                "links": [
                    {
                        "rel": "self",
                        "href": "/api/workflows/550e8400-e29b-41d4-a716-446655440000",
                        "method": "GET"
                    },
                    {
                        "rel": "status",
                        "href": "/api/workflows/550e8400-e29b-41d4-a716-446655440000/status",
                        "method": "GET"
                    }
                ]
            }
        },
        # Enable JSON encoders for datetime serialization
        json_encoders={
            'datetime': lambda v: v.isoformat() if v else None,
        },
        # Allow extra fields for forward compatibility
        extra="ignore"
    )
    
    workflow_id: str = Field(
        ...,
        description=(
            "Unique identifier for the created workflow. "
            "This ID can be used to reference the workflow in subsequent API calls."
        ),
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"}
    )
    
    name: str = Field(
        ...,
        description=(
            "Name of the workflow. "
            "This matches the name specified in the workflow definition."
        ),
        json_schema_extra={"example": "web-app"}
    )
    
    status: str = Field(
        ...,
        description=(
            "Initial status of the workflow. "
            "This will typically be 'pending' immediately after creation."
        ),
        json_schema_extra={"example": "pending"}
    )
    
    created_at: datetime = Field(
        ...,
        description=(
            "Timestamp when the workflow was created. "
            "This is set to the current server time when the workflow is created."
        ),
        json_schema_extra={"example": "2023-01-01T12:00:00Z"}
    )
    
    links: List[Dict[str, str]] = Field(
        default_factory=list,
        description=(
            "HATEOAS-style links to related resources. "
            "These can be used to navigate the API."
        ),
        json_schema_extra={
            "example": [
                {
                    "rel": "self",
                    "href": "/api/workflows/550e8400-e29b-41d4-a716-446655440000",
                    "method": "GET"
                },
                {
                    "rel": "status",
                    "href": "/api/workflows/550e8400-e29b-41d4-a716-446655440000/status",
                    "method": "GET"
                }
            ]
        }
    )
    
    # Helper methods
    def add_link(self, rel: str, href: str, method: str = "GET") -> None:
        """Add a HATEOAS-style link to the response.
        
        Args:
            rel: The relationship type (e.g., 'self', 'status').
            href: The URL of the related resource.
            method: The HTTP method to use with the link (default: 'GET').
        """
        self.links.append({
            "rel": rel,
            "href": href,
            "method": method.upper()
        })
    
    def get_link(self, rel: str) -> Optional[Dict[str, str]]:
        """Get a link by its relationship type.
        
        Args:
            rel: The relationship type to look for.
            
        Returns:
            The link dictionary if found, or None if not found.
        """
        return next((link for link in self.links if link["rel"] == rel), None)

class StartWorkflowRequest(BaseModel):
    """Request model for starting a workflow."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "workflow_123",
                "timeout": 300
            }
        }
    )
    
    workflow_id: str = Field(
        ...,
        description="ID of the workflow to start",
        json_schema_extra={"example": "workflow_123"}
    )
    timeout: int = Field(
        default=300,
        description="Timeout in seconds",
        json_schema_extra={
            "description": "Timeout in seconds",
            "minimum": 1,
            "maximum": 3600
        }
    )

class StartWorkflowResponse(BaseModel):
    """Response model for starting a workflow."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "workflow_123",
                "status": "running",
                "start_time": "2023-01-01T12:00:00Z",
                "message": "Workflow started successfully"
            }
        }
    )
    
    This model defines the structure of the response returned when a workflow
    is successfully started. It includes the workflow ID, status, and timestamps.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "execution_id": "exec-1234567890abcdef",
                "name": "web-app",
                "status": "starting",
                "started_at": "2023-01-01T12:00:00Z",
                "timeout_seconds": 600,
                "links": [
                    {
                        "rel": "self",
                        "href": "/api/workflows/550e8400-e29b-41d4-a716-446655440000/executions/exec-1234567890abcdef",
                        "method": "GET"
                    },
                    {
                        "rel": "status",
                        "href": "/api/workflows/550e8400-e29b-41d4-a716-446655440000/status",
                        "method": "GET"
                    },
                    {
                        "rel": "stop",
                        "href": "/api/workflows/550e8400-e29b-41d4-a716-446655440000/executions/exec-1234567890abcdef/stop",
                        "method": "POST"
                    }
                ]
            }
        },
        # Enable JSON encoders for datetime serialization
        json_encoders={
            'datetime': lambda v: v.isoformat() if v else None,
        },
        # Allow extra fields for forward compatibility
        extra="ignore"
    )
    
    workflow_id: str = Field(
        ...,
        description=(
            "The unique identifier of the workflow that was started. "
            "This matches the workflow_id from the request."
        ),
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"}
    )
    
    execution_id: str = Field(
        ...,
        description=(
            "The unique identifier for this specific execution of the workflow. "
            "This can be used to track the status of the execution."
        ),
        json_schema_extra={"example": "exec-1234567890abcdef"}
    )
    
    name: str = Field(
        ...,
        description=(
            "The name of the workflow. "
            "This is provided for convenience and matches the workflow definition."
        ),
        json_schema_extra={"example": "web-app"}
    )
    
    status: str = Field(
        ...,
        description=(
            "The initial status of the workflow execution. "
            "This will typically be 'starting' immediately after the start request."
        ),
        json_schema_extra={"example": "starting"}
    )
    
    started_at: datetime = Field(
        ...,
        description=(
            "The timestamp when the workflow execution was started. "
            "This is set to the current server time when the workflow starts."
        ),
        json_schema_extra={"example": "2023-01-01T12:00:00Z"}
    )
    
    timeout_seconds: int = Field(
        ...,
        description=(
            "The maximum time in seconds that the workflow is allowed to run. "
            "The workflow will be automatically terminated if it exceeds this duration."
        ),
        json_schema_extra={"example": 600}
    )
    
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "The complete set of parameters being used for this execution, "
            "including any overrides from the start request."
        ),
        json_schema_extra={
            "example": {
                "ENVIRONMENT": "staging",
                "FEATURE_FLAGS": "new-ui,beta-feature"
            }
        }
    )
    
    links: List[Dict[str, str]] = Field(
        default_factory=list,
        description=(
            "HATEOAS-style links to related resources. "
            "These can be used to navigate the API and interact with the workflow execution."
        ),
        json_schema_extra={
            "example": [
                {
                    "rel": "self",
                    "href": "/api/workflows/550e8400-e29b-41d4-a716-446655440000/executions/exec-1234567890abcdef",
                    "method": "GET"
                },
                {
                    "rel": "status",
                    "href": "/api/workflows/550e8400-e29b-41d4-a716-446655440000/status",
                    "method": "GET"
                },
                {
                    "rel": "stop",
                    "href": "/api/workflows/550e8400-e29b-41d4-a716-446655440000/executions/exec-1234567890abcdef/stop",
                    "method": "POST"
                }
            ]
        }
    )
    
    # Helper methods
    def add_link(self, rel: str, href: str, method: str = "GET") -> None:
        """Add a HATEOAS-style link to the response.
        
        Args:
            rel: The relationship type (e.g., 'self', 'status', 'stop').
            href: The URL of the related resource.
            method: The HTTP method to use with the link (default: 'GET').
        """
        self.links.append({
            "rel": rel,
            "href": href,
            "method": method.upper()
        })
    
    def get_link(self, rel: str) -> Optional[Dict[str, str]]:
        """Get a link by its relationship type.
        
        Args:
            rel: The relationship type to look for.
            
        Returns:
            The link dictionary if found, or None if not found.
        """
        return next((link for link in self.links if link["rel"] == rel), None)


class StopWorkflowRequest(BaseModel):
    """Request model for stopping a workflow execution.

    This model is used to validate and document the request payload
    for stopping a running workflow instance.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "execution_id": "exec-1234567890abcdef",
                "force": False,
                "timeout": 30,
                "reason": "User requested stop"
            }
        },
        # Allow extra fields for forward compatibility
        extra="ignore"
    )

    workflow_id: str = Field(
        ...,
        min_length=1,
        description=(
            "The unique identifier of the workflow to stop. "
            "This should be a valid workflow ID that was returned "
            "when the workflow was created."
        ),
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"}
    )

    execution_id: Optional[str] = Field(
        default=None,
        description=(
            "Optional specific execution ID to stop. "
            "If not provided, the most recent execution will be stopped."
        ),
        json_schema_extra={"example": "exec-1234567890abcdef"}
    )

    force: bool = Field(
        default=False,
        description=(
            "If True, force immediate termination of the workflow. "
            "This may result in orphaned resources and should be used with caution. "
            "If False, the workflow will perform a graceful shutdown."
        )
    )

    timeout: int = Field(
        default=30,
        ge=0,
        le=300,
        description=(
            "Maximum time in seconds to wait for a graceful shutdown before forcing termination. "
            "Only applicable if force=False. Set to 0 for immediate graceful shutdown. "
            "Maximum allowed value is 300 seconds (5 minutes)."
        ),
        json_schema_extra={"example": 30}
    )

    reason: Optional[str] = Field(
        default=None,
        max_length=1000,
        description=(
            "Optional reason for stopping the workflow. "
            "This will be recorded in the workflow's history."
        ),
        json_schema_extra={"example": "User requested stop due to maintenance"}
    )

    # Validators
    @field_validator('workflow_id')
    @classmethod
    def validate_workflow_id(cls, v: str) -> str:
        """Validate workflow ID."""
        if not v or not v.strip():
            raise ValueError("Workflow ID cannot be empty")
        return v.strip()

    @field_validator('reason')
    @classmethod
    def validate_reason(cls, v: Optional[str]) -> Optional[str]:
        """Validate reason for stopping."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Reason cannot be empty if provided")
        return v


class StopWorkflowResponse(BaseModel):
    """Response model for stopping a workflow execution.

    This model defines the structure of the response returned when a workflow
    is successfully stopped. It includes the workflow ID, status, and timestamps.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "execution_id": "exec-1234567890abcdef",
                "name": "web-app",
                "status": "stopping",
                "stopped_at": "2023-01-01T12:05:00Z",
                "force_stop": False,
                "message": "Workflow stop requested. Graceful shutdown in progress.",
                "links": [
                    {
                        "rel": "status",
                        "href": "/api/workflows/550e8400-e29b-41d4-a716-446655440000/status",
                        "method": "GET"
                    }
                ]
            }
        },
        # Enable JSON encoders for datetime serialization
        json_encoders={
            'datetime': lambda v: v.isoformat() if v else None,
        },
        # Allow extra fields for forward compatibility
        extra="ignore"
    )

    workflow_id: str = Field(
        ...,
        description=(
            "The unique identifier of the workflow that was stopped. "
            "This matches the workflow_id from the request."
        ),
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"}
    )

    execution_id: str = Field(
        ...,
        description=(
            "The unique identifier of the execution that was stopped. "
            "This can be used to track the status of the stop operation."
        ),
        json_schema_extra={"example": "exec-1234567890abcdef"}
    )

    name: str = Field(
        ...,
        description=(
            "The name of the workflow. "
            "This is provided for convenience and matches the workflow definition."
        ),
        json_schema_extra={"example": "web-app"}
    )

    status: str = Field(
        ...,
        description=(
            "The status of the workflow after the stop request. "
            "This will typically be 'stopping' or 'stopped'."
        ),
        json_schema_extra={"example": "stopping"}
    )

    stopped_at: datetime = Field(
        ...,
        description=(
            "The timestamp when the stop was requested. "
            "Note that the actual stop may complete after this time, "
            "especially for graceful shutdowns."
        ),
        json_schema_extra={"example": "2023-01-01T12:05:00Z"}
    )

    force_stop: bool = Field(
        default=False,
        description=(
            "Indicates whether a forced stop was requested. "
            "If True, the workflow was terminated immediately without cleanup."
        )
    )

    message: str = Field(
        ...,
        description=(
            "A human-readable message describing the result of the stop request. "
            "This may include information about the shutdown process or any warnings."
        ),
        json_schema_extra={"example": "Workflow stop requested. Graceful shutdown in progress."}
    )

    links: List[Dict[str, str]] = Field(
        default_factory=list,
        description=(
            "HATEOAS-style links to related resources. "
            "These can be used to navigate the API and check the workflow status."
        ),
        json_schema_extra={
            "example": [
                {
                    "rel": "status",
                    "href": "/api/workflows/550e8400-e29b-41d4-a716-446655440000/status",
                    "method": "GET"
                },
                {
                    "rel": "logs",
                    "href": "/api/workflows/550e8400-e29b-41d4-a716-446655440000/logs",
                    "method": "GET"
                }
            ]
        }
    )

    # Helper methods
    def add_link(self, rel: str, href: str, method: str = "GET") -> None:
        """Add a HATEOAS-style link to the response.

        Args:
            rel: The relationship type (e.g., 'status', 'logs').
            href: The URL of the related resource.
            method: The HTTP method to use with the link (default: 'GET').
        """
        self.links.append({
            "rel": rel,
            "href": href,
            "method": method.upper()
        })

    def get_link(self, rel: str) -> Optional[Dict[str, str]]:
        """Get a link by its relationship type.

        Args:
            rel: The relationship type to look for.

        Returns:
            The link dictionary if found, or None if not found.
        """
        return next((link for link in self.links if link["rel"] == rel), None)

class ListWorkflowsRequest(BaseModel):
    """Request model for listing workflows."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "running",
                "limit": 10,
                "offset": 0
            }
        }
    )
    
    status: str = Field(
        default="all",
        json_schema={
            "description": "Filter workflows by status (all, running, completed, failed, cancelled)",
            "enum": ["all", "running", "completed", "failed", "cancelled"]
        }
    )
    limit: int = Field(
        default=50,
        json_schema={
            "description": "Maximum number of workflows to return",
            "minimum": 1,
            "maximum": 1000
        }
    )
    offset: int = Field(
        default=0,
        json_schema={
            "description": "Number of workflows to skip",
            "minimum": 0
        }
    )

class WorkflowSummary(BaseModel):
    """Summary of a workflow for listing."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "workflow_123",
                "name": "web-app",
                "status": "running",
                "created_at": "2023-01-01T12:00:00Z",
                "start_time": "2023-01-01T12:00:00Z",
                "service_count": 2
            }
        }
    )
    
    workflow_id: str = Field(..., json_schema={"description": "ID of the workflow"})
    name: str = Field(..., json_schema={"description": "Name of the workflow"})
    status: WorkflowStatus = Field(..., json_schema={"description": "Current status of the workflow"})
    created_at: datetime = Field(..., json_schema={"description": "When the workflow was created"})
    start_time: Optional[datetime] = Field(default=None, json_schema={"description": "When the workflow started"})
    end_time: Optional[datetime] = Field(default=None, json_schema={"description": "When the workflow ended"})
    service_count: int = Field(..., json_schema={"description": "Number of services in the workflow"})


class ListWorkflowsResponse(BaseModel):
    """Response model for listing workflows."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflows": [{
                    "workflow_id": "workflow_123",
                    "name": "web-app",
                    "status": "running",
                    "created_at": "2023-01-01T12:00:00Z"
                }],
                "total": 1,
                "limit": 10,
                "offset": 0,
                "message": "Found 1 workflow(s)"
            }
        }
    )
    
    workflows: List[WorkflowSummary] = Field(..., json_schema={"description": "List of workflows"})
    total: int = Field(..., json_schema={"description": "Total number of workflows"})
    limit: int = Field(..., json_schema={"description": "Maximum number of workflows per page"})
    offset: int = Field(..., json_schema={"description": "Number of workflows skipped"})
    message: str = Field(..., json_schema={"description": "Status message"})
