# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2020 - Artem Fedoskin
"""
import datetime

from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Date, Boolean, Float, ForeignKey, DateTime

from app import db
from app import constants as c

from app.main.models import Region
from app.login.util import hash_pass

class Download(db.Model):

    __tablename__ = 'Download'

    id = Column(Integer, primary_key=True)
    created_date = Column(DateTime, default=datetime.datetime.utcnow)

    user_id = Column(Integer, ForeignKey('User.id', ondelete="CASCADE"))
    user = db.relationship('User', backref=db.backref('downloads', passive_deletes=True))

    task_id = Column(String, unique=False, nullable=False)

    download_name = Column(String, unique=False, nullable=True) 
    filename = Column(String, unique=True, nullable=True)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.seat)