"""Database connection and setup."""
from sqlmodel import SQLModel, create_engine, Session

engine = create_engine("sqlite:///database.db")

def get_session():
    """Provide a database session."""
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    """Create database tables."""
    SQLModel.metadata.create_all(engine)
