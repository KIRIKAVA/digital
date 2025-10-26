from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime

# CRUD для проверок
def create_check(db: Session, check: schemas.CheckCreate):
    db_check = models.Check(
        target=check.target,
        check_types=[ct.value for ct in check.check_types]
    )
    db.add(db_check)
    db.commit()
    db.refresh(db_check)
    return db_check

def get_check(db: Session, check_id: str):
    return db.query(models.Check).filter(models.Check.id == check_id).first()

def get_checks(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Check).offset(skip).limit(limit).all()

# CRUD для агентов
def create_agent(db: Session, agent: schemas.AgentCreate):
    db_agent = models.Agent(
        name=agent.name,
        location=agent.location,
        token=agent.token
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

def get_agent_by_token(db: Session, token: str):
    return db.query(models.Agent).filter(models.Agent.token == token).first()

def get_active_agents(db: Session):
    return db.query(models.Agent).filter(models.Agent.is_active == True).all()

def update_agent_heartbeat(db: Session, agent_id: str):
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if agent:
        agent.last_heartbeat = datetime.utcnow()
        db.commit()
    return agent

# CRUD для результатов
def create_check_result(db: Session, result_data: dict):
    db_result = models.CheckResult(**result_data)
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

def get_check_results(db: Session, check_id: str):
    return db.query(models.CheckResult).filter(models.CheckResult.check_id == check_id).all()
def get_checks(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Check).order_by(models.Check.created_at.desc()).offset(skip).limit(limit).all()