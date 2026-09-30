"""
Metadata Consistency Engine.

Compares user-declared or extracted metadata fields (case number, party
names, dates, reference numbers) across every document in a filing
package. When two documents disagree on the same field, a Conflict
record is created. The engine explicitly does NOT decide which value is
correct — that is a human-review decision (see ReviewTask).
"""
from sqlalchemy.orm import Session
from app import models
from app.core.ids import new_id, utcnow

COMPARABLE_FIELDS = {
    "case_number", "party_name", "document_date", "order_date",
    "filing_date", "reference_number",
}


def detect_metadata_conflicts(db: Session, *, case_id: str, filing_package_id: str) -> list[models.Conflict]:
    entries = (
        db.query(models.DocumentMetadata)
        .join(models.DocumentVersion, models.DocumentMetadata.document_version_id == models.DocumentVersion.id)
        .join(models.Document, models.DocumentVersion.document_id == models.Document.id)
        .filter(
            models.DocumentMetadata.case_id == case_id,
            models.Document.filing_package_id == filing_package_id,
            models.Document.status == "ACTIVE",
        )
        .all()
    )

    by_field: dict[str, list[models.DocumentMetadata]] = {}
    for entry in entries:
        if entry.field_name not in COMPARABLE_FIELDS:
            continue
        by_field.setdefault(entry.field_name, []).append(entry)

    conflicts = []
    for field_name, field_entries in by_field.items():
        values_seen = {}
        for entry in field_entries:
            norm = (entry.field_value or "").strip().lower()
            if not norm:
                continue
            values_seen.setdefault(norm, []).append(entry)

        if len(values_seen) > 1:
            distinct_entries = [v[0] for v in values_seen.values()]
            for i in range(len(distinct_entries)):
                for j in range(i + 1, len(distinct_entries)):
                    left, right = distinct_entries[i], distinct_entries[j]
                    conflict = models.Conflict(
                        id=new_id("conf"),
                        case_id=case_id,
                        filing_package_id=filing_package_id,
                        conflict_type="METADATA_CONFLICT",
                        field_name=field_name,
                        left_document_version_id=left.document_version_id,
                        left_value=left.field_value,
                        right_document_version_id=right.document_version_id,
                        right_value=right.field_value,
                        status="UNRESOLVED",
                        created_at=utcnow().isoformat(),
                    )
                    db.add(conflict)
                    conflicts.append(conflict)
    db.commit()
    for c in conflicts:
        db.refresh(c)
    return conflicts
