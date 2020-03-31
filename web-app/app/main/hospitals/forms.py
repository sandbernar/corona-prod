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

class AddHospitalsDataForm(UploadDataForm):
	region = TextField('Region', id='region'   , validators=[DataRequired()])
	hospital_type = SelectField('Hospital Type', id='hospital_type',
    	default=0,
    	choices=[(0, "Больница"),
    			(1, "Диспансер"),
    			(2, "Поликлиника")])

class HospitalSearchForm(FlaskForm):
	region = SelectField(id='region')
	nomenklatura = SelectField(id='nomenklatura')
	hospital_type = SelectField(id='hospital_type')


class UpdateHospitalProfileForm(FlaskForm):
	is_found = BooleanField(id="is_found")
	in_hospital = BooleanField(id="in_hospital")

	hospital = TextField('Hospital', id='hospital'   , validators=[DataRequired()])
