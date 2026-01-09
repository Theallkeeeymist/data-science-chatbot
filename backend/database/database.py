import sys

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from chatbot.components.exception.exception import ChatbotException
from chatbot.components.src_logging.logger import logging

# Creating a file {interview_app.db}
SQLALCHEMY_DATABASE_URL = "sqlite:///./interview_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

session_local = sessionmaker(autocommit = False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = session_local()
    try:
        yield db
        logging.info("db yielded.")
    finally:
        db.close
        logging.info("db finally executed and closed")