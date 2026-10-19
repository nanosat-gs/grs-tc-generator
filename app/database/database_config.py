from flask_sqlalchemy.session import Session
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm import DeclarativeBase

#Base = declarative_base()
class Base(DeclarativeBase):
    pass

class DatabaseConfig:
    """Base configuration class for database connections"""

    def __init__(self, db_url: str, **kwargs):
        self.db_url = db_url
        self.engine = None
        self.session_factory = None
        self.kwargs = kwargs

    def create_engine(self) -> Engine:
        """Create and return a database engine"""
        raise NotImplementedError("Subclasses must implement this method")

    def create_session(self) -> Session:
        """Create and return a new session"""
        if not self.engine:
            self.engine = self.create_engine()

        if not self.session_factory:
            self.session_factory = scoped_session(
                sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            )
            Base.metadata.create_all(bind=self.engine)
            # create_all never alters an existing table: the status CHECK
            # grew with the uplink slice and is replaced here when needed.
            from app.database.migrations import ensure_status_constraint
            ensure_status_constraint(self.engine)

        return self.session_factory()
