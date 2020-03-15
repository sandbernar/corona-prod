# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from app.home import blueprint
from flask import render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app import login_manager, db
from jinja2 import TemplateNotFound
from app.home.models import Patient
from datetime import datetime
from flask_uploads import UploadSet
import pandas as pd
from opencage.geocoder import OpenCageGeocode
import numpy as np

key = '6670b10323b541bdbbf3e39bf07b7e46'
geocoder = OpenCageGeocode(key)
from app.home.forms import PatientForm, UploadDataForm

@blueprint.route('/index')
@login_required
def index():
    
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    last_five_patients = []
    for p in Patient.query.order_by(Patient.id.desc()).limit(5).all():
        last_five_patients.append([p.full_name, p.is_found, p.in_hospital, p.hospital, p.visited_country])

    coordinates_patients = []
    for p in Patient.query.all():
        if p.address_lat:
            coordinates_patients.append((p.address_lat, p.address_lng, p.full_name))

    return route_template('index', last_five_patients=last_five_patients, coordinates_patients=coordinates_patients)

@blueprint.route('/tables')
@login_required
def tables():
    
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    patients = []
    for p in Patient.query.all():
        patients.append(p)

    return route_template('tables', patients=patients)

@blueprint.route('/<template>')
def route_template(template, **kwargs):

    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    try:
        total = len(Patient.query.filter_by().all())

        is_found = len(Patient.query.filter_by(is_found=True).all())
        ratio = 0 if total == 0 else is_found/total
        is_found_str  = str("{}/{} ({}%)".format(is_found, total, format(ratio*100, '.2f')))
        
        in_hospital  = len(Patient.query.filter_by(in_hospital=True).all())
        ratio = 0 if is_found == 0 else in_hospital/is_found
        in_hospital_str = str("{}/{} ({}%)".format(in_hospital, is_found, format(ratio*100, '.2f')))

        regions = len(np.unique([ p.region for p in Patient.query.filter_by().all()]))

        return render_template(template + '.html', stats = [str(total), is_found_str, in_hospital_str, regions], **kwargs)

    except TemplateNotFound:
        return render_template('error-404.html'), 404
    
    except:
        return render_template('error-500.html'), 500

## Patient Handling

@blueprint.route('/add_person', methods=['GET', 'POST'])
def add_patient():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    patient_form = PatientForm(request.form)
    if 'create' in request.form:

        # fullname  = request.form['fullname']
        # iin     = request.form['iin'   ]
        # dob = request.form['dob']
        new_dict = request.form.to_dict(flat=False)

        new_dict['arrival_date'] = datetime.strptime(request.form['arrival_date'], '%Y-%m-%d')
        new_dict['dob'] = datetime.strptime(request.form['dob'], '%Y-%m-%d')

        new_dict['is_found'] = (new_dict['is_found'] == 1)
        new_dict['in_hospital'] = (new_dict['in_hospital'] == 1)

        # user = User.query.filter_by(username=username).first()
        # if user:
        #     return render_template( 'login/register.html', msg='Username already registered', form=patient_form)

        # user = User.query.filter_by(email=email).first()
        # if user:
        #     return render_template( 'login/register.html', msg='Email already registered', form=patient_form)

        # # else we can create the user
        patient = Patient(**new_dict)
        db.session.add(patient)
        db.session.commit()

        return route_template( 'add_person', form=patient_form)
        # return render_template( 'login/register.html', success='User created please <a href="/login">login</a>', form=patient_form)
    else:
        return route_template( 'add_person', form=patient_form)

@blueprint.route('/add_data', methods=['GET', 'POST'])
def add_data():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    data_form = UploadDataForm()
    docs = UploadSet('documents', ['xls', 'xlsx', 'csv'])

    if data_form.validate_on_submit():
        filename = docs.save(data_form.file.data)
        file_url = docs.url(filename)
        print(docs.path(filename))

        patients = pd.read_excel(docs.path(filename))
        print(patients)

        for index, row in patients.iterrows():
            patient = Patient()
            patient.full_name = row["ФИО"]
            patient.iin = row["ИИН"]
            patient.dob = datetime.strptime(row["Дата рождения"], '%d.%m.%Y')
            patient.citizenship = row["Гражданство"]
            patient.pass_num = row["Номер паспорта"]
            patient.telephone = row["Номер мобильного телефона"]
            patient.arrival_date = datetime.strptime(row["Дата въезда"], '%d.%m.%Y')
            patient.flight_code = row["рейс"]
            patient.visited_country = row["Место и сроки пребывания в последние 14 дней до прибытия в Казахстан (укажите страну, область, штат и т.д.)"]
            patient.region = row["регион"]
            patient.home_address = row["Место жительство, либо предпологаемое место проживания"]
            patient.job = row["Место работы"]
            patient.is_found = True if row["Найден (да/нет)"].lower() == "да" else False
            patient.in_hospital = True if row["Госпитализирован (да/нет)"].lower() == "да" else False
            patient.hospital = row["Место госпитализации"] if not pd.isnull(row["Место госпитализации"]) else ""

            query = "{}, {}".format(patient.region, patient.home_address)
            results = geocoder.geocode(query)
            print(results)
            if len(results):
                patient.address_lat = results[0]['geometry']['lat']
                patient.address_lng = results[0]['geometry']['lng']

            db.session.add(patient)
            db.session.commit()

        # user = User.query.filter_by(username=username).first()
        # if user:
        #     return render_template( 'login/register.html', msg='Username already registered', form=patient_form)

        # user = User.query.filter_by(email=email).first()
        # if user:
        #     return render_template( 'login/register.html', msg='Email already registered', form=patient_form)

        # # else we can create the user
        return route_template( 'add_data', form=data_form)
        # return render_template( 'login/register.html', success='User created please <a href="/login">login</a>', form=patient_form)
    else:
        return route_template( 'add_data', form=data_form)