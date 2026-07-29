from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class StandardResponse(BaseModel, Generic[T]):
    status: str = "success"
    success: bool = True
    message: str | None = None
    data: T | None = None
    status_code: int = 200

class ErrorResponse(BaseModel):
    status: str = "error"
    success: bool = False
    message: str
    detail: Any | None = None
    status_code: int = 400
