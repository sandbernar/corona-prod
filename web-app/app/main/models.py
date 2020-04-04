# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Date, Boolean, Float, ForeignKey

from app import db
from app import constants as c

from app.login.util import hash_pass

def set_props(model, kwargs):
    for property, value in kwargs.items():
        if hasattr(value, '__iter__') and not isinstance(value, str):
            value = value[0]
            
        setattr(model, property, value)

class Region(db.Model):

    __tablename__ = 'Region'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    def __init__(self, **kwargs):
        set_props(self, kwargs)

    def __repr__(self):
        return str(self.name)

class TravelType(db.Model):

    __tablename__ = 'TravelType'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    value = Column(String, unique=True)

    def __init__(self, **kwargs):
        set_props(self, kwargs)

    def __repr__(self):
        return str(self.name)

class VariousTravel(db.Model):
    __tablename__ = 'VariousTravel'

    id = Column(Integer, primary_key=True)
    date = Column(Date)

    border_control_id = Column(Integer, ForeignKey('BorderControl.id'), nullable=True, default=None)
    border_control = db.relationship('BorderControl')

    def __init__(self, **kwargs):
        set_props(self, kwargs)

    def __repr__(self):
        return str(self.border_control)    

class BorderControl(db.Model):
    __tablename__ = 'BorderControl'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    
    travel_type_id = Column(Integer, ForeignKey('TravelType.id'), nullable=True, default=None)
    travel_type = db.relationship('TravelType')    

    def __init__(self, **kwargs):
        set_props(self, kwargs)

    def __repr__(self):
        return str(self.name)

class Infected_Country_Category(db.Model):

    __tablename__ = 'Infected_Country_Category'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    def __init__(self, **kwargs):
        set_props(self, kwargs)

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
        set_props(self, kwargs)

    def __repr__(self):
        return str(self.name)