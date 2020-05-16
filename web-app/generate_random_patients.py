import os
import json
from random import randrange, randint, choice
from datetime import datetime, timedelta

import psycopg2

import names
import pycountry
import geonamescache

class Main:
    def __setattr__(self, name, value):
        """
        Function doesnt set value if it is in blacklist
        """
        blacklist = ["", None, "-"]
        if value in blacklist:
            return
        elif type(value) == tuple and len(value) == 2 and value[1] == True:
            self.__dict__[name] = value[0]
        else:
            if type(value) == str:
                value = value.replace("'", "")
            self.__dict__[name] = value
    
    def insertQuery(self):
        """
        Function returns INSERT query with its class variables
        """
        variableNames = [key for key in self.__dict__.keys() if self.__dict__[key] is not None]
        if 'table_name' in variableNames:
            variableNames.remove('table_name')
        variableValues = []
        for key in variableNames:
            value = self.__dict__[key]
            if type(value) == str and value != "NULL":
                value = value.replace("'", "")
                variableValues.append(f"'{value}'")
            elif type(value) == dict:
                variableValues.append(f"'{json.dumps(value)}'")
            elif type(value) == bool:
                variableValues.append("true" if value else "false")
            else:
                variableValues.append(str(value))

        fieldNames = ",".join(variableNames)
        fieldValues = ",".join(variableValues)
        tableName = type(self).__name__
        if 'table_name' in self.__dict__:
            tableName = self.__dict__["table_name"]
        insertQuery = f"INSERT INTO \"{tableName}\" ({fieldNames}) VALUES ({fieldValues});"
        return insertQuery

class Address(Main):
    def __init__(self):
        self.id = (None, True)
        self.country_id = ("NULL", True)
        self.city = ("", True)
        self.street = ("", True)
        self.lat = "NULL"
        self.lng = "NULL"
    
    def insert(self):
        psqlQuery(self.insertQuery())
        self.id = psqlQuery("""
            SELECT id FROM "Address" WHERE 
                city='%s' AND
                street='%s' AND
                country_id=%d;
        """ % (self.city.replace("'", ""), self.street.replace("'", ""), self.country_id))[0]["id"]

class Patient(Main):
    def __init__(self):
        self.first_name = ("", True)
        self.second_name = ("", True)
        self.iin = ("", True)
        self.is_found = True
        self.dob = "1900-01-01"
        self.home_address_id = "NULL"

    def insert(self):
        psqlQuery(self.insertQuery())

def randomDate(start, end):
    """
    This function will return a random datetime between two datetime 
    objects.
    """
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = randrange(int_delta)
    return start + timedelta(seconds=random_second)

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

import argparse
ap = argparse.ArgumentParser()
ap.add_argument("-n", "--number", required=True, help="Number of Patients")
args = vars(ap.parse_args())

gc = geonamescache.GeonamesCache()
cities = gc.get_cities()
kzcities = [cities[city] for city in cities if cities[city].get('countrycode') == 'KZ']

travel_types = psqlQuery("SELECT * FROM \"TravelType\";")
local_type_id = None

for t in travel_types:
    if t["value"] == "local_type":
        local_type_id = t["id"]


for i in range(int(args['number'])):
    patient = Patient()
    patient.first_name = names.get_first_name()
    patient.second_name = names.get_last_name()
    patient.iin = f"{randint(0, 999999999):09}"
    bornDate = randomDate(datetime.strptime('01.01.1950', '%d.%m.%Y'), datetime.strptime('31.12.2001', '%d.%m.%Y'))
    bornDate = datetime.strftime(bornDate, "%Y-%m-%dT00:00:00+06:00")
    patient.dob = bornDate
    patient.created_date = datetime.strftime(datetime.today(), "%Y-%m-%dT00:00:00+06:00")
    patient.travel_type_id = local_type_id
    
    toPoint = kzcities[randint(0, len(kzcities)-1)]
    # insert address
    additionalLat = randint(0, 200)
    additionalLon = randint(0, 200)
    address = Address()
    address.country_id = 88
    address.city = toPoint['name'] + f"{additionalLat} {additionalLon}"
    address.lat = toPoint['latitude'] + float(additionalLat)/1000
    address.lng = toPoint['longitude'] + float(additionalLon)/1000
    address.insert()
    patient.home_address_id = address.id
    patient.insert()
