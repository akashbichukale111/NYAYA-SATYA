"""Procedural Obligation Engine - Core Domain Models & Schemas
Grounded in UNWIND settle/obligation.py framework:
Enforces WHO / WHAT / LOSS / SIGN structure.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ObligationStatus(str, Enum):
    AWAITING_AUTHORISATION = "AWAITING_AUTHORISATION"
    AUTHORISED = "AUTHORISED"
    DISPATCHED = "DISPATCHED"
    SUPERSEDED = "SUPERSEDED"
    CANCELLED = "CANCELLED"


class Reversibility(str, Enum):
    REVERSIBLE = "REVERSIBLE"
    IRREVERSIBLE = "IRREVERSIBLE"
    PARTIAL = "PARTIAL"


class CounterpartyNotice(BaseModel):
    counterparty: str
    told_claim: str
    told_at: str
    channel: str
    remedial_correction_required: str


class IrreversibleLossExposure(BaseModel):
    min_exposure_inr: float
    max_exposure_inr: float
    unstated_assumptions: List[str]
    qualitative_impact: str


class ObligationRecord(BaseModel):
    obligation_id: str
    case_id: str
    title: str
    status: ObligationStatus = ObligationStatus.AWAITING_AUTHORISATION
    counterparties: List[CounterpartyNotice]
    reversible_actions: List[str]
    irreversible_loss: IrreversibleLossExposure
    approver: Optional[str] = None
    signed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ruling_basis: str


class SignObligationRequest(BaseModel):
    approver_name: str
    bar_council_id: str
    authorization_token: Optional[str] = None
