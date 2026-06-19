from sqlmodel import Session, create_engine, select, SQLModel
from sqlalchemy import text

from app import crud
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate

engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    echo= settings.DEBUG, #Log SQL queries if in debug mode
    pool_pre_ping= True, # Verify connections before using them
    pool_size= 5, # Default connection pool size
    max_overflow= 10, # Max overflow connections    
    )


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28
from app import models

def create_tables() -> None:
    """Create all database tables if they don't exist.
    This is useful for development/testing but in production you should use Alembic migrations."""
    
    print("📦 Creating database tables...")
    SQLModel.metadata.create_all(engine)
    print("✅ Database tables created successfully!")


def drop_tables() -> None:
    """
    Drop all database tables.
    USE WITH CAUTION - This will delete all data!
    """
    print("⚠️  Dropping all database tables...")
    SQLModel.metadata.drop_all(engine)
    print("✅ All tables dropped!")


def init_db(session: Session) -> None:
    """
    Initialize the database with:
      1. Create tables if they don't exist (development only)
      2. Create the first superuser if it doesn't exist
    """
    # Create tables if they don't exist
    # In production, you should use Alembic migrations instead
    if settings.ENVIRONMENT == "local" or settings.ENVIRONMENT == "staging":
        create_tables()
    
    # Check if database has tables (optional check)
    try:
        # Test if user table exists
        session.exec(text("SELECT 1 FROM user LIMIT 1")).first()
    except Exception:
        # Table doesn't exist, create it
        create_tables()

    # Create superuser
    _create_superuser(session)


def _create_superuser(session:Session) -> None:
    """
    Create the first superuser if it doesn't exist.
    """
    if not settings.FIRST_SUPERUSER:
        print("⚠️  No FIRST_SUPERUSER configured, skipping superuser creation")
        return
    
    # Check if superuser already exists
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()

    if not user:
        print(f"👤 Creating superuser: {settings.FIRST_SUPERUSER}")
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
            is_active=True,
        )
        user = crud.create_user(session=session, user_create=user_in)
        print("✅ Superuser created successfully!")
    else:
        print(f"✅ Superuser already exists: {settings.FIRST_SUPERUSER}")
    
    return user

def get_session():
    with Session(engine) as session:
        yield session

# ----- For testing and standalone use -----------

# Convenience function for quick testing
def reset_database() -> None:
    """
    Reset the database: drop all tables and recreate them.
    USE WITH CAUTION - This will delete all data!
    """
    print("🔄 Resetting database...")
    drop_tables()
    create_tables()
    
    # Initialize with superuser
    with Session(engine) as session:
        init_db(session)
    
    print("✅ Database reset complete!")


# For standalone execution: python -m app.core.db
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        reset_database()
    elif len(sys.argv) > 1 and sys.argv[1] == "drop":
        drop_tables()
    else:
        # Default: create tables and init
        with Session(engine) as session:
            init_db(session)
        print("✅ Database initialization complete!")