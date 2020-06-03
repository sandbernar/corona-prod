# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from flask_login import UserMixin
from sqlalchemy import Binary, Column, Integer, String, Date, Boolean, ForeignKey

from app import db, login_manager

from app.login.util import hash_pass
from app.main.models import Region

class User(db.Model, UserMixin):
    __tablename__ = 'User'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(Binary)

    full_name = Column(String, nullable=True, default=None)
    organization = Column(String, nullable=True, default=None)
    telephone = Column(String, nullable=True, default=None)
    email = Column(String, nullable=True, default=None)

    region_id = Column(Integer, ForeignKey('Region.id'))
    region = db.relationship('Region')

    @property
    def is_admin(self):
        admin_role = UserRole.query.filter_by(value="admin").first()

        return user_role_id == admin_role.id
    
    is_admin = Column(Boolean, default=True)

    user_role_id = Column(Integer, ForeignKey('UserRole.id'))
    user_role = db.relationship('UserRole')

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]

            if property == 'password':
                value = hash_pass( value ) # we need bytes here (not plain str)

            if property == 'region_id':
                setattr(self, 'is_admin', value == None)
                
            setattr(self, property, value)

    def __repr__(self):
        return str(self.username)

def set_props(model, kwargs):
    for property, value in kwargs.items():
        if hasattr(value, '__iter__') and not isinstance(value, str):
            value = value[0]
            
        setattr(model, property, value)

class UserRole(db.Model):
    __tablename__ = 'UserRole'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    value = Column(String, unique=True, nullable=False)

    #User Rights
    can_add_air = Column(Boolean, default=False)
    can_add_train = Column(Boolean, default=False)
    can_add_auto = Column(Boolean, default=False)
    can_add_foot = Column(Boolean, default=False)
    can_add_sea = Column(Boolean, default=False)
    can_add_local = Column(Boolean, default=False)
    can_add_blockpost = Column(Boolean, default=False)
    can_see_success_add_window = Column(Boolean, default=False)

    can_lookup_own_patients = Column(Boolean, default=False)
    can_lookup_other_patients = Column(Boolean, default=False)

    can_found_by_default = Column(Boolean, default=False) 
    can_set_infected = Column(Boolean, default=False) 
    can_set_hospital_home_quarant = Column(Boolean, default=False) 
    can_set_transit = Column(Boolean, default=False) 
    can_access_contacted = Column(Boolean, default=False)    
    can_delete_own_patients = Column(Boolean, default=False)
    can_delete_other_patients = Column(Boolean, default=False)

    can_export_patients = Column(Boolean, default=False)
    can_export_contacted = Column(Boolean, default=False)
    can_add_edit_hospital = Column(Boolean, default=False)
    
    can_block_own_region_accounts = Column(Boolean, default=False)
    can_block_all_accounts = Column(Boolean, default=False)
    can_access_roles = Column(Boolean, default=False)

    def __init__(self, **kwargs):
        set_props(self, kwargs)

    def __repr__(self):
        return str(self.name)

@login_manager.user_loader
def user_loader(id):
    return User.query.filter_by(id=id).first()

@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    user = User.query.filter_by(username=username).first()
    return user if user else None
