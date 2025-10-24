# db/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Define base class for models
Base = declarative_base()

# SQLite by default (you can replace with PostgreSQL URI later)
DB_URL = os.getenv("DATABASE_URI")
# DB_URL = "postgresql://admin:0987654321@localhost:5432/DocAI"


# Create the engine
engine = create_engine(DB_URL)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes the database and creates all tables."""
    from db import models  # import models here to register them
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized and tables created.")

def get_session():
    """Yields a new database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

