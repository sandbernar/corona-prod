# -*- encoding: utf-8 -*-
"""
License: MIT
"""

from flask_wtf import FlaskForm
from wtforms import TextField, SelectField, RadioField, DateField, BooleanField
from wtforms.validators import DataRequired
from flask_babelex import _

class DownloadSearchForm(FlaskForm):

    download_date = DateField('Report End Date')
