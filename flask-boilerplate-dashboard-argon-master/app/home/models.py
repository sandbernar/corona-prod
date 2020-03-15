# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Date, Boolean, Float

from app import db

from app.base.util import hash_pass


class Patient(db.Model):

    __tablename__ = 'Patient'

    id = Column(Integer, primary_key=True)
    full_name = Column(String, unique=False)
    iin = Column(String, unique=True)
    dob = Column(Date, unique=False)
    citizenship = Column(String, unique=False)
    pass_num = Column(String, unique=True)
    telephone = Column(String, unique=False)
    arrival_date = Column(Date, unique=False)
    flight_code = Column(String, unique=False)
    visited_country = Column(String, unique=False)
    region = Column(String, unique=False)
    home_address = Column(String, unique=False)
    job = Column(String, unique=False)
    is_found = Column(Boolean, unique=False)
    in_hospital = Column(Boolean, unique=False)
    hospital = Column(String, unique=False)
    address_lat = Column(Float, unique=False)
    address_lng = Column(Float, unique=False)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]

            # if property == 'password':
                # value = hash_pass( value ) # we need bytes here (not plain str)
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.id)