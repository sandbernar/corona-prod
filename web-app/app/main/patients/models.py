# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

import datetime

from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Date, Boolean, Float, ForeignKey, JSON, DateTime

from app import db
from app import constants as c
from app.login.models import User
from app.main.models import Country, Address, VisitedCountry
from app.login.util import hash_pass


class State(db.Model):
    """
    State class represents Patient state:
    * infected
    * dead
    * healthy
    """

    __tablename__ = 'State'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

class Patient(db.Model):

    __tablename__ = 'Patient'

    id = Column(Integer, primary_key=True)
    created_date = Column(DateTime, default=datetime.datetime.utcnow)

    created_by_id = Column(Integer, ForeignKey('User.id'))
    created_by = db.relationship('User')

    travel_type_id = Column(Integer, ForeignKey('TravelType.id'), nullable=True, default=None)
    travel_type = db.relationship('TravelType')

    travel_id = Column(Integer, nullable=True, default=None, unique=False)

    is_contacted_person = Column(Boolean, unique=False)

    first_name = Column(String, unique=False)
    second_name = Column(String, unique=False)
    patronymic_name = Column(String, unique=False, nullable=True)

    # False - male, True - female, None - unknown
    gender = Column(Boolean, nullable=True, default=None)
    dob = Column(Date, nullable=False)
    iin = Column(String, nullable=True, default=None)

    citizenship_id = Column(Integer, ForeignKey('Country.id'))
    citizenship = db.relationship('Country', foreign_keys=[citizenship_id])

    pass_num = Column(String, unique=False, nullable=True, default=None)

    country_of_residence_id = Column(Integer, ForeignKey('Country.id'), nullable=True)
    country_of_residence = db.relationship('Country', foreign_keys=[country_of_residence_id])

    home_address_id = Column(Integer, ForeignKey('Address.id'), nullable=False)
    home_address = db.relationship('Address', foreign_keys=[
                                   home_address_id], cascade="all,delete", backref="Patient")

    telephone = Column(String, nullable=True, default=None)
    email = Column(String, nullable=True, default=None)

    region_id = Column(Integer, ForeignKey('Region.id'))
    region = db.relationship('Region')

    status_id = Column(Integer, ForeignKey('PatientStatus.id'))
    status = db.relationship('PatientStatus')

    is_found = Column(Boolean, unique=False, default=False)
    is_infected = Column(Boolean, unique=False, default=False)
    is_contacted = Column(Boolean, unique=False, default=False)

    hospital_id = Column(Integer, ForeignKey('Hospital.id'), nullable=True, default=None)
    hospital = db.relationship('Hospital')

    job = Column(String, nullable=True, default=None)
    job_position = Column(String, nullable=True, default=None)
    job_address_id = Column(Integer, ForeignKey('Address.id'), nullable=True, default=None)
    job_address = db.relationship('Address', foreign_keys=[
                                  job_address_id], cascade="all, delete-orphan", single_parent=True)

    attrs = Column(JSON, unique=False)

    # infected, dead, healthy
    states = db.relationship("State", secondary=lambda: PatientState.__table__,
                             backref=db.backref("patients"))

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]

            setattr(self, property, value)

    def __repr__(self):
        return "{} {} {}".format(str(self.second_name), str(self.first_name), str(self.patronymic_name))

    @property
    def serialize(self):
        """Return object data in easily serializable format"""
        color = "green"
        if self.is_infected == True:	
            color = "red"
        return {
            "type": "Feature",
            "id": self.id,
            "geometry": {"type": "Point", "coordinates": [self.home_address.lat, self.home_address.lng]},
            "properties": {
                    "balloonContent": "идет загрузка...",
                    "clusterCaption": "идет загрузка...",
                    # "hintContent": "Текст подсказки"
            },
            "options": {
                "preset": "islands#icon",
                "iconColor": color
            }
        }

    def get_created_date(self):
        sql = "select * from logging.t_history WHERE tabname='{}' \
                AND new_val->>'id'='{}' AND operation='INSERT';".format(self.__tablename__, self.id)
        result = db.engine.execute(sql)
        created_date = result.fetchone()[1]

        return created_date


class PatientState(db.Model):
    """
    PatientState represents many-to-many relationship between Patient and State tables.
    Table includes:
    * created_at: creation datetime
    * detection_date: datetime of detection
    * comment: comment on state
    """
    __tablename__ = 'PatientState'

    state_id = Column(Integer, ForeignKey('State.id'), primary_key=True)
    patient_id = Column(Integer, ForeignKey('Patient.id'), primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    patient = db.relationship('Patient')
    state = db.relationship('State')
    detection_date = Column(DateTime, nullable=False)
    comment = Column(String, nullable=True)


class ContactedPersons(db.Model):
    __tablename__ = 'ContactedPersons'

    id = Column(Integer, primary_key=True)

    infected_patient_id = Column(Integer, ForeignKey('Patient.id', ondelete="CASCADE"))
    infected_patient = db.relationship('Patient', foreign_keys=[infected_patient_id],
                                       backref=db.backref('infected_patient', passive_deletes=True))

    contacted_patient_id = Column(Integer, ForeignKey('Patient.id'))
    contacted_patient = db.relationship('Patient', foreign_keys=[contacted_patient_id])

    attrs = Column(JSON, unique=False)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]

            setattr(self, property, value)

    def __repr__(self):
        return str(self.id)

    @property
    def created_date(self):
        sql = "select * from logging.t_history WHERE tabname='ContactedPersons' \
                AND new_val->>'id'='{}' AND operation='INSERT';".format(self.id)
        result = db.engine.execute(sql)
        created_date = result.fetchone()[1]

        return created_date

    def added_in_n_hours(self, hours = 2):
        infected_created_date = self.infected_patient.get_created_date()

        return self.created_date - infected_created_date < datetime.timedelta(hours=hours)

class PatientStatus(db.Model):

    __tablename__ = 'PatientStatus'

    id = Column(Integer, primary_key=True)
    value = Column(String, unique=True)
    name = Column(String, unique=True)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]

            setattr(self, property, value)

    def __repr__(self):
        return str(self.name)
