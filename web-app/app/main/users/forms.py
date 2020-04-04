# -*- encoding: utf-8 -*-
"""
License: MIT
"""

from flask_wtf import FlaskForm
from wtforms import TextField, SelectField 
from wtforms.validators import DataRequired

class CreateUserForm(FlaskForm):
    full_name = TextField('Full Name', validators=[DataRequired()])

    username = TextField('Username', validators=[DataRequired()])
    password = TextField('Password', validators=[DataRequired()])

    email    = TextField('Email')
    telephone    = TextField('Telephone')

    region_id = SelectField('Region', validators=[DataRequired()])
    organization = TextField('Organization', validators=[DataRequired()])

class UpdateUserForm(CreateUserForm):
    password = TextField('Password', validators=[])