from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ToolError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ToolResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "error"]
    data: dict[str, Any] | None = None
    error: ToolError | None = None

    @classmethod
    def success(cls, **data: Any) -> "ToolResponse":
        return cls(status="ok", data=data)

    @classmethod
    def failure(cls, code: str, message: str, **details: Any) -> "ToolResponse":
        return cls(status="error", error=ToolError(code=code, message=message, details=details))
