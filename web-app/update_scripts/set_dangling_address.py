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

patients = psqlQuery("""
    SELECT 
        id, home_address_id 
    FROM "Patient" p1 
    WHERE 
        created_by_id IS NULL AND 
        (SELECT 
            count(*) 
        FROM "Patient" p2 
            WHERE p2.home_address_id=p1.home_address_id) > 1;""")
for patient in patients:
    psqlQuery("""
        UPDATE "Patient" p1 SET 
            home_address_id=(
                CASE
                    WHEN (SELECT count(*) FROM "Patient" p2 WHERE p2.home_address_id=p1.home_address_id) > 1 THEN (
                            SELECT 
                                id 
                            FROM "Address" as a1 
                            WHERE 
                                a1.city=(SELECT city FROM "Address" a2 WHERE a2.id=p1.home_address_id LIMIT 1) AND
                                a1.street=(SELECT street FROM "Address" a2 WHERE a2.id=p1.home_address_id LIMIT 1) AND 
                                a1.country_id=(SELECT country_id FROM "Address" a2 WHERE a2.id=p1.home_address_id LIMIT 1) AND
                                (SELECT count(*) FROM "Patient" p2 WHERE p2.home_address_id=a1.id) = 0 
                            LIMIT 1)
                    ELSE p1.home_address_id
                END
            ) WHERE p1.id=%d;""" % patient["id"])
    # print(attrs)