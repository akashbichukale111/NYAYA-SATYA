"""NYAYA-SATYA Judicial Review Dossier Subsystem (Phase 6 & Phase 7).

Compiles 24-section auditable review packages for Human Legal Gate authority,
with full versioning, structural diffing, and dedicated human review checklists.
"""

from nyaya_dossier.dossier_builder import DossierBuilder
from nyaya_dossier.dossier_diff import DossierComparator, DossierDiff, SectionDiff
from nyaya_dossier.dossier_model import (
    DossierEntry,
    DossierItemCategory,
    JudicialReviewDossier,
)
from nyaya_dossier.dossier_version import DossierVersionRecord, DossierVersionStore
from nyaya_dossier.export_formatter import DossierFormatter
from nyaya_dossier.human_checklist import (
    HumanReviewChecklist,
    ReviewItem,
    ReviewSeverity,
    ReviewStatus,
)

__all__ = [
    "DossierBuilder",
    "DossierComparator",
    "DossierDiff",
    "DossierEntry",
    "DossierFormatter",
    "DossierItemCategory",
    "DossierVersionRecord",
    "DossierVersionStore",
    "HumanReviewChecklist",
    "JudicialReviewDossier",
    "ReviewItem",
    "ReviewSeverity",
    "ReviewStatus",
    "SectionDiff",
]
