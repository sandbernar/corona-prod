# -*- encoding: utf-8 -*-
"""
License: MIT
"""

from flask_wtf import FlaskForm
from wtforms import TextField, SelectField, DateField
from wtforms.validators import DataRequired
import app.constants as c

class FlightTrainsForm(FlaskForm):
    from_country_id = SelectField('From Country',
                                validators=[DataRequired()])

    from_city = TextField('From City', id='from_city', validators=[DataRequired()])

    to_country_id = SelectField('To Country',
                                validators=[DataRequired()])
    to_city = TextField('To City', id='to_city', validators=[DataRequired()])

class FlightForm(FlightTrainsForm):
    date = DateField('Date', validators=[DataRequired()])
    code = TextField('Code'     , id='flight_code' , validators=[DataRequired()])

class TrainForm(FlightTrainsForm):
    departure_date = DateField('Departure Date', validators=[DataRequired()])
    arrival_date = DateField('Arrival Date', validators=[DataRequired()])