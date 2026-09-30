from typing import Optional
from pydantic import BaseModel


class CreateCaseRequest(BaseModel):
    title: str
    is_demo: bool = False


class TriggerWorkflowRequest(BaseModel):
    workflow_type: str
    trigger_type: str
    trigger_source_engine: Optional[str] = None
    trigger_event_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class ApprovalDecisionRequest(BaseModel):
    approve: bool
    reason: str = ""


class VerifyTaskRequest(BaseModel):
    passed: bool
    reason: str = ""


class CompleteTaskRequest(BaseModel):
    output: Optional[str] = None


class FailTaskRequest(BaseModel):
    reason: str
