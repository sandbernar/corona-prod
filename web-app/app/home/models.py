# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Date, Boolean, Float, ForeignKey

from app import db
from app import constants as c

from app.base.util import hash_pass

class Patient(db.Model):

    __tablename__ = 'Patient'

    id = Column(Integer, primary_key=True)
    full_name = Column(String, unique=False)
    iin = Column(String, unique=False)
    dob = Column(Date, unique=False)
    citizenship = Column(String, unique=False)
    pass_num = Column(String, unique=False)
    telephone = Column(String, unique=False)
    arrival_date = Column(Date, unique=False)
    visited_country = Column(String, unique=False)
    
    is_contacted_person = Column(Boolean, unique=False)

    travel_type_id = Column(Integer, ForeignKey('TravelType.id'))
    travel_type = db.relationship('TravelType')    

    flight_code_id = Column(Integer, ForeignKey('FlightCode.id'), nullable=True, default=None)
    flight_code = db.relationship('FlightCode')

    region_id = Column(Integer, ForeignKey('Region.id'))
    region = db.relationship('Region')

    status_id = Column(Integer, ForeignKey('PatientStatus.id'))
    status = db.relationship('PatientStatus')

    is_found = Column(Boolean, unique=False)
    is_infected = Column(Boolean, unique=False, default=False)

    hospital_id = Column(Integer, ForeignKey('Hospital.id'))
    hospital = db.relationship('Hospital')

    home_address = Column(String, unique=False)
    job = Column(String, unique=False)

    address_lat = Column(Float, unique=False)
    address_lng = Column(Float, unique=False)

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

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.id)

class FlightCode(db.Model):

    __tablename__ = 'FlightCode'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.name)       

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


class Hospital(db.Model):

    __tablename__ = 'Hospital'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=False)
    full_name = Column(String, unique=False)
    address = Column(String, unique=False)
    
    region_id = Column(Integer, ForeignKey('Region.id'))
    region = db.relationship('Region')

    hospital_nomenklatura_id = Column(Integer, ForeignKey('Hospital_Nomenklatura.id'))
    hospital_nomenklatura = db.relationship('Hospital_Nomenklatura')

    hospital_type_id = Column(Integer, ForeignKey('Hospital_Type.id'))
    hospital_type = db.relationship('Hospital_Type')

    address_lat = Column(Float, unique=False)
    address_lng = Column(Float, unique=False)
    beds_amount = Column(Integer, unique=False)
    meds_amount = Column(Integer, unique=False)
    tests_amount = Column(Integer, unique=False)
    tests_used = Column(Integer, unique=False)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.name)

class Region(db.Model):

    __tablename__ = 'Region'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.name)

class TravelType(db.Model):

    __tablename__ = 'TravelType'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    value = Column(String, unique=True)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.name)

class Hospital_Type(db.Model):

    __tablename__ = 'Hospital_Type'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.name)

class Hospital_Nomenklatura(db.Model):

    __tablename__ = 'Hospital_Nomenklatura'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.name)

class Infected_Country_Category(db.Model):

    __tablename__ = 'Infected_Country_Category'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.name)

class Foreign_Country(db.Model):

    __tablename__ = 'Foreign_Country'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    value = Column(String, unique=True)
    
    category_id = Column(Integer, ForeignKey('Infected_Country_Category.id'))
    category = db.relationship('Infected_Country_Category')

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.name)