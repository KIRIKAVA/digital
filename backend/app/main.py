from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import logging
from datetime import datetime
from .database import engine, get_db, Base
from . import models, schemas, crud

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Host Checker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.post("/checks/", response_model=schemas.CheckResponse)
def create_check(check: schemas.CheckCreate, db: Session = Depends(get_db)):
    logger.info(f"Creating check for target: {check.target}")
    db_check = crud.create_check(db=db, check=check)
    return db_check


@app.get("/checks/{check_id}", response_model=schemas.CheckWithResults)
def get_check(check_id: str, db: Session = Depends(get_db)):
    db_check = crud.get_check(db, check_id=check_id)
    if not db_check:
        raise HTTPException(status_code=404, detail="Check not found")
    results = crud.get_check_results(db, check_id)
    check_response = schemas.CheckWithResults(
        id=db_check.id,
        target=db_check.target,
        check_types=db_check.check_types,
        status=db_check.status,
        created_at=db_check.created_at,
        completed_at=db_check.completed_at,
        results=[]
    )
    for result in results:
        agent = db.query(models.Agent).filter(models.Agent.id == result.agent_id).first()
        check_response.results.append(
            schemas.CheckResultResponse(
                id=result.id,
                check_type=result.check_type,
                success=result.success,
                result_data=result.result_data,
                response_time=result.response_time,
                error_message=result.error_message,
                created_at=result.created_at,
                agent_name=agent.name if agent else "Unknown"
            )
        )
    return check_response


@app.get("/checks/", response_model=List[schemas.CheckResponse])
def list_checks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_checks(db, skip=skip, limit=limit)


@app.post("/agents/register", response_model=schemas.AgentResponse)
def register_agent(agent: schemas.AgentCreate, db: Session = Depends(get_db)):
    existing_agent = db.query(models.Agent).filter(models.Agent.name == agent.name).first()
    if existing_agent:
        raise HTTPException(status_code=400, detail="Agent with this name already exists")
    return crud.create_agent(db=db, agent=agent)


@app.post("/agents/{agent_name}/heartbeat")
def agent_heartbeat(agent_name: str, db: Session = Depends(get_db)):
    agent = db.query(models.Agent).filter(models.Agent.name == agent_name).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    crud.update_agent_heartbeat(db, agent.id)
    return {"status": "ok"}


@app.get("/agents/", response_model=List[schemas.AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    return db.query(models.Agent).all()


# ЕДИНСТВЕННЫЙ эндпоинт /results/
@app.post("/results/")
def submit_results(results_data: dict, db: Session = Depends(get_db)):
    """Submit check results from agent"""
    logger.info(f"📥 Received results for check: {results_data.get('check_id')}")
    check_id = results_data.get('check_id')
    agent_name = results_data.get('agent_name')
    results = results_data.get('results', [])
    if not check_id:
        raise HTTPException(status_code=400, detail="Missing check_id")

    db_check = crud.get_check(db, check_id=check_id)
    if not db_check:
        raise HTTPException(status_code=404, detail="Check not found")

    agent = db.query(models.Agent).filter(models.Agent.name == agent_name).first()
    if not agent:
        logger.warning(f"Agent {agent_name} not found, creating temporary agent")
        agent = models.Agent(
            name=agent_name,
            location="unknown",
            token="auto-generated"
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)

    for result in results:
        db_result = models.CheckResult(
            check_id=check_id,
            agent_id=agent.id,
            check_type=result.get('check_type'),
            success=result.get('success', False),
            result_data=result.get('result_data', {}),
            response_time=result.get('response_time'),
            error_message=result.get('error_message')
        )
        db.add(db_result)

    db_check.status = "completed"
    db_check.completed_at = datetime.utcnow()
    db.commit()
    logger.info(f"✅ Results saved for check {check_id}: {len(results)} results from {agent_name}")
    return {"status": "success", "results_saved": len(results)}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "backend"}


@app.get("/")
def root():
    return {"message": "Host Checker API with Database", "version": "1.0.0"}