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
from app.login.util import hash_pass
from flask_babelex import _

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

    patient_id = Column(Integer, ForeignKey('Patient.id', ondelete="CASCADE"))
    patient = db.relationship('Patient', backref=db.backref('various_travel', passive_deletes=True))    

    border_control_id = Column(Integer, ForeignKey('BorderControl.id'), nullable=True, default=None)
    border_control = db.relationship('BorderControl')

    def __init__(self, **kwargs):
        set_props(self, kwargs)

    def __repr__(self):
        return str(self.border_control)

class BlockpostTravel(db.Model):
    __tablename__ = 'BlockpostTravel'

    id = Column(Integer, primary_key=True)
    date = Column(Date)

    patient_id = Column(Integer, ForeignKey('Patient.id', ondelete="CASCADE"))
    patient = db.relationship('Patient', backref=db.backref('blockpost_travel', passive_deletes=True))    

    region_id = Column(Integer, ForeignKey('Region.id'), nullable=False)
    region = db.relationship('Region')

    def __init__(self, **kwargs):
        set_props(self, kwargs)

    def __repr__(self):
        return str(self.border_control)

class OldDataTravel(db.Model):
    __tablename__ = 'OldDataTravel'
    id = Column(Integer, primary_key=True)

    patient_id = Column(Integer, ForeignKey('Patient.id', ondelete="CASCADE"))
    patient = db.relationship('Patient', backref=db.backref('old_data_travel', passive_deletes=True))    

    date = Column(Date, nullable=True)
    place = Column(String, nullable=True)
    path = Column(String, nullable=True)

    attrs = Column(JSON, unique=False)

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

class Country(db.Model):

    __tablename__ = 'Country'

    id = Column(Integer, primary_key=True)

    code = Column(String, unique=True)
    name = Column(String, unique=True)
    
    # category_id = Column(Integer, ForeignKey('Infected_Country_Category.id'))
    # category = db.relationship('Infected_Country_Category')

    def __init__(self, **kwargs):
        set_props(self, kwargs)

    def __repr__(self):
        return str(self.name)

class VisitedCountry(db.Model):

    __tablename__ = 'VisitedCountry'

    id = Column(Integer, primary_key=True)
    
    patient_id = Column(Integer, ForeignKey('Patient.id', ondelete="CASCADE"))
    patient = db.relationship('Patient', backref=db.backref('visited_country', passive_deletes=True))

    country_id = Column(Integer, ForeignKey('Country.id'), nullable=True, default=None)
    country = db.relationship('Country')

    from_date = Column(Date, nullable=True)
    to_date = Column(Date, nullable=True)

    def __init__(self, **kwargs):
        set_props(self, kwargs)

    def __repr__(self):
        if self.country:
            return str(self.country)
        else:
            return _("Неизвестно")


class JobCategory(db.Model):
    __tablename__ = 'JobCategory'

    id = Column(Integer, primary_key=True)
    value = Column(String, unique=True, nullable=True, default=None)
    name = Column(String, unique=True)

    def __init__(self, **kwargs):
        set_props(self, kwargs)

    def __repr__(self):
        return str(self.name)

class Address(db.Model):

    __tablename__ = 'Address'

    id = Column(Integer, primary_key=True)

    country_id = Column(Integer, ForeignKey('Country.id'))
    country = db.relationship('Country')
    
    state = Column(String, nullable=True, default = "")
    county = Column(String, nullable=True, default = "")

    city = Column(String, nullable=True, default = "")

    street = Column(String, nullable=True, default = "")
    house = Column(String, nullable=True, default = "")
    flat = Column(String, nullable=True, default = "")
    building = Column(String, nullable=True, default = "")

    lat = Column(Float, nullable=True, default = None)
    lng = Column(Float, nullable=True, default = None)
    
    def __init__(self, **kwargs):
        set_props(self, kwargs)

    def __repr__(self):
        display_str = ""

        for param in [("", self.country), ("", self.city), ("", self.street), (_("дом"), self.house),
                        (_("кв."), self.flat), (_("корпус"), self.building)]:
            if param[1] != None and param[1] != "":
                display_str = display_str + "{} {}, ".format(param[0], param[1])
        
        # Get rid of the last comma
        display_str = str(display_str).rstrip().rstrip(",")

        return display_str

class Token(db.Model):
    __tablename__ = 'tokens'

    id = Column(Integer, primary_key=True)
    token = Column(String, unique=False)
    organisation = Column(String, unique=False)

class HGBDToken(db.Model):
    __tablename__ = 'HGBDToken'

    id = Column(Integer, primary_key=True)
    token = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    count = Column(Integer, default=0)
