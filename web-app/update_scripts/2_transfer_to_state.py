# -*- encoding: utf-8 -*-

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

def getDetectionDate(patient_id, status_name):
    if status_name == "Найден":
        result = psqlQuery("""
            SELECT * FROM logging.t_history 
            WHERE tabname='Patient' AND new_val->>'id'='%d' AND 
                  new_val->>'is_found'='true' AND (old_val IS NULL OR old_val->>'is_found'='false')
            ;""" % (
            patient_id
        ))
        if result is None or len(result) == 0:
            return datetime.strftime(datetime.now(), "%Y-%m-%dT%H:%M:%S")
        return "T".join(result[0]["tstamp"].split())
    elif status_name == "Инфицирован":
        result = psqlQuery("""
            SELECT * FROM logging.t_history 
            WHERE tabname='Patient' AND new_val->>'id'='%d' AND 
                  new_val->>'is_infected'='true' AND (old_val IS NULL OR old_val->>'is_infected'='false')
            ;""" % (
            patient_id
        ))
        if result is None or len(result) == 0:
            return datetime.strftime(datetime.now(), "%Y-%m-%dT%H:%M:%S")
        return "T".join(result[0]["tstamp"].split())
    result = psqlQuery("""
        SELECT * FROM logging.t_history 
        WHERE tabname='Patient' AND new_val->>'id'='%d' AND 
                new_val->>'status_id'='%d' AND (old_val IS NULL OR old_val->>'status_id'!='%d')
        ;""" % (
        patient_id,
        status[status_name]
    ))
    if result is None or len(result) == 0:
        return datetime.strftime(datetime.now(), "%Y-%m-%dT%H:%M:%S")
    return "T".join(result[0]["tstamp"].split())

"""
    Transfer is_found, is_infected, status_id (PatientStatus) to attrs
"""

patients = psqlQuery('SELECT * FROM "Patient"')
for patient in patients:
    statuses = []
    if patient["attrs"].get("is_found", False):
        statuses.append("Найден")
    if patient["attrs"].get("is_infected", False):
        if "Найден" not in statuses:
            statuses.append("Найден")
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
            detection_date = getDetectionDate(patient["id"], status)
            psqlQuery('INSERT INTO "PatientState" (state_id, patient_id, created_at, detection_date, attrs) VALUES (%d, %d, \'%s\',\'%s\', \'{}\');' % (
                states.get(status), patient["id"], now, detection_date
            ))




