from sqlalchemy import create_engine, Column, Integer, String, BigInteger, DateTime, Float, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os
from contextlib import contextmanager

from config import config

os.makedirs("data", exist_ok=True)

engine = create_engine(config.DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    balance = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    join_date = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, default=False)

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False)
    payment_id = Column(String, unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    stars_amount = Column(Integer, nullable=False)
    payment_method = Column(String, default="crypto")
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

Base.metadata.create_all(bind=engine)

@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()