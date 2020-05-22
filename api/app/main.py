from typing import List

from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware


from . import crud, models, schemas
from .database import SessionLocal, engine

import time
import logging


# bind models
models.Base.metadata.create_all(bind=engine)


# origins for cors
origins = [
    "*"
]

# init на "боевой машине" LMAO
app = FastAPI()

logger = logging.getLogger("api")

# model for JSONEXCEPTIONS
class UnicornException(Exception):
    def __init__(self):
        pass

class InsufficientRightsException(Exception):
    def __init__(self):
        pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(UnicornException)
async def unicorn_exception_handler(request: Request, exc: UnicornException):
    return JSONResponse(
        status_code=400,
        content={"ErrorCode" : "invalid_request", "Error" :"Invalid Authorization Code"}
    )

@app.exception_handler(InsufficientRightsException)
async def rights_exception_handler(request: Request, exc: InsufficientRightsException):
    return JSONResponse(
        status_code=400,
        content={"ErrorCode" : "invalid_request", "Error" :"Insufficient Access Rights"}
    )

# Dependency
def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

right_get_status_by_iin = "get_status_by_iin"
right_get_status_by_pn = "get_status_by_pn"
right_get_patients_within_interval = "get_patients_within_interval"
get_stats_by_region = "get_stats_by_region"
get_regions = "get_regions"

rights = [right_get_status_by_iin, right_get_status_by_pn, right_get_patients_within_interval, get_stats_by_region, get_regions]

for right_value in rights:
    crud.add_token_right(SessionLocal(), right_value)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    token = None
    try:
        token = request.headers["X-API-TOKEN"]
    except:
        return JSONResponse(content=jsonable_encoder({"ErrorCode" : "invalid_request", "Error" :"The request is missing a required header : X-API-TOKEN"}), status_code=400)
    response = await call_next(request)
    return response

def validate_token(token, db, right):
    db_token = crud.get_token_id_by_token(db, token)
    if db_token is None:
        raise UnicornException()

    if not crud.check_token_right(db, db_token.id, right):
        raise InsufficientRightsException()        

def is_contacted(db, id):
    db_contacted = crud.get_is_contacted(db, id)
    if db_contacted is None:
        return False    
    else:
        return True

@app.post("/api/get_status_by_iin/", response_model=schemas.Patient)
def get_status_by_iin(request: Request, patient: schemas.PatientByIIN, db: Session = Depends(get_db)):
    validate_token(request.headers["X-API-TOKEN"], db, "get_status_by_iin")
    logger.error(request.headers["X-API-TOKEN"][:5])
    logger.error("/api/get_status_by_iin/")
    db_patient = crud.get_patient_by_iin(db, patient.iin)
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    db_patient.is_contacted = is_contacted(db, db_patient.id)
    return db_patient

@app.post("/api/get_status_by_pass_num/", response_model=schemas.Patient)
def get_status_by_pn(request: Request, patient: schemas.PatientByPassNum, db: Session = Depends(get_db)):
    validate_token(request.headers["X-API-TOKEN"], db, "get_status_by_pn")
    logger.error(request.headers["X-API-TOKEN"][:5])
    logger.error("api/get_status_by_pass_num/")
    db_patient = crud.get_patient_by_pass_num(db, patient.pass_num)
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    db_patient.is_contacted = is_contacted(db, db_patient.id)
    return db_patient

@app.post("/api/get_patients_within_interval/", response_model=List[schemas.PatientFrom])
def get_patients_within_interval(request: Request, interval: schemas.Interval, db: Session = Depends(get_db)):
    validate_token(request.headers["X-API-TOKEN"], db, "get_patients_within_interval")
    logger.error(request.headers["X-API-TOKEN"][:5])
    logger.error("/api/get_patients_within_interval/")

    db_patients = crud.get_patients(db, interval.begin, interval.end, interval.page)
    return db_patients

@app.post("/api/get_stats_by_region/", response_model=List[schemas.RegionStatsFrom])
def get_stats_by_region(request: Request, region_id: schemas.RegionId, db: Session = Depends(get_db)):
    validate_token(request.headers["X-API-TOKEN"], db, "get_stats_by_region")
    logger.error(request.headers["X-API-TOKEN"][:5])
    logger.error("/api/get_stats_by_region/")

    db_stats_region = crud.get_region_stats(db, region_id.region_id)
    return db_stats_region

@app.post("/api/get_regions/", response_model=List[schemas.Region])
def get_regions(request: Request, db: Session = Depends(get_db)):
    validate_token(request.headers["X-API-TOKEN"], db, "get_regions")
    logger.error(request.headers["X-API-TOKEN"][:5])
    logger.error("/api/get_regions/")

    db_patients = crud.get_regions(db)
    return db_patients