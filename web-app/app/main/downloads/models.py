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

class Download(db.Model):

    __tablename__ = 'Download'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('User.id', ondelete="CASCADE"))
    user = db.relationship('User', backref=db.backref('download', passive_deletes=True))

    task_id = Column(String, unique=False, nullable=False)
    filename = Column(String, unique=False, nullable=True)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.seat)