import os
from sqlmodel import SQLModel, create_engine, Session

DB_PATH = os.environ.get("CBE_DB_PATH", "case_bottleneck_engine.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def init_db(fresh: bool = False) -> None:
    if fresh and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    SQLModel.metadata.create_all(engine)


def get_session():
    # expire_on_commit=False: several endpoints (e.g. actions/{id}/approve)
    # commit more than once within a single request (action commit, then
    # audit.record()'s own commit, then reassessment). SQLAlchemy's default
    # expire_on_commit=True clears the ORM instance's __dict__ after each
    # commit; SQLModel's JSON serialization reads __dict__ directly rather
    # than lazy-reloading, so a since-expired object silently serializes to
    # `{}` (found via API testing: /actions/{id}/reject and /approve both
    # exhibited this). Disabling expire-on-commit keeps returned objects
    # populated with the values this request itself just wrote, which is
    # exactly what every caller here actually wants.
    with Session(engine, expire_on_commit=False) as session:
        yield session
