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

    patient_id = Column(Integer, ForeignKey('Patient.id', ondelete="CASCADE"))
    patient = db.relationship('Patient', backref=db.backref('various_travel', passive_deletes=True))    

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
        return str(self.country)        

class Address(db.Model):

    __tablename__ = 'Address'

    id = Column(Integer, primary_key=True)

    country_id = Column(Integer, ForeignKey('Country.id'))
    country = db.relationship('Country')
    
    state = Column(String, nullable=True, default = "")
    county = Column(String, nullable=True, default = "")

    city = Column(String, nullable=False, default = "")

    street = Column(String, nullable=True, default = "")
    house = Column(String, nullable=True, default = "")
    flat = Column(String, nullable=True, default = "")
    building = Column(String, nullable=True, default = "")

    lat = Column(Float, nullable=True, default = None)
    lng = Column(Float, nullable=True, default = None)
    
    def __init__(self, **kwargs):
        set_props(self, kwargs)

    def __repr__(self):
        display_str = str(self.country.name)
        
        # if self.state != None:
            # display_str = display_str + ", {}".format(self.state)

        display_str = display_str + ", {}, {}, {}".format(str(self.city), str(self.street), str(self.house))

        if self.building != None:
            display_str = display_str + ", {}".format(str(self.building))

        return display_str