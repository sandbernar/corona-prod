# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from flask import Flask, url_for
from flask_babel import Babel, gettext
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module
from logging import basicConfig, DEBUG, getLogger, StreamHandler
from os import path
import pandas as pd
import re


from app import constants as C

db = SQLAlchemy()
login_manager = LoginManager()

def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)

def register_blueprints(app):
    for module_name in ('base', 'home'):
        module = import_module('app.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)

def configure_database(app):
    def add_hospitals():
        from app.home.models import ( Hospital, Region, Hospital_Type, Hospital_Nomenklatura, PatientStatus, 
            Foreign_Country, Infected_Country_Category, ContactedPersons, TravelType)
       
        # Clean the tables
        TravelType.query.delete()
        Region.query.delete()
        Hospital_Type.query.delete()
        Hospital_Nomenklatura.query.delete()
        PatientStatus.query.delete()

        Infected_Country_Category.query.delete()
        Foreign_Country.query.delete()
        ContactedPersons.query.delete()

        db.session.commit()

        df = pd.read_excel(C.hospitals_list_xlsx)
        df = df.drop_duplicates()

        for typ in C.travel_types:
            travel_type = TravelType(value=typ[0], name=typ[1])
            db.session.add(travel_type)        

        for cat in C.country_category:
            country_cat = Infected_Country_Category(name=cat)
            db.session.add(country_cat)

        for country in C.code_country_list:
            new_country = Foreign_Country(value=country[0], name=country[1])
            db.session.add(new_country)

        for status in C.patient_statuses:
            p_status = PatientStatus(value=status[0], name=status[1])
            db.session.add(p_status)

        for n in df.region.unique():
            region = Region(name=n)
            db.session.add(region)

        region = Region(name="Вне РК")
        db.session.add(region)

        for n in df.Nomenklatura.unique():
            nomen = Hospital_Nomenklatura(name=n)
            db.session.add(nomen)

        for n in df.TIPMO.unique():
            typ = Hospital_Type(name=n)
            db.session.add(typ)

        db.session.commit()

        for index, row in df.iterrows():
            hospital = Hospital()

            full_name = row["Name"]
            short_name = re.findall('"([^"]*)"', full_name.replace("«", "\"").replace("»", "\""))
            if not len(short_name):
                short_name = full_name
            elif not (len(short_name[0])):
                short_name = full_name
            else:
                short_name = short_name[0]

            hospital.name = short_name
            hospital.full_name = full_name
            
            region = Region.query.filter_by(name=row["region"]).first()
            hospital.region_id = region.id
            hospital.address = ", ".join(row["Adres"].split(":")[3:])

            hospital_type = Hospital_Type.query.filter_by(name=row["TIPMO"]).first()
            hospital.hospital_type_id = hospital_type.id

            hospital_nomenklatura = Hospital_Nomenklatura.query.filter_by(name=row["Nomenklatura"]).first()
            hospital.hospital_nomenklatura_id = hospital_nomenklatura.id

            hospital.beds_amount = 0
            hospital.meds_amount = 0
            hospital.tests_amount = 0
            hospital.tests_used = 0

            db.session.add(hospital)

        db.session.commit()

    def initialize_db(db):
        from app.home.models import Hospital
        hospitals = Hospital.query.count()
        
        if hospitals == 0:
            add_hospitals()

    @app.before_first_request
    def initialize_database():
        db.create_all()

        initialize_db(db)

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

def create_app(config, selenium=False):
    app = Flask(__name__, static_folder='base/static')
    babel = Babel(app)
    app.config.from_object(config)
    if selenium:
        app.config['LOGIN_DISABLED'] = True
    register_extensions(app)
    register_blueprints(app)
    configure_database(app)
    configure_logs(app)
    apply_themes(app)
    return app
