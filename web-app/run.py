# -*- encoding: utf-8 -*-
"""
License: Commercial
Copyright (c) 2019 - present AppSeed.us
"""

from flask_migrate import Migrate
from os import environ
from sys import exit
from flask_uploads import UploadSet, configure_uploads
from flask_babelex import Babel
from flask import request, session

from config import config_dict
from app import create_app, db

get_config_mode = environ.get('CONFIG_MODE', 'Debug')
print(get_config_mode)

try:
    config_mode = config_dict[get_config_mode.capitalize()]
except KeyError:
    exit('Error: Invalid CONFIG_MODE environment variable entry.')

app = create_app(config_mode)
Migrate(app, db)
babel = Babel(app)

@babel.localeselector
def get_locale():
    if request.args.get('lang'):
        session['lang'] = request.args.get('lang')
    return session.get('lang', 'en')

docs = UploadSet('documents', ['xls', 'xlsx', 'csv'])
configure_uploads(app, docs)

if __name__ == "__main__":
    app.run()
