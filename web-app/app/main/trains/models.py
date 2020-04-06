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

class TrainTravel(db.Model):

    __tablename__ = 'TrainTravel'

    id = Column(Integer, primary_key=True)

    train_code_id = Column(Integer, ForeignKey('TrainCode.id'))
    train_code = db.relationship('TrainCode')

    wagon = Column(String, unique=False, nullable=True) 
    seat = Column(String, unique=False, nullable=True)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.seat)

class TrainCode(db.Model):

    __tablename__ = 'TrainCode'

    id = Column(Integer, primary_key=True)
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