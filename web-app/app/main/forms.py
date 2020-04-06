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

class UploadDataForm(FlaskForm):
    docs = UploadSet('documents', ['xls', 'xlsx', 'csv'])
    file = FileField    (validators=[FileAllowed(docs, 'Только файлы с расширением .xls, .xlsx и .csv!'), FileRequired('Файл пуст!')])
    submit = SubmitField('Загрузить')

class TableSearchForm(FlaskForm):
    region = SelectField(id='region')
    not_found = BooleanField(id="not_found")
    is_infected = BooleanField(id="is_infected")
    not_in_hospital = BooleanField(id="not_in_hospital")
    flight_code = TextField(id='myInput')

    travel_type = SelectField(id='travel_type')

    first_name = TextField()
    second_name = TextField()
    patronymic_name = TextField()

    iin = TextField(id='iin')
    telephone = TextField(id='telephone')