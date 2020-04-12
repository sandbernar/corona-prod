from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from os import getenv

SQLALCHEMY_DATABASE_URL = "postgresql://%s:%s@%s:%s/%s" % (getenv("DATABASE_USER"), getenv("DATABASE_PASSWORD"), getenv("DATABASE_HOST"), getenv("DATABASE_PORT"), getenv("DATABASE_NAME"))

engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()