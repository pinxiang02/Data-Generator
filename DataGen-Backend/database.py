from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Connection string for your specific Postgres Docker setup
# user: pinxiang | pass: pinxiang | db: pinxiang_database
SQLALCHEMY_DATABASE_URL = "postgresql+pg8000://pinxiang:pinxiang@localhost:5432/pinxiang_database"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()