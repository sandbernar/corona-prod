# -*- encoding: utf-8 -*-
"""
License: MIT
"""

from flask_wtf import FlaskForm
from wtforms import TextField, SelectField, RadioField
from wtforms.validators import DataRequired
from flask_babelex import _

class CreateUserForm(FlaskForm):
    full_name = TextField('Full Name', validators=[DataRequired()])

    username = TextField('Username', validators=[DataRequired()])
    password = TextField('Password', validators=[DataRequired()])

    email    = TextField('Email')
    telephone    = TextField('Telephone')

    region_id = SelectField('Region', validators=[DataRequired()])
    organization = TextField('Organization', validators=[DataRequired()])
    is_admin = RadioField("Is Admin", choices=[(1, _("Да")), (0, _("Нет"))], default=0, validators=[DataRequired()])

class UpdateUserForm(CreateUserForm):
    password = TextField('Password', validators=[])