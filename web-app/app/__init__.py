# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from logging import basicConfig, DEBUG, getLogger, StreamHandler
from os import path, getenv, environ
from importlib import import_module
from celery import Celery

from flask import Flask, url_for
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
import numpy as np

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
celery = Celery(__name__)

def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)

def register_blueprints(app):
    for module_name in ('login', 'main'):
        module = import_module('app.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)

        if module_name == "main":
            for submodule_name in ["users", "hospitals", "patients", "flights_trains", "various"]:
                module = import_module('app.{}.{}.routes'.format(module_name, submodule_name))
                app.register_blueprint(module.blueprint)            

def configure_database(app):
    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()

def configure_logs(app):
    # soft logging
    try:
        basicConfig(filename='error.log', level=DEBUG)
        logger = getLogger()
        logger.addHandler(StreamHandler())
    except:
        pass

def apply_themes(app):
    """
    Add support for themes.

    If DEFAULT_THEME is set then all calls to
      url_for('static', filename='')
      will modfify the url to include the theme name

    The theme parameter can be set directly in url_for as well:
      ex. url_for('static', filename='', theme='')

    If the file cannot be found in the /static/<theme>/ location then
      the url will not be modified and the file is expected to be
      in the default /static/ location
    """
    @app.context_processor
    def override_url_for():
        return dict(url_for=_generate_url_for_theme)

    def _generate_url_for_theme(endpoint, **values):
        if endpoint.endswith('static'):
            themename = values.get('theme', None) or \
                app.config.get('DEFAULT_THEME', None)
            if themename:
                theme_file = "{}/{}".format(themename, values.get('filename', ''))
                if path.isfile(path.join(app.static_folder, theme_file)):
                    values['filename'] = theme_file
        return url_for(endpoint, **values)

def create_app(config, selenium=False, unittest=False):
    app = Flask(__name__, static_folder='main/static')
    # csrf = CSRFProtect(app)

    app.config.from_object(config)
    if selenium:
        app.config['LOGIN_DISABLED'] = True
    if unittest:
        app.config['WTF_CSRF_ENABLED'] = False
    app.config['SECRET_KEY'] = getenv("APP_SECRET_KEY") or "supersecret123456haha"

    app.config['CELERY_BROKER_URL'] = environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    app.config['CELERY_RESULT_BACKEND'] = environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

    celery.conf.update(app.config)

    csrf.init_app(app)
    register_extensions(app)
    register_blueprints(app)
    configure_database(app)
    configure_logs(app)
    apply_themes(app)
    return app
