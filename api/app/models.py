from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Binary, JSON, DateTime, Date, Float
from sqlalchemy.orm import relationship, backref

from .database import Base

import datetime

class Token(Base):
    __tablename__ = 'tokens'

    id = Column(Integer, primary_key=True)
    token = Column(String, unique=False)
    organisation = Column(String, unique=False)

class Patient(Base):
    __tablename__ = 'Patient'

    id = Column(Integer, primary_key=True)
    created_date = Column(DateTime, default=datetime.datetime.utcnow)
    first_name = Column(String, unique=False)
    second_name = Column(String, unique=False)
    patronymic_name = Column(String, unique=False, nullable=True)
    iin = Column(String, nullable=True, default=None)
    pass_num = Column(String, unique=False, nullable=True, default=None)
    home_address_id = Column(Integer, ForeignKey('Address.id'), nullable=False)
    home_address = relationship('Address', foreign_keys=[home_address_id], cascade="all,delete", backref="Patient")
    status_id = Column(Integer, ForeignKey('PatientStatus.id'))
    status = relationship('PatientStatus')
    is_found = Column(Boolean, unique=False, default=False)
    is_infected = Column(Boolean, unique=False, default=False)
    hospital_id = Column(Integer, ForeignKey('Hospital.id'), nullable=True, default=None)
    hospital = relationship('Hospital')

class PatientStatus(Base):

    __tablename__ = 'PatientStatus'

    id = Column(Integer, primary_key=True)
    value = Column(String, unique=True)
    name = Column(String, unique=True)

class Region(Base):

    __tablename__ = 'Region'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

class Country(Base):

    __tablename__ = 'Country'

    id = Column(Integer, primary_key=True)

    code = Column(String, unique=True)
    name = Column(String, unique=True)

class Address(Base):

    __tablename__ = 'Address'

    id = Column(Integer, primary_key=True)

    country_id = Column(Integer, ForeignKey('Country.id'))
    country = relationship('Country')
    
    state = Column(String, nullable=True, default = "")
    county = Column(String, nullable=True, default = "")

    city = Column(String, nullable=True, default = "")

    street = Column(String, nullable=True, default = "")
    house = Column(String, nullable=True, default = "")
    flat = Column(String, nullable=True, default = "")
    building = Column(String, nullable=True, default = "")

    lat = Column(Float, nullable=True, default = None)
    lng = Column(Float, nullable=True, default = None)

class Hospital(Base):

    __tablename__ = 'Hospital'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=False)
    full_name = Column(String, unique=False)
    address = Column(String, unique=False)
    
    region_id = Column(Integer, ForeignKey('Region.id'))
    region = relationship('Region')

class ContactedPersons(Base):
    __tablename__ = 'ContactedPersons'

    id = Column(Integer, primary_key=True)
    
    infected_patient_id = Column(Integer, ForeignKey('Patient.id', ondelete="CASCADE"))
    infected_patient = relationship('Patient', foreign_keys=[infected_patient_id],
                                                backref=backref('infected_patient', passive_deletes=True))

    contacted_patient_id = Column(Integer, ForeignKey('Patient.id'))
    contacted_patient = relationship('Patient', foreign_keys=[contacted_patient_id])
    
    attrs = Column(JSON, unique=False)
