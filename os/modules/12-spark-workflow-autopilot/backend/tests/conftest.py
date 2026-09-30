import os
import tempfile
import pytest

os.environ["SPARK_DB_PATH"] = tempfile.mktemp(suffix=".db")

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.models.models import Case  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def case(db):
    c = Case(title="Test Case", is_demo=True)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c
