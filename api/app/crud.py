from sqlalchemy.orm import Session
from datetime import date
from sqlalchemy import exc

from . import models, schemas
import logging
logger = logging.getLogger("api")

def get_patient_by_iin(db: Session, iin: str):
    return db.query(models.Patient).filter(models.Patient.iin == iin).first()

def get_patient_by_pass_num(db: Session, pass_num: str):
    return db.query(models.Patient).filter(models.Patient.pass_num == pass_num).first()

def get_token_id_by_token(db: Session, token: str):
    return db.query(models.Token).filter(models.Token.token == token).first()

def get_is_contacted(db: Session, id: int):
    return db.query(models.ContactedPersons).filter(models.ContactedPersons.contacted_patient_id == id).first()

def get_patients(db: Session, begin: date, end: date):
    flight = None
    try:
        flight = db.query(models.FlightTravel).join(models.Patient, models.FlightTravel.patient_id == models.Patient.id).filter(models.Patient.created_date >= begin).filter(models.Patient.created_date <= end).all()
    except exc.SQLAlchemyError as err:
        logger.error(err)
    
    train = None
    try:
        train = db.query(models.TrainTravel).join(models.Patient, models.TrainTravel.patient_id == models.Patient.id).filter(models.Patient.created_date >= begin).filter(models.Patient.created_date <= end).all()
    except exc.SQLAlchemyError as err:
        logger.error(err)
    
    other = None
    try:
        other = db.query(models.VisitedCountry).join(models.Patient, models.VisitedCountry.patient_id == models.Patient.id).filter(models.Patient.travel_type_id != 1).filter(models.Patient.travel_type_id != 2).filter(models.Patient.created_date >= begin).filter(models.Patient.created_date <= end).all()
    except exc.SQLAlchemyError as err:
        logger.error(err)

    data = []
    for a in flight:
        if (a.flight_code == None or a.flight_code.from_country == None):
            continue
        data.append({
            "from_country": a.flight_code.from_country.name,
            "to_region": a.flight_code.to_city,
            "patient": a.patient
        })
    for a in train:
        if a.train == None or a.train.from_country == None:
            continue
        data.append({
            "from_country": a.train.from_country.name,
            "to_region": a.train.to_city,
            "patient": a.patient
        })
    for a in other:
        if a.country == None:
            continue
        data.append({
            "from_country": a.country.name,
            "to_region": "Kazakhstan",
            "patient": a.patient
        })
    
    return data