from pydantic import BaseModel, ConfigDict


class ApiRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApiResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
