# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

import os
from   os import environ

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):

    basedir    = os.path.abspath(os.path.dirname(__file__))
    LANGUAGES = ['ru_RU', 'kk_KZ']

    SECRET_KEY = 'S3cretKey_7655'

    # This will create a file in <app> FOLDER
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'database.db')

    # For 'in memory' database, please use:
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    #     
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # THEME SUPPORT
    #  if set then url_for('static', filename='', theme='')
    #  will add the theme name to the static URL:
    #    /static/<DEFAULT_THEME>/filename
    # DEFAULT_THEME = "themes/dark"
    DEFAULT_THEME = None
    UPLOADED_DOCUMENTS_DEST = os.path.join(basedir, 'documents')
    TEMPLATES_AUTO_RELOAD = True


class ProductionConfig(Config):
    DEBUG = False

    # Security
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 3600

    # PostgreSQL database
    SQLALCHEMY_DATABASE_URI = 'postgresql://{}:{}@{}:{}/{}'.format(
        environ.get('DATABASE_USER'),
        environ.get('DATABASE_PASSWORD'),
        environ.get('DATABASE_HOST', ''),
        environ.get('DATABASE_PORT', '5432'),
        environ.get('DATABASE_NAME')
    )
    
    TEMPLATES_AUTO_RELOAD = True


class DebugConfig(Config):
    DEBUG = True


config_dict = {
    'Production': ProductionConfig,
    'Debug': DebugConfig
}
