# -*- encoding: utf-8 -*-

import os
import json
from datetime import datetime, timedelta
import threading
import time

import psycopg2

from app import constants as C

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
    try:
        columns = [col.name for col in psqlCursor.description]
        returnValue = []
        for row in psqlCursor:
            pairs = list(zip(columns, row))
            obj = {}
            for pair in pairs:
                obj[pair[0]] = pair[1]
            returnValue.append(obj)
    except Exception as e:
        returnValue = None
    return returnValue

statusResult = psqlQuery('SELECT * FROM "PatientStatus"')
status = {}
for state in statusResult:
    status[state["id"]] = state["name"]
    status[state["name"]] = state["id"]
print("status:",status)

statesResult = psqlQuery('SELECT * FROM "State"')
states = {}
for state in statesResult:
    states[state["id"]] = state["name"]
    states[state["name"]] = state["id"]
print("states:",states)

"""
    Transfer is_found, is_infected, status_id (PatientStatus) to attrs
"""

def addPatientStates(patient):
    print(patient["id"])
    statuses = []
    if patient.get("is_found", False):
        statuses.append("Найден")
    if patient.get("status_id", None):
        if "Найден" not in statuses:
            statuses.append("Найден")
        statuses.append(status.get(patient["status_id"]))
    if patient.get("is_infected", False):
        statuses.append("Инфицирован")
    patientStates = psqlQuery('SELECT * FROM "PatientState" WHERE patient_id=%d' % patient["id"])
    for st in statuses:
        found = False
        if patientStates is not None:
            for patientState in patientStates:
                if states.get(patientState.get("state_id")) == st:
                    found = True
                    break
        if not found:
            now = datetime.strftime(datetime.now(), "%Y-%m-%dT%H:%M:%S")
            if st == "Нет Статуса":
                continue
            print(st, states.get(st))
            psqlQuery('INSERT INTO "PatientState" (state_id, patient_id, created_at, detection_date, attrs) VALUES (%d, %d, \'%s\',\'%s\', \'{}\');' % (
                states.get(st), patient["id"], now, now
            ))
    is_found = "false"
    if patient.get("is_found", False):
        is_found = "true"

    is_infected = "false"
    if patient.get("is_infected", False):
        is_infected = "true"
    psqlQuery('UPDATE "Patient" SET is_found=%s, is_infected=%s WHERE id=%d;' % (is_found, is_infected, patient["id"]))


patients = psqlQuery('SELECT * FROM "Patient" ORDER BY id;')
for patient in patients:
    addPatientStates(patient)

print("done")
