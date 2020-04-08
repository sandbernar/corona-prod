# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from flask import Flask, url_for
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module
from logging import basicConfig, DEBUG, getLogger, StreamHandler
from os import path
import pandas as pd
import re
from flask_wtf.csrf import CSRFProtect


from app import constants as C

db = SQLAlchemy()
login_manager = LoginManager()

def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)

def register_blueprints(app):
    for module_name in ('login', 'main'):
        module = import_module('app.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)

        if module_name == "main":
            for submodule_name in ["users", "hospitals", "patients", "flights"]:
                module = import_module('app.{}.{}.routes'.format(module_name, submodule_name))
                app.register_blueprint(module.blueprint)            

def configure_database(app):
    def add_hospitals():
        from app.main.models import (Region, Country, Infected_Country_Category, 
                                    TravelType, BorderControl, VariousTravel, Address, VisitedCountry)
        from app.main.patients.models import PatientStatus, ContactedPersons, Patient
        from app.main.hospitals.models import  Hospital, Hospital_Type
        from app.main.flights.models import FlightTravel, FlightCode
       
        # Clear the tables
        Patient.query.delete()

        ## Travel
        BorderControl.query.delete()
        VariousTravel.query.delete()
        
        ### Flight
        FlightTravel.query.delete()
        FlightCode.query.delete()

        TravelType.query.delete()
        Region.query.delete()

        Hospital_Type.query.delete()

        PatientStatus.query.delete()
        ContactedPersons.query.delete()

        Infected_Country_Category.query.delete()
        VisitedCountry.query.delete()

        Address.query.delete()
        Country.query.delete()

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
            new_country = Country(code=country[0], name=country[1])
            db.session.add(new_country)

        for status in C.patient_statuses:
            p_status = PatientStatus(value=status[0], name=status[1])
            db.session.add(p_status)

        for n in df.region.unique():
            region = Region(name=n)
            db.session.add(region)

        region = Region(name="Вне РК")
        db.session.add(region)

        for n in df.TIPMO.unique():
            if not pd.isna(n):
                typ = Hospital_Type(name=n)
                db.session.add(typ)

        db.session.commit()

        # We need to get ids of TravelType for by auto and by foot types
        q = TravelType.query
        foot_auto_type_ids = [q.filter_by(value = C.by_auto_type[0]).first().id,
                              q.filter_by(value = C.by_foot_type[0]).first().id]
        
        for type_id in foot_auto_type_ids:
            for border_name in C.by_earth_border:
                border = BorderControl(travel_type_id = type_id, name = border_name)
                db.session.add(border)

        sea_type_id = q.filter_by(value = C.by_sea_type[0]).first().id
        for border_name in C.by_sea_border:
            border = BorderControl(travel_type_id = sea_type_id, name = border_name)
            db.session.add(border)

        for index, row in df.iterrows():
            hospital = Hospital()

            full_name = row["Name"]
            if not pd.isna(full_name):
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

                hospital.beds_amount = 0
                hospital.meds_amount = 0
                hospital.tests_amount = 0
                hospital.tests_used = 0

                db.session.add(hospital)

        db.session.commit()

    def initialize_db(db):
        from app.main.hospitals.models import Hospital
        hospitals = Hospital.query.count()
        
        if hospitals == 0:
            add_hospitals()
        
        triggers = db.engine.execute('select * from information_schema.triggers')
        triggers = [row for row in triggers]

        if len(triggers) == 0:
            triggerQueries = [
                'CREATE TRIGGER "triggerPatient" BEFORE INSERT OR UPDATE OR DELETE ON "Patient" FOR EACH ROW EXECUTE PROCEDURE change_trigger();',
                'CREATE TRIGGER "triggerContactedPersons" BEFORE INSERT OR UPDATE OR DELETE ON "ContactedPersons" FOR EACH ROW EXECUTE PROCEDURE change_trigger();',
                'CREATE TRIGGER "triggerRegion" BEFORE INSERT OR UPDATE OR DELETE ON "Region" FOR EACH ROW EXECUTE PROCEDURE change_trigger();',
                'CREATE TRIGGER "triggerTravelType" BEFORE INSERT OR UPDATE OR DELETE ON "TravelType" FOR EACH ROW EXECUTE PROCEDURE change_trigger();',
                'CREATE TRIGGER "triggerInfected_Country_Category" BEFORE INSERT OR UPDATE OR DELETE ON "Infected_Country_Category" FOR EACH ROW EXECUTE PROCEDURE change_trigger();',
                'CREATE TRIGGER "triggerPatientStatus" BEFORE INSERT OR UPDATE OR DELETE ON "PatientStatus" FOR EACH ROW EXECUTE PROCEDURE change_trigger();',
                'CREATE TRIGGER "triggerCountry" BEFORE INSERT OR UPDATE OR DELETE ON "Country" FOR EACH ROW EXECUTE PROCEDURE change_trigger();',
                'CREATE TRIGGER "triggerFlightCode" BEFORE INSERT OR UPDATE OR DELETE ON "FlightCode" FOR EACH ROW EXECUTE PROCEDURE change_trigger();',
                'CREATE TRIGGER "triggerBorderControl" BEFORE INSERT OR UPDATE OR DELETE ON "BorderControl" FOR EACH ROW EXECUTE PROCEDURE change_trigger();',
                'CREATE TRIGGER "triggerVisitedCountry" BEFORE INSERT OR UPDATE OR DELETE ON "VisitedCountry" FOR EACH ROW EXECUTE PROCEDURE change_trigger();',
                'CREATE TRIGGER "triggerAddress" BEFORE INSERT OR UPDATE OR DELETE ON "Address" FOR EACH ROW EXECUTE PROCEDURE change_trigger();',
                'CREATE TRIGGER "triggerUser" BEFORE INSERT OR UPDATE OR DELETE ON "User" FOR EACH ROW EXECUTE PROCEDURE change_trigger();',
                'CREATE TRIGGER "triggerHospital_Type" BEFORE INSERT OR UPDATE OR DELETE ON "Hospital_Type" FOR EACH ROW EXECUTE PROCEDURE change_trigger();',
                'CREATE TRIGGER "triggerContactedPerson" BEFORE INSERT OR UPDATE OR DELETE ON "ContactedPerson" FOR EACH ROW EXECUTE PROCEDURE change_trigger();',
                'CREATE TRIGGER "triggerHospital" BEFORE INSERT OR UPDATE OR DELETE ON "Hospital" FOR EACH ROW EXECUTE PROCEDURE change_trigger();',
                'CREATE TRIGGER "triggerFlightTravel" BEFORE INSERT OR UPDATE OR DELETE ON "FlightTravel" FOR EACH ROW EXECUTE PROCEDURE change_trigger();',
                'CREATE TRIGGER "triggerVariousTravel" BEFORE INSERT OR UPDATE OR DELETE ON "VariousTravel" FOR EACH ROW EXECUTE PROCEDURE change_trigger();'
            ]
            for triggerQuery in triggerQueries:
                db.engine.execute(triggerQuery)

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

def create_app(config, selenium=False, unittest=False):
    app = Flask(__name__, static_folder='main/static')
    app.config.from_object(config)
    if selenium:
        app.config['LOGIN_DISABLED'] = True
    if unittest:
        app.config['CSRF_ENABLED'] = False
    print("unittest haha", unittest)
    csrf = CSRFProtect(app)
    register_extensions(app)
    register_blueprints(app)
    configure_database(app)
    configure_logs(app)
    apply_themes(app)
    return app
