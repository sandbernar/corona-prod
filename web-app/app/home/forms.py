# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from flask_wtf import FlaskForm
from wtforms import TextField, PasswordField, DateField, SelectField, RadioField, SubmitField, BooleanField
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms.validators import InputRequired, Email, DataRequired
from flask_uploads import UploadSet
from app import constants as c

## login and registration

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
    arrival_date = DateField('Arrival', id='arrival_date'        , validators=[DataRequired()])
    flight_code = TextField('Flight Code', id='flight_code'   , validators=[DataRequired()])
    visited_country = TextField('Visited Country', id='visited_country'   , validators=[DataRequired()])
    
    region_id = SelectField('Region', id='region' , validators=[DataRequired()])

    hospital_region_id = SelectField('Hospital Region', id='hospital_region' , validators=[DataRequired()])
    hospital_id = SelectField('Hospital', id='hospital' , validators=[DataRequired()])

    home_address = TextField('Home Address', id='home_address'   , validators=[DataRequired()])
    job = TextField('Job', id='job'   , validators=[DataRequired()])
    is_found = RadioField("Is Found", id="is_found", choices=[(1, "Да"),(0,"Нет")], validators=[DataRequired()])
    in_hospital = RadioField("In Hospital", id="in_hospital", choices=[(1, "Да"),(0,"Нет")], validators=[DataRequired()])
    hospital = TextField('Hospital', id='hospital')
	
class UploadDataForm(FlaskForm):
    docs = UploadSet('documents', ['xls', 'xlsx', 'csv'])
    file = FileField    (validators=[FileAllowed(docs, 'Только файлы с расширением .xls, .xlsx и .csv!'), FileRequired('Файл пуст!')])
    submit = SubmitField('Загрузить')

class TableSearchForm(FlaskForm):
	region = SelectField(id='region')
	not_found = BooleanField(id="not_found")
	not_in_hospital = BooleanField(id="not_in_hospital")

class UpdateProfileForm(FlaskForm):
	is_found = BooleanField(id="is_found")
	in_hospital = BooleanField(id="in_hospital")

	hospital_region_id = SelectField('Hospital Region', id='hospital_region' , validators=[DataRequired()])
	hospital_type = SelectField('Hospital Type', id='hospital_type' , validators=[DataRequired()])

	hospital_id = SelectField('Hospital_id', id='hospital_id' , validators=[DataRequired()])

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
