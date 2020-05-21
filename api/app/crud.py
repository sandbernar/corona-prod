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

def get_token_right(db: Session, right_value: str):
	token_right = db.query(models.TokenRights).filter(models.TokenRights.right_value == right_value)
	
	if token_right.count():
		return token_right.first()

	return None

def add_token_right(db: Session, right_value: str):
	token_right = db.query(models.TokenRights).filter(models.TokenRights.right_value == right_value)

	if not token_right.count():
		token_right = models.TokenRights()
		token_right.right_value = right_value

		db.add(token_right)
		db.commit()
		
		return True

	return False

def get_region_stats(db: Session, region_id: int):
	try:
		region = db.query(models.Region).filter(models.Region.id == region_id).first()
	except exc.SQLAlchemyError as err:
		logger.error(err)

	patient_query = db.query(models.Patient).filter(models.Patient.region_id == region.id)
	infected_state_id = db.query(models.State).filter(models.State.value == "infected").first().id

	infected_patient_count = patient_query.join(models.PatientState, models.PatientState.patient_id == models.Patient.id)
	infected_patient_count = infected_patient_count.filter(models.PatientState.state_id == infected_state_id)
	infected_patient_count = infected_patient_count.group_by(models.Patient.id).count()

	contacted_patient_count = patient_query.join(models.ContactedPersons, models.ContactedPersons.contacted_patient_id == models.Patient.id)
	contacted_patient_count = contacted_patient_count.count()

	response = {"region": str(region.name), "id": region.id}
	response["stats"] = {"infected": infected_patient_count, "contacted": contacted_patient_count}

	return [response]

def get_regions(db: Session):
    return [{"name": region.name, "id": region.id } for region in db.query(models.Region).all()]

def get_is_contacted(db: Session, id: int):
    return db.query(models.ContactedPersons).filter(models.ContactedPersons.contacted_patient_id == id).first()

def get_patients(db: Session, begin: date, end: date, page: int):
    flight = None
    try:
        flight = db.query(models.FlightTravel).join(models.Patient, models.FlightTravel.patient_id == models.Patient.id).filter(models.Patient.created_date >= begin).filter(models.Patient.created_date <= end).order_by(models.Patient.id).limit(100).offset(100 * (page - 1)).all()
    except exc.SQLAlchemyError as err:
        logger.error(err)
    
    train = None
    try:
        train = db.query(models.TrainTravel).join(models.Patient, models.TrainTravel.patient_id == models.Patient.id).filter(models.Patient.created_date >= begin).filter(models.Patient.created_date <= end).order_by(models.Patient.id).limit(100).offset(100 * (page - 1)).all()
    except exc.SQLAlchemyError as err:
        logger.error(err)
    
    other = None
    try:
        other = db.query(models.VisitedCountry).join(models.Patient, models.VisitedCountry.patient_id == models.Patient.id).filter(models.Patient.travel_type_id != 1).filter(models.Patient.travel_type_id != 2).filter(models.Patient.created_date >= begin).filter(models.Patient.created_date <= end).order_by(models.Patient.id).limit(100).offset(100 * (page - 1)).all()
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