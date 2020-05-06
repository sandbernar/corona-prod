# -*- encoding: utf-8 -*-
# import os
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker

# from app import create_app
# from app.main.patients.models import Patient, PatientStatus, PatientState, State

# from config import config_dict

# get_config_mode = os.environ.get('CONFIG_MODE', 'Debug')
# config_mode = config_dict[get_config_mode.capitalize()]

# app = create_app(config_mode) 
# engine = create_engine(config_mode.SQLALCHEMY_DATABASE_URI)

# Session = sessionmaker(bind = engine)
# session = Session()

# patients = session.query(Patient).all()
# for patient in patients:
#     print(patient)

# session.close()

import os
import json
from datetime import datetime, timedelta

import psycopg2

# Connect to our PostgreSQL
psqlConn = psycopg2.connect(dbname=os.getenv("DATABASE_NAME"),
                            user=os.getenv("DATABASE_USER"),
                            password=os.getenv("DATABASE_PASSWORD"),
                            host=os.getenv("DATABASE_HOST"))
psqlConn.autocommit = True
psqlCursor = psqlConn.cursor()

def psqlQuery(query_message):
    """
    Function that queries PostgreSQL
    If SELECT returns key-value paired objects
    """
    psqlCursor.execute(query_message)
    # print(query_message)
    try:
        columns = [col.name for col in psqlCursor.description]
        returnValue = []
        for row in psqlCursor:
            pairs = list(zip(columns, row))
            obj = {}
            for pair in pairs:
                obj[pair[0]] = pair[1]
            returnValue.append(obj)
    except Exception:
        returnValue = None
    return returnValue

"""
    Transfer is_found, is_infected, status_id (PatientStatus) to attrs
"""

statesResult = psqlQuery('SELECT * FROM "State"')
states = {}
for state in statesResult:
    states[state["id"]] = state["name"]
    states[state["name"]] = state["id"]

patients = psqlQuery('SELECT * FROM "Patient"')
for patient in patients:
    statuses = []
    if patient["attrs"].get("is_found", False):
        statuses.append("Найден")
    if patient["attrs"].get("is_infected", False):
        statuses.append("Инфицирован")
    if patient["attrs"].get("status", None):
        statuses.append(patient["attrs"].get("status"))

    patientStates = psqlQuery('SELECT * FROM "PatientState" WHERE patient_id=%d' % patient["id"])
    for status in statuses:
        found = False
        for patientState in patientStates:
            if states.get(patientState["id"]) == status:
                found = True
                break
        if not found:
            now = datetime.now()
            now = datetime.strftime(now, "%Y-%m-%dT%H:%M:%S")
            psqlQuery('INSERT INTO "PatientState" (state_id, patient_id, created_at, detection_date, attrs) VALUES (%d, %d, \'%s\',\'%s\', \'{}\');' % (
                states.get(status), patient["id"], now, now
            ))




