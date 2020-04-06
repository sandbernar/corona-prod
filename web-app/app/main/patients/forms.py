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
from flask_babelex import _

class PatientForm(FlaskForm):
    travel_type = SelectField('Travel Type', id='travel_type', validators=[DataRequired()])

    # Flight Travel
    flight_arrival_date = SelectField('Flight Arrival Date', id='flight_arrival_date', validators=[DataRequired()])
    flight_code_id = SelectField('Flight Code', id='flight_code_id', validators=[DataRequired()])
    flight_seat = TextField('Flight Seat', id='flight_seat')

    # Travel by auto, foot, sea
    arrival_date = DateField('Arrival Date', validators=[DataRequired()])
    auto_border_id = SelectField('By Auto Border', validators=[DataRequired()])
    foot_border_id = SelectField('By Foot Border', id='foot_border_id', validators=[DataRequired()])
    sea_border_id = SelectField('By Sea Border', validators=[DataRequired()])

    first_name = TextField('First Name', validators=[DataRequired()])
    second_name = TextField('Second Name', validators=[DataRequired()])
    patronymic_name = TextField('Patronymic Name')

    gender = RadioField('Gender', choices=[(0, _("Мужчина")), (1, _("Женщина")), (-1, _("Неизвестно"))], 
                                                                            default = -1, validators=[DataRequired()])
    dob = DateField('DoB', validators=[DataRequired()])
    iin = TextField('IIN')

    citizenship_id = SelectField('Citizenship', validators=[DataRequired()])
    pass_num = TextField('Pass No.', id='pass_num')

    country_of_residence_id = SelectField('Residence Country', validators=[DataRequired()])

    home_address_country_id = SelectField('Home Address Country', validators=[DataRequired()])
    home_address_state = TextField('Home State')
    home_address_city = TextField('Home City', validators=[DataRequired()])
    home_address_street = TextField('Home Street', validators=[DataRequired()])
    home_address_house = TextField('Home House', validators=[DataRequired()])
    home_address_flat = TextField('Home Flat')
    home_address_building = TextField('Home Building')    

    visited_country_id = SelectField('Visited Country', validators=[DataRequired()])
    visited_from_date = DateField('Visit From Date')
    visited_to_date = DateField('Visit To Date')
   
    region_id = SelectField('Region', id='region', validators=[DataRequired()])

    job = TextField('Job')
    job_position = TextField('Job Position')

    job_address_country_id = SelectField('Job Address Country')
    job_address_state = TextField('Job State')
    job_address_city = TextField('Job City')
    job_address_street = TextField('Job Street')
    job_address_house = TextField('Job House')
    job_address_flat = TextField('Job Flat')
    job_address_building = TextField('Job Building')

    telephone = TextField('Telephone', id='telephone'   , validators=[DataRequired()])
    email = TextField('EMail', id='email')

    hospital_region_id = SelectField('Hospital Region', id='hospital_region' , validators=[DataRequired()])
    hospital_id = SelectField('Hospital', id='hospital' , validators=[DataRequired()])  

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