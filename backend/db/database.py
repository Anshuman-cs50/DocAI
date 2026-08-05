# db/database.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Define base class for models
Base = declarative_base()

# SQLite by default (you can replace with PostgreSQL URI later)
# Load from environment variable (for Render/Supabase) or fallback to local Docker connection
DB_URI = os.getenv("DATABASE_URL", "postgresql://admin:0987654321@localhost:5432/DocAI")

"""
docker command to run db on powershell: 
docker exec -it postgres_ts_vector psql -U admin -d DocAI
"""

# Create the engine
engine = create_engine(DB_URI)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes the database, enables pgvector, and creates all tables."""
    from . import models  # import models here to register them

    try:
        # 1. Connect and ENABLE the pgvector EXTENSION
        # This must happen before creating tables that rely on it.
        with engine.connect() as connection:
            try:
                # Use an isolation level that allows DDL commands (like CREATE EXTENSION)
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                connection.commit() # Commit the extension creation
            except Exception as e:
                print(f"[WARNING] Warning: Could not enable pgvector extension: {e}")

        # 2. Create all tables defined in models.py
        Base.metadata.create_all(bind=engine)
        
        print("[OK] Database initialized and tables created (pgvector enabled).")
    except Exception as e:
        print(f"[ERROR] Error: Could not connect to PostgreSQL. Please ensure the database is running on localhost:5432.")
        raise

def get_session():
    """Yields a new database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

