"""
Duplicate Engine.

Detects exact/hash duplicates using SHA-256 (computed at ingestion time
in app.services.parsing) and flags possible content duplicates using a
conservative text-similarity heuristic. Never deletes or auto-merges
anything — always produces a DuplicateGroup for human review.
"""
import difflib
from sqlalchemy.orm import Session
from app import models
from app.core.ids import new_id, utcnow
from app.core.enums import DuplicateType

CONTENT_SIMILARITY_THRESHOLD = 0.92


def detect_duplicates(db: Session, *, case_id: str, filing_package_id: str) -> list[models.DuplicateGroup]:
    versions = (
        db.query(models.DocumentVersion)
        .join(models.Document, models.DocumentVersion.document_id == models.Document.id)
        .filter(
            models.DocumentVersion.case_id == case_id,
            models.Document.filing_package_id == filing_package_id,
            models.DocumentVersion.extraction_status == "OK",
        )
        .all()
    )

    groups = []
    seen_ids = set()

    # 1. Exact hash duplicates.
    by_hash: dict[str, list[models.DocumentVersion]] = {}
    for v in versions:
        if v.sha256:
            by_hash.setdefault(v.sha256, []).append(v)

    for digest, group_versions in by_hash.items():
        if len(group_versions) > 1:
            ids = [v.id for v in group_versions]
            group = models.DuplicateGroup(
                id=new_id("dupg"), case_id=case_id, filing_package_id=filing_package_id,
                duplicate_type=DuplicateType.HASH_DUPLICATE.value,
                member_document_version_ids=ids,
                similarity_evidence=f"Identical SHA-256 hash: {digest}",
                created_at=utcnow().isoformat(),
            )
            db.add(group)
            groups.append(group)
            seen_ids.update(ids)

    # 2. Possible content duplicates among remaining versions (different
    # hash, but near-identical extracted text — e.g. re-saved/re-exported
    # copies).
    remaining = [v for v in versions if v.id not in seen_ids and v.extracted_text]
    compared = set()
    for i in range(len(remaining)):
        for j in range(i + 1, len(remaining)):
            a, b = remaining[i], remaining[j]
            pair_key = tuple(sorted([a.id, b.id]))
            if pair_key in compared:
                continue
            compared.add(pair_key)
            ratio = difflib.SequenceMatcher(
                None, a.extracted_text[:5000], b.extracted_text[:5000]
            ).ratio()
            if ratio >= CONTENT_SIMILARITY_THRESHOLD:
                group = models.DuplicateGroup(
                    id=new_id("dupg"), case_id=case_id, filing_package_id=filing_package_id,
                    duplicate_type=DuplicateType.POSSIBLE_CONTENT_DUPLICATE.value,
                    member_document_version_ids=[a.id, b.id],
                    similarity_evidence=f"Text similarity ratio {ratio:.3f} (threshold {CONTENT_SIMILARITY_THRESHOLD})",
                    created_at=utcnow().isoformat(),
                )
                db.add(group)
                groups.append(group)

    db.commit()
    for g in groups:
        db.refresh(g)
    return groups
