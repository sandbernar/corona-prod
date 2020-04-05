# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Date, Boolean, Float, ForeignKey, JSON, DateTime
import datetime

from app import db
from app import constants as c

from app.login.models import User
from app.main.models import Country, Address, VisitedCountry

from app.login.util import hash_pass

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

    home_address_id = Column(Integer, ForeignKey('Address.id'))
    home_address = db.relationship('Address', foreign_keys=[home_address_id])

    visited_country_id = Column(Integer, ForeignKey('VisitedCountry.id'), nullable=True)
    visited_country = db.relationship('VisitedCountry')

    telephone = Column(String)
    email = Column(String, nullable=True)

    region_id = Column(Integer, ForeignKey('Region.id'))
    region = db.relationship('Region')

    status_id = Column(Integer, ForeignKey('PatientStatus.id'))
    status = db.relationship('PatientStatus')

    is_found = Column(Boolean, unique=False, default=False)
    is_infected = Column(Boolean, unique=False, default=False)

    hospital_id = Column(Integer, ForeignKey('Hospital.id'))
    hospital = db.relationship('Hospital')

    job = Column(String, nullable=True)
    job_position = Column(String, nullable=True)
    job_address_id = Column(Integer, ForeignKey('Address.id'), nullable=True, default=None)
    job_address = db.relationship('Address', foreign_keys=[job_address_id])

    attrs = Column(JSON, unique=False)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.id)

class ContactedPersons(db.Model):
    __tablename__ = 'ContactedPersons'

    id = Column(Integer, primary_key=True)
    
    person_id = Column(Integer, ForeignKey('Patient.id'))
    # person = db.relationship('Patient')

    patient_id = Column(Integer, ForeignKey('Patient.id'))
    # patient = db.relationship('Patient')
    
    attrs = Column(JSON, unique=False)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.id)   

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

class ContactedPerson(db.Model):

    __tablename__ = 'ContactedPerson'

    id = Column(Integer, primary_key=True)
    full_name = Column(String, unique=False)
    iin = Column(String, unique=True)
    # dob = Column(Date, unique=False)
    telephone = Column(String, unique=False)
    
    region_id = Column(Integer, ForeignKey('Region.id'))
    region = db.relationship('Region')

    home_address = Column(String, unique=False)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.id)
