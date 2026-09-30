import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./uls.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

# check_same_thread only needed for sqlite
connect_args = {"check_same_thread": False} if IS_SQLITE else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

if IS_SQLITE:
    # pysqlite's default driver-level transaction handling conflicts with
    # SQLAlchemy's SAVEPOINT (nested transaction) support, which this
    # system relies on for Simulation and Crash Test (see
    # app/agents/simulation.py) to guarantee production data is never
    # mutated by a what-if run. Without these two listeners, begin_nested()
    # can raise "This transaction is closed" or, worse, fail to roll back
    # cleanly. This is the standard SQLAlchemy-recommended fix.
    @event.listens_for(engine, "connect")
    def _sqlite_disable_pysqlite_transaction_handling(dbapi_connection, connection_record):
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _sqlite_emit_explicit_begin(conn):
        conn.exec_driver_sql("BEGIN")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Import models so they register on Base.metadata before create_all
    from app.models import orm  # noqa: F401
    Base.metadata.create_all(bind=engine)
