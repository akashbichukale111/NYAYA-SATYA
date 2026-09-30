"""Load the synthetic demo cases (Section 57) into the database."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sqlmodel import Session

from app.database import engine, init_db
from app.models import Case, CaseEvent, CaseDocument, Dependency, Transition
from app.demo_data import ALL_DEMO_CASES
from app.security import scan_for_injection, hash_content


def seed(fresh: bool = True):
    init_db(fresh=fresh)
    with Session(engine) as session:
        for builder in ALL_DEMO_CASES:
            data = builder()
            session.add(Case(**data["case"]))
            for ev in data["events"]:
                session.add(CaseEvent(**ev))
            for doc in data["documents"]:
                injected = scan_for_injection(doc["content_text"])
                session.add(CaseDocument(
                    **doc,
                    contains_injection_attempt=injected,
                    quarantined=injected,
                    sha256=hash_content(doc["content_text"]),
                ))
            for dep in data["dependencies"]:
                session.add(Dependency(**dep))
            for t in data["transitions"]:
                session.add(Transition(**t))
        session.commit()
    print(f"Seeded {len(ALL_DEMO_CASES)} demo cases.")


if __name__ == "__main__":
    seed(fresh=True)
