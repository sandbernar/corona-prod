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
    address = psqlQuery('SELECT * FROM "Address" WHERE id=%d;' % (patient["home_address_id"]))[0]
    addressID = psqlQuery("""INSERT INTO "Address" (
        country_id,
        state,
        county,
        city,
        street,
        house,
        flat,
        building,
        lat,
        lng
    ) VALUES (
        %d,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %f,
        %f
    ) RETURNING id;""" % (
        address["country_id"],
        f"\'{address['state']}\'" if address["state"] is not None else "null",
        f"\'{address['county']}\'" if address["county"] is not None else "null",
        f"\'{address['city']}\'" if address["city"] is not None else "null",
        f"\'{address['street']}\'" if address["street"] is not None else "null",
        f"\'{address['house']}\'" if address["house"] is not None else "null",
        f"\'{address['flat']}\'" if address["flat"] is not None else "null",
        f"\'{address['building']}\'" if address["building"] is not None else "null",
        address["lat"] if address["lat"] is not None else "null",
        address["lng"] if address["lng"] is not None else "null"
    ))[0]
    psqlQuery('UPDATE "Patient" SET home_address_id=%d WHERE id=%d;' % (addressID["id"], patient["id"]))
