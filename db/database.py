from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///MasterArbeit_1.db", connect_args={"check_same_thread": False})
Base = declarative_base()

sessionLocal = sessionmaker(bind=engine)


def get_db():
    session = sessionLocal()
    try:
        yield session
    finally:
        session.close()