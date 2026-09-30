"""Base Module Adapter for NYAYA-SATYA OS.
Provides common contract and utilities for module integration.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from fastapi import APIRouter
from contracts.models import ModuleMetadata, AttentionItem


class BaseModuleAdapter(ABC):
    def __init__(self, metadata: ModuleMetadata):
        self.metadata = metadata
        self.router = APIRouter(prefix=metadata.api_prefix, tags=[metadata.name])
        self._register_routes()

    @abstractmethod
    def _register_routes(self):
        """Register specific module endpoints onto self.router."""
        pass

    @abstractmethod
    def get_summary(self, case_id: str) -> Dict[str, Any]:
        """Return executive metric card summary for the OS Command Center."""
        pass

    def get_attention_items(self, case_id: str) -> List[AttentionItem]:
        """Return any active attention / alert items for this module."""
        return []
