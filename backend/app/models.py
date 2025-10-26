from sqlalchemy import Column, String, DateTime, Boolean, JSON, Integer, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False)
    location = Column(String)
    token = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    last_heartbeat = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связь с проверками
    results = relationship("CheckResult", back_populates="agent")

class Check(Base):
    __tablename__ = "checks"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    target = Column(String, nullable=False)
    check_types = Column(JSON)  # Список типов проверок
    status = Column(String, default="pending")  # pending, running, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Связь с результатами
    results = relationship("CheckResult", back_populates="check")

class CheckResult(Base):
    __tablename__ = "check_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    check_id = Column(String, ForeignKey("checks.id"))
    agent_id = Column(String, ForeignKey("agents.id"))
    check_type = Column(String, nullable=False)  # ping, http, etc.
    success = Column(Boolean)
    result_data = Column(JSON)  # Результаты проверки
    response_time = Column(Integer)  # Время ответа в ms
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    check = relationship("Check", back_populates="results")
    agent = relationship("Agent", back_populates="results")