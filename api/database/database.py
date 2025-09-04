import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables from .env file
load_dotenv()

# Get DATABASE_URL from environment variables (required)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required but not set")

# Convert sync postgresql:// to async postgresql+asyncpg:// for Railway compatibility
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    print(f"🔄 Converted DATABASE_URL to async driver: postgresql+asyncpg://...")
elif DATABASE_URL.startswith("postgresql+asyncpg://"):
    print(f"✅ Using async DATABASE_URL: postgresql+asyncpg://...")

# FASTAPI ENGINE: Optimized for web requests
engine = create_async_engine(
    DATABASE_URL,
    # FastAPI-optimized connection pool settings
    pool_size=10,                    # Moderate pool for trading bot requests
    max_overflow=20,                 # Allow overflow for occasional spikes
    pool_timeout=30,                 # Timeout for getting connection
    pool_recycle=3600,              # Recycle connections after 1 hour
    pool_pre_ping=True,             # Validate connections before use
    pool_reset_on_return='commit',   # Reset connection state on return
    echo=False,                     # Set to True for SQL debugging
    future=True,                    # Use SQLAlchemy 2.0 style
)

AsyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session 