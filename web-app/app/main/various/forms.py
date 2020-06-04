# -*- encoding: utf-8 -*-
"""
License: MIT
"""

from flask_wtf import FlaskForm
from wtforms import TextField, SelectField, RadioField, DateField
from wtforms.validators import DataRequired
from flask_babelex import _

class DownloadVariousData(FlaskForm):
	start_count = TextField()
	end_count = TextField()

	hospital_type = SelectField()

	start_date = DateField()
	end_date = DateField()
