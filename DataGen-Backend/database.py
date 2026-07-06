import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# App metadata database (users, generators, nodes, destination configs).
# Defaults to the local Docker Postgres on :5436; override with DATABASE_URL
# so the containerized backend can reach the "postgres" service by name.
# user: pinxiang | pass: pinxiang | db: pinxiang_database
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+pg8000://pinxiang:pinxiang@localhost:5436/pinxiang_database",
)

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()