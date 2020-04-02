# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from flask_wtf import FlaskForm
from wtforms import TextField, DateField, SelectField, RadioField, BooleanField
from wtforms.validators import DataRequired
from app.main.forms import UploadDataForm
from app import constants as c

class PatientForm(FlaskForm):
    full_name = TextField    ('Full Name', id='full_name'   , validators=[DataRequired()])
    iin = TextField('IIN', id='iin'   , validators=[DataRequired()])
    dob = DateField('DoB', id='dob'        , validators=[DataRequired()])
    citizenship = SelectField('Citizenship', id='citizenship',
    	default="KZ",
    	choices=c.code_country_list, 
    	validators=[DataRequired()])
    pass_num = TextField('Pass No.', id='pass_num'   , validators=[DataRequired()])
    telephone = TextField('Telephone', id='telephone'   , validators=[DataRequired()])
    visited_country = TextField('Visited Country', id='visited_country'   , validators=[DataRequired()])
    
    region_id = SelectField('Region', id='region', validators=[DataRequired()])

    travel_type_id = SelectField('Travel Type', id='travel_type_id', validators=[DataRequired()])
    
    flight_arrival_date = SelectField('Flight Arrival Date', id='flight_arrival_date'        , validators=[DataRequired()])
    flight_code_id = SelectField('Flight Code', id='flight_code_id', validators=[DataRequired()])

    hospital_region_id = SelectField('Hospital Region', id='hospital_region' , validators=[DataRequired()])
    hospital_id = SelectField('Hospital', id='hospital' , validators=[DataRequired()])

    home_address = TextField('Home Address', id='home_address'   , validators=[DataRequired()])
    job = TextField('Job', id='job'   , validators=[DataRequired()])
    patient_status = SelectField('Patient Status', id='patient_status' , validators=[DataRequired()])
    is_found = RadioField("Is Found", id="is_found", choices=[(1, "Да"),(0,"Нет")], default=0, validators=[DataRequired()])
    is_infected = RadioField("Is Infected", id="is_infected", choices=[(1, "Да"),(0,"Нет")], default=0, validators=[DataRequired()])
    hospital = TextField('Hospital', id='hospital')

class UpdateProfileForm(PatientForm):
    is_found = BooleanField(id="is_found")
    is_infected = BooleanField(id="is_infected")
    in_hospital = BooleanField(id="in_hospital")
    is_home = BooleanField(id="is_home")
    is_transit = BooleanField(id="is_transit")
    citizenship = TextField('Citizenship', id='citizenship', validators=[DataRequired()])
    flight_code_id = SelectField('Flight Code', id='flight_code_id')

    hospital_region_id = SelectField('Hospital Region', id='hospital_region' , validators=[DataRequired()])
    hospital_type = SelectField('Hospital Type', id='hospital_type' , validators=[DataRequired()])

    hospital_id = SelectField('Hospital_id', id='hospital_id' , validators=[DataRequired()])

class AddFlightFromExcel(UploadDataForm):
    flights_id = SelectField('Flights ID', id='flights_id' , validators=[DataRequired()])