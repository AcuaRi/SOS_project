from sqlalchemy import Column, BigInteger, String, TIMESTAMP, func
from sqlalchemy.orm import relationship
# 기존 Yun/db.py에서 정의된 Base를 import 합니다.
from Yun.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    # 필요한 경우 다른 관계를 여기에 정의할 수 있습니다.
    # 예: items = relationship("Item", back_populates="owner")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
    
class sos_friends(Base):
    __tablename__="sos_friends"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(100), unique=True, nullable=False)
    
    def __repr__(self):
        return f"<sos_friends(id={self.id}, email='{self.email}')>"