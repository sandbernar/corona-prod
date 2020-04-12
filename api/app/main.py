from typing import List

from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from . import crud, models, schemas
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

import time
import logging

app = FastAPI()

logger = logging.getLogger("api")

class UnicornException(Exception):
    def __init__(self):
        pass

@app.exception_handler(UnicornException)
async def unicorn_exception_handler(request: Request, exc: UnicornException):
    return JSONResponse(
        status_code=400,
        content={"ErrorCode" : "invalid_request", "Error" :"Invalid Authorization Code"}
    )

# Dependency
def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    token = None
    try:
        token = request.headers["X-API-TOKEN"]
    except:
        return JSONResponse(content=jsonable_encoder({"ErrorCode" : "invalid_request", "Error" :"The request is missing a required header : X-API-TOKEN"}), status_code=400)
    response = await call_next(request)
    return response

def validate_token(token, db):
    db_token = crud.get_token_id_by_token(db, token)
    if db_token is None:
        raise UnicornException()

def is_contacted(db, id):
    db_contacted = crud.get_is_contacted(db, id)
    if db_contacted is None:
        return False    
    else:
        return True

@app.post("/get_status_by_iin/", response_model=schemas.Patient)
def get_status_by_iin(request: Request, patient: schemas.PatientByIIN, db: Session = Depends(get_db)):
    validate_token(request.headers["X-API-TOKEN"], db)
    db_patient = crud.get_patient_by_iin(db, patient.iin)
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    db_patient.is_contacted = is_contacted(db, db_patient.id)
    return db_patient

@app.post("/get_status_by_pass_num/", response_model=schemas.Patient)
def get_status_by_pn(request: Request, patient: schemas.PatientByPassNum, db: Session = Depends(get_db)):
    validate_token(request.headers["X-API-TOKEN"], db)
    db_patient = crud.get_patient_by_pass_num(db, patient.pass_num)
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    db_patient.is_contacted = is_contacted(db, db_patient.id)
    return db_patient