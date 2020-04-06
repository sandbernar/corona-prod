# -*- encoding: utf-8 -*-
"""
License: Commercial
Copyright (c) 2019 - present AppSeed.us
"""

from flask import Flask
from os import environ
from sys import exit

import config
from config import config_dict

from app.login.models import User
from app.login.util import hash_pass
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import argparse
ap = argparse.ArgumentParser()
ap.add_argument("-u", "--username", required=True,
	help="Login")
ap.add_argument("-p", "--password", required=True,
	help="Password")
args = vars(ap.parse_args())

get_config_mode = environ.get('CONFIG_MODE', 'Debug')
print(get_config_mode)

try:
    config_mode = config_dict[get_config_mode.capitalize()]
except KeyError:
    exit('Error: Invalid CONFIG_MODE environment variable entry.')


app = Flask(__name__, static_folder='main/static')
app.config.from_object(config)

engine = create_engine(config_mode.SQLALCHEMY_DATABASE_URI)

Session = sessionmaker(bind = engine)
session = Session()

user = User()
user.username = args["username"]
user.password = hash_pass(args["password"])

# user.username = args["username"]
# user.organization = Column(String)
# user.telephone = Column(String)
# user.email = Column(String)

session.add(user)
session.commit()

session.close()

