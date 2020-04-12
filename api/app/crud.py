from sqlalchemy.orm import Session

from . import models, schemas

def get_patient_by_iin(db: Session, iin: str):
    return db.query(models.Patient).filter(models.Patient.iin == iin).first()

def get_patient_by_pass_num(db: Session, pass_num: str):
    return db.query(models.Patient).filter(models.Patient.pass_num == pass_num).first()

def get_token_id_by_token(db: Session, token: str):
    return db.query(models.Token).filter(models.Token.token == token).first()

def get_is_contacted(db: Session, id: int):
    return db.query(models.ContactedPersons).filter(models.ContactedPersons.contacted_patient_id == id).first()