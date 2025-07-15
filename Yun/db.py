from sqlalchemy import (
    create_engine, Column, BigInteger, String, SmallInteger,
    DECIMAL, Enum, JSON, TIMESTAMP, func
)
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os, enum

load_dotenv()                                           # .env 읽기
engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Risk(enum.Enum):
    낮음 = "낮음"; 중간 = "중간"; 높음 = "높음"; 심각 = "심각"; 알수 = "알수"

class SymLog(Base):
    __tablename__ = "sym_log"
    id    = Column(BigInteger, primary_key=True, autoincrement=True)
    uid   = Column(BigInteger, nullable=False)
    sym   = Column(String(200))
    dis   = Column(String(200))
    risk  = Column(Enum(Risk))
    dcode = Column(SmallInteger)
    dname = Column(String(40))
    lat   = Column(DECIMAL(9, 6))
    lng   = Column(DECIMAL(9, 6))
    raw   = Column(JSON)
    c_at  = Column(TIMESTAMP, server_default=func.current_timestamp())
