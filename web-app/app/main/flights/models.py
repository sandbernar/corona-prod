# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Date, Boolean, Float, ForeignKey

from app import db
from app import constants as c

from app.main.models import Region
from app.login.util import hash_pass

class FlightTravel(db.Model):

    __tablename__ = 'FlightTravel'

    id = Column(Integer, primary_key=True)

    patient_id = Column(Integer, ForeignKey('Patient.id', ondelete="CASCADE"))
    patient = db.relationship('Patient', backref=db.backref('flight_travel', passive_deletes=True))

    flight_code_id = Column(Integer, ForeignKey('FlightCode.id'))
    flight_code = db.relationship('FlightCode')

    seat = Column(String, unique=False, nullable=True)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.seat)

class FlightCode(db.Model):

    __tablename__ = 'FlightCode'

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=False)

    date = Column(Date, unique=False)

    from_country = Column(String, unique=False)
    from_city = Column(String, unique=False)

    to_country = Column(String, unique=False)
    to_city = Column(String, unique=False)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.code)