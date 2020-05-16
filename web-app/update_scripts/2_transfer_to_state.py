# -*- encoding: utf-8 -*-

import os
import json
from datetime import datetime, timedelta
from multiprocessing import Pool
import numpy as np
import time

import psycopg2

from app import constants as C

psqlConn = psycopg2.connect(dbname=os.getenv("DATABASE_NAME"),
                            user=os.getenv("DATABASE_USER"),
                            password=os.getenv("DATABASE_PASSWORD"),
                            host=os.getenv("DATABASE_HOST"))
psqlConn.autocommit = True
psqlCursor = psqlConn.cursor()

def psqlQuery(query_message, psqlCursor):
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

statusResult = psqlQuery('SELECT * FROM "PatientStatus"', psqlCursor)
status = {}
for state in statusResult:
    status[state["id"]] = state["name"]
    status[state["name"]] = state["id"]
print("status:",status)

statesResult = psqlQuery('SELECT * FROM "State"', psqlCursor)
states = {}
for state in statesResult:
    states[state["id"]] = state["name"]
    states[state["name"]] = state["id"]
print("states:",states)

"""
    Transfer is_found, is_infected, status_id (PatientStatus) to attrs
"""

def addPatientStates(patient, psqlCursor):
    statuses = []
    if patient.get("is_found", False):
        statuses.append("Найден")
    if patient.get("status_id", None):
        if "Найден" not in statuses:
            statuses.append("Найден")
        statuses.append(status.get(patient["status_id"]))
    if patient.get("is_infected", False):
        statuses.append("Инфицирован")
    patientStates = psqlQuery('SELECT * FROM "PatientState" WHERE patient_id=%d' % patient["id"], psqlCursor)
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
            if st == "Госпитализирован" and patient.get("hospital_id") is not None:
                psqlQuery("""
                    INSERT INTO "PatientState" 
                        (state_id, patient_id, created_at, detection_date, attrs) 
                    VALUES 
                        (%d, %d, \'%s\',\'%s\', \'{"hospital_id": %d}\');""" % (
                    states.get(st), patient["id"], now, now, patient["hospital_id"]
                ), psqlCursor)
            else:
                psqlQuery('INSERT INTO "PatientState" (state_id, patient_id, created_at, detection_date, attrs) VALUES (%d, %d, \'%s\',\'%s\', \'{}\');' % (
                    states.get(st), patient["id"], now, now
                ), psqlCursor)
    is_found = "false"
    if patient.get("is_found", False):
        is_found = "true"

    is_infected = "false"
    if patient.get("is_infected", False):
        is_infected = "true"
    psqlQuery('UPDATE "Patient" SET is_found=%s, is_infected=%s WHERE id=%d;' % (is_found, is_infected, patient["id"]), psqlCursor)

def handlePatients(patients):
    # Connect to our PostgreSQL
    psqlConn = psycopg2.connect(dbname=os.getenv("DATABASE_NAME"),
                                user=os.getenv("DATABASE_USER"),
                                password=os.getenv("DATABASE_PASSWORD"),
                                host=os.getenv("DATABASE_HOST"))
    psqlConn.autocommit = True
    psqlCursor = psqlConn.cursor()

    for i, patient in enumerate(patients):
        print(i+1, "/", len(patients))
        addPatientStates(patient, psqlCursor)

patients = psqlQuery('SELECT * FROM "Patient" ORDER BY id;', psqlCursor)

process_num = 16

pool = Pool(process_num)
pool.map(handlePatients, np.array_split(patients, process_num))

print("done")
