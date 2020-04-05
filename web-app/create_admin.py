# -*- encoding: utf-8 -*-
"""
License: Commercial
Copyright (c) 2019 - present AppSeed.us
"""

from flask_migrate import Migrate
from os import environ
from sys import exit
from flask_uploads import UploadSet, configure_uploads

from config import config_dict
from app import create_app, db

from app.login.models import User
from app.login.util import hash_pass
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine

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

app = create_app(config_mode) 
Migrate(app, db)
engine = create_engine(config_mode.SQLALCHEMY_DATABASE_URI)

from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind = engine)
session = Session()

user = User()
user.username = args["username"]
user.password = hash_pass(args["password"])

user.full_name = "test1"
user.organization = "test2"
user.telephone = "s"
user.email = "s"
user.region_id = 1
# user.username = args["username"]
# user.organization = Column(String)
# user.telephone = Column(String)
# user.email = Column(String)

session.add(user)
session.commit()

session.close()

