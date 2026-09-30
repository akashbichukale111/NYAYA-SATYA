from pydantic import BaseModel


class RejectRequest(BaseModel):
    reason: str


class SimulateRequest(BaseModel):
    dependency_id: str


class CrashTestRequest(BaseModel):
    mutation: str
    target_dependency_id: str | None = None
