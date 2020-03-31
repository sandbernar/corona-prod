# -*- encoding: utf-8 -*-
"""
License: MIT
"""

from flask_wtf import FlaskForm
from wtforms import TextField, SelectField 
from wtforms.validators import DataRequired

class CreateUserForm(FlaskForm):
    username = TextField('Username'     , id='username_create' , validators=[DataRequired()])
    email    = TextField('Email'        , id='email_create'    )
    telephone    = TextField('Telephone'        , id='tel_create'    )
    password = TextField('Password' , id='pwd_create'      , validators=[DataRequired()])

    region_id = SelectField('Region', id='region', validators=[DataRequired()])

class UpdateUserForm(FlaskForm):
    username = TextField('Username'     , id='username_create')
    email    = TextField('Email'        , id='email_create'    )
    telephone    = TextField('Telephone'        , id='tel_create'    )
    password = TextField('Password' , id='pwd_create'      )

    region_id = SelectField('Region', id='region', validators=[DataRequired()])