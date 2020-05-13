# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from flask_wtf import FlaskForm
from wtforms import TextField, SelectField, BooleanField
from wtforms.validators import InputRequired, DataRequired
from app import constants as c
from app.main.forms import UploadDataForm

class AddHospitalForm(UploadDataForm):
	region_id = SelectField('Hospital Region', validators=[DataRequired()])
	full_name = TextField('Hospital Full Name', validators=[DataRequired()])
	hospital_type_id = SelectField('Hospital Type', validators=[DataRequired()])

class HospitalSearchForm(FlaskForm):
	region = SelectField(id='region')
	hospital_type = SelectField(id='hospital_type')

class HospitalPatientsSearchForm(FlaskForm):
    full_name = TextField("Full Name")
    region_id = SelectField("Region ID")
    iin = TextField("IIN")  