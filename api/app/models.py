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
    
    # created_by_id = Column(Integer, ForeignKey('User.id'))
    # created_by = relationship('User', backref='id', lazy='dynamic',
    #                     primaryjoin="User.id == Patient.created_by_id")

    # travel_type_id = Column(Integer, ForeignKey('TravelType.id'), nullable=True, default=None)
    # travel_type = relationship('TravelType')

    # travel_id = Column(Integer, nullable=True, default=None, unique=False)

    is_contacted_person = Column(Boolean, unique=False)
   
    first_name = Column(String, unique=False)
    second_name = Column(String, unique=False)
    patronymic_name = Column(String, unique=False, nullable=True)

    # False - male, True - female, None - unknown
    gender = Column(Boolean, nullable=True, default=None)
    dob = Column(Date, nullable=False)
    iin = Column(String, nullable=True, default=None)
    
    pass_num = Column(String, unique=False, nullable=True, default=None)
    
    home_address_id = Column(Integer, ForeignKey('Address.id'), nullable=False)
    home_address = relationship('Address', foreign_keys=[home_address_id], cascade="all,delete", backref="Patient")

    telephone = Column(String, nullable=True, default=None)
    email = Column(String, nullable=True, default=None)

    # region_id = Column(Integer, ForeignKey('Region.id'))
    # region = relationship('Region')

    status_id = Column(Integer, ForeignKey('PatientStatus.id'))
    status = relationship('PatientStatus')
    # posts = relationship('Post', backref='author', lazy='dynamic',
                        # primaryjoin="User.id == Post.user_id"))

    is_found = Column(Boolean, unique=False, default=False)
    is_infected = Column(Boolean, unique=False, default=False)
    # is_contacted = Column(Boolean, unique=False, default=False)

    hospital_id = Column(Integer, ForeignKey('Hospital.id'), nullable=True, default=None)
    hospital = relationship('Hospital')

    # job = Column(String, nullable=True, default=None)
    # job_position = Column(String, nullable=True, default=None)
    # job_address_id = Column(Integer, ForeignKey('Address.id'), nullable=True, default=None)
    # job_address = relationship('Address', foreign_keys=[job_address_id], cascade="all, delete-orphan", single_parent=True)

    # attrs = Column(JSON, unique=False)

    # infected, dead, healthy
    # states = relationship("State", secondary=lambda:PatientState.__table__, backref=backref("patients"))

    # def __init__(self, **kwargs):
    #     for property, value in kwargs.items():
    #         if hasattr(value, '__iter__') and not isinstance(value, str):
    #             value = value[0]
                
    #         setattr(self, property, value)

    # def __repr__(self):
    #     return "{} {} {}".format(str(self.first_name), str(self.second_name), str(self.patronymic_name))

# class PatientState(Base):
#     """
#     PatientState represents many-to-many relationship between Patient and State tables.
#     Table includes:
#     * created_at: creation datetime
#     * detection_date: datetime of detection
#     * comment: comment on state
#     """
#     __tablename__ = 'PatientState'

#     state_id = Column(Integer, ForeignKey('State.id'), primary_key = True)
#     patient_id = Column(Integer, ForeignKey('Patient.id'), primary_key = True)
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
#     patient = relationship('Patient')
#     state = relationship('State')
#     detection_date = Column(DateTime, nullable=False)
#     comment = Column(String, nullable=True)
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
