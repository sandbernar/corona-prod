# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Float, ForeignKey

from app import db
from app import constants as c

from app.login.util import hash_pass

class Hospital(db.Model):

    __tablename__ = 'Hospital'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=False)
    full_name = Column(String, unique=False)
    address = Column(String, unique=False)
    
    region_id = Column(Integer, ForeignKey('Region.id'))
    region = db.relationship('Region')

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