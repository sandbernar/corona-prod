# -*- encoding: utf-8 -*-
"""
License: MIT
"""

from flask_wtf import FlaskForm
from wtforms import TextField, SelectField, DateField
from wtforms.validators import DataRequired
import app.constants as c

class FlightForm(FlaskForm):
    code = TextField('Code'     , id='flight_code' , validators=[DataRequired()])
    date    = DateField('Date'        , id='arrival_date', validators=[DataRequired()])

    from_country = SelectField('From Country',
                                default="KZ",
                                choices=c.code_country_list,
                                id='from_country',
                                validators=[DataRequired()])

    from_city = TextField('From City', id='from_city', validators=[DataRequired()])

    to_country = SelectField('To Country',
                                default="KZ",
                                choices=c.code_country_list,
                                id='to_country',
                                validators=[DataRequired()])
    to_city = TextField('To City', id='to_city', validators=[DataRequired()])