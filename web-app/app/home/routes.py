# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from app.home import blueprint
from flask import render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app import login_manager, db
from app import constants as c
from jinja2 import TemplateNotFound
from app.home.models import Patient, Hospital, Region, Hospital_Type, Hospital_Nomenklatura
from datetime import datetime
from flask_uploads import UploadSet
import pandas as pd
from opencage.geocoder import OpenCageGeocode
import numpy as np
from wtforms import SelectField
import math
from app.home.forms import PatientForm, UploadDataForm, TableSearchForm, UpdateProfileForm, AddHospitalsDataForm, HospitalSearchForm
import json

key = '6670b10323b541bdbbf3e39bf07b7e46'
geocoder = OpenCageGeocode(key)

@blueprint.route('/index', methods=['GET'])
@login_required
def index():
    
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    last_five_patients = []
    for p in Patient.query.order_by(Patient.id.desc()).limit(5).all():
        last_five_patients.append(p)

    coordinates_patients = []
    for p in Patient.query.all():
        if p.address_lat:
            coordinates_patients.append(p)

    patients = [ p for p in Patient.query.filter_by().all()]
    regions = dict()
    for p in patients:
        found_hospital = regions.get(p.region, (0, 0))
        regions[p.region] = (found_hospital[0] + (1 - int(p.is_found)), found_hospital[1] + (1 - int(p.in_hospital)))

    return route_template('index', last_five_patients=last_five_patients, coordinates_patients=coordinates_patients, regions=regions)

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
    
    # except:
        # return render_template('error-500.html'), 500

@blueprint.route("/get_hospital_by_region", methods=['POST'])
def get_hospital_by_region():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    region_id = request.form.get("region_id")
    hospital_type_id = request.form.get("hospital_type_id")

    hospitals = Hospital.query.filter_by(region_id=int(region_id), hospital_type_id=int(hospital_type_id))

    hospitals_options = "".join([ "<option value='{}'>{}</option>".format(h.id, h.name) for h in hospitals ])

    return json.dumps(hospitals_options, ensure_ascii=False)


@blueprint.route('/add_person', methods=['GET', 'POST'])
def add_patient():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    patient_form = PatientForm()
    regions = Region.query.all()

    if not patient_form.region_id.choices:
        patient_form.region_id.choices = [(r.id, r.name) for r in regions]
        patient_form.hospital_region_id.choices = [(r.id, r.name) for r in regions]

    hospitals = Hospital.query.all()
    if not patient_form.hospital_id.choices:
        patient_form.hospital_id.choices = [ (-1, c.no_hospital) ] + [(h.id, h.name) for h in hospitals]

    hospital_types = Hospital_Type.query.all()
    hospital_types = [(h.id, h.name) for h in hospital_types]

    if 'create' in request.form:
        new_dict = request.form.to_dict(flat=False)

        new_dict['arrival_date'] = datetime.strptime(request.form['arrival_date'], '%Y-%m-%d')
        new_dict['dob'] = datetime.strptime(request.form['dob'], '%Y-%m-%d')

        new_dict['is_found'] = int(new_dict['is_found'][0]) == 1
        new_dict['in_hospital'] = int(new_dict['in_hospital'][0]) == 1

        patient = Patient.query.filter_by(iin=new_dict["iin"][0]).first()
        if patient:
            msg = 'Пациент с ИИН {} уже есть в базе'.format(new_dict["iin"][0])
            return route_template( 'add_person', form=PatientForm(request.form), added=False, error_msg=msg)

        patient = Patient.query.filter_by(pass_num=new_dict["pass_num"][0]).first()
        if patient:
            msg = 'Пациент с Номером Паспорта {} уже есть в базе'.format(new_dict["pass_num"][0])
            return route_template( 'add_person', form=PatientForm(request.form), added=False, error_msg=msg)

        # # else we can create the user
        patient = Patient(**new_dict)

        region = Region.query.filter_by(id=new_dict["region_id"][0]).first()
        query = "{}, {}".format(region.name, patient.home_address)
        results = geocoder.geocode(query)
        
        if len(results):
            patient.address_lat = results[0]['geometry']['lat']
            patient.address_lng = results[0]['geometry']['lng']        

        db.session.add(patient)
        db.session.commit()

        return route_template( 'add_person', form=patient_form, added=True, error_msg=None)
        # return render_template( 'login/register.html', success='User created please <a href="/login">login</a>', form=patient_form)
    else:
        return route_template( 'add_person', form=patient_form, hospital_types=hospital_types, added=False, error_msg=None)

@blueprint.route('/add_data', methods=['GET', 'POST'])
def add_data():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    data_form = UploadDataForm()
    docs = UploadSet('documents', ['xls', 'xlsx', 'csv'])

    if data_form.validate_on_submit():
        filename = docs.save(data_form.file.data)
        file_url = docs.url(filename)

        patients = pd.read_excel(docs.path(filename))
        added = 0

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
            
            if len(results):
                patient.address_lat = results[0]['geometry']['lat']
                patient.address_lng = results[0]['geometry']['lng']

            db.session.add(patient)
            db.session.commit()
            added += 1

        # # else we can create the user
        return route_template( 'add_data', form=data_form, added=added)
        # return render_template( 'login/register.html', success='User created please <a href="/login">login</a>', form=patient_form)
    else:
        return route_template( 'add_data', form=data_form, added=-1)

@blueprint.route('/patients')
@login_required
def patients():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    form = TableSearchForm()
    regions = np.unique([ p.region for p in Patient.query.all()])

    regions = Region.query.all()

    if not form.region.choices:
        form.region.choices = [ (-1, c.all_regions) ] + [(r.id, r.name) for r in regions]

    patients = []
    filt = dict()

    if "region" in request.args:
        region = request.args["region"]
        if region != c.all_regions:
            if region in regions:
                filt["region"] = region
                form.region.default = region

    if "not_found" in request.args:
        filt["is_found"] = False
        form.not_found.default='checked'
    if "not_in_hospital" in request.args:
        filt["in_hospital"] = False
        form.not_in_hospital.default='checked'

    page = 1
    per_page = 5
    if "page" in request.args:
        page = int(request.args["page"][0])

    q = Patient.query.filter_by(**filt)
    
    total_len = q.count()

    for p in q.offset((page-1)*per_page).limit(per_page).all():
        patients.append(p)

    max_page = math.ceil(total_len/per_page)

    form.process()
    return route_template('patients', patients=patients, form=form, page=page, max_page=max_page, total = total_len)

@blueprint.route('/delete_patient', methods=['POST'])
@login_required
def delete_patient():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    if len(request.form):
        if "delete" in request.form:
            Patient.query.filter(Patient.id == request.form["delete"][0]).delete()
            db.session.commit()

    return redirect(url_for('home_blueprint.patients'))

@blueprint.route('/patient_profile', methods=['GET', 'POST'])
@login_required
def patient_profile():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    if "id" in request.args:
        patient = Patient.query.filter_by(id=request.args["id"]).first()
        
        if not patient:
            return render_template('error-404.html'), 404
        else:
            form = UpdateProfileForm()
            updated = False

            if len(request.form):
                if "hospital" in request.form:
                    patient.hospital = request.form["hospital"]
                
                patient.is_found = "is_found" in request.form 
                patient.in_hospital = "in_hospital" in request.form 
                db.session.add(patient)
                db.session.commit()
                updated = True
            
            form.hospital.default = patient.hospital

            if patient.is_found:
                form.is_found.default = 'checked'
            
            if patient.in_hospital:
                form.in_hospital.default='checked'


            age = 2020 - int(patient.dob.year)
            form.process()
            hospital_name = Hospital.query.filter_by(id=patient.hospital_id).first()
            return route_template('profile', patient=patient, age=age, hospital_name=hospital_name.name, form = form, updated = updated)
    else:    
        return render_template('error-500.html'), 500

# Hospitals

@blueprint.route('/hospitals')
@login_required
def all_hospitals():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))
    
    form = HospitalSearchForm(request.form)
    regions = Region.query.all()

    if not form.region.choices:
        form.region.choices = [ (-1, c.all_regions) ] + [(r.id, r.name) for r in regions]
    
    filt = dict()

    q = Hospital.query
    region = request.args.get("region", '-1')
    if region != str(-1):
        filt["region_id"] = region
        form.region.default = region
        q = Hospital.query.filter_by(region_id = filt["region_id"])

    hospital_type = Hospital_Type.query.all()

    if not form.hospital_type.choices:
        form.hospital_type.choices = [ (-1, c.all_hospital_types) ] + [(r.id, r.name) for r in hospital_type]

    nomenklatura_ids = q.with_entities(Hospital.hospital_nomenklatura_id).all()
    nomenklatura_ids = np.unique([n.hospital_nomenklatura_id for n in nomenklatura_ids])
    print(nomenklatura_ids)
    choices = [(-1, c.all_hospital_nomenklatura)]

    if not form.nomenklatura.choices:
        for i in nomenklatura_ids:
            choice = Hospital_Nomenklatura.query.filter_by(id = str(i)).first()
            choices.append((choice.id, choice.name))
        
        form.nomenklatura.choices = choices

    hospitals = []

    hospital_type = request.args.get("hospital_type", '-1')
    if hospital_type != str(-1):
        filt["hospital_type_id"] = hospital_type
        form.hospital_type.default = hospital_type

    nomenklatura = request.args.get("nomenklatura", '-1')
    if nomenklatura != str(-1):
        filt["hospital_nomenklatura_id"] = nomenklatura
        form.nomenklatura.default = nomenklatura        
    
    page = 1
    per_page = 10
    if "page" in request.args:
        page = int(request.args["page"][0])

    q = q.filter_by(**filt)
    
    total_len = q.count()

    for h in q.offset((page-1)*per_page).limit(per_page).all():
        hospitals.append(h)

    max_page = math.ceil(total_len/per_page)

    form.process()    

    return route_template('hospitals', hospitals=hospitals, form=form, page=page, max_page=max_page, total = total_len)


@blueprint.route('/add_hospital', methods=['GET', 'POST'])
def add_hospital():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    patient_form = PatientForm()
    if 'create' in request.form:

        # fullname  = request.form['fullname']
        # iin     = request.form['iin'   ]
        # dob = request.form['dob']
        new_dict = request.form.to_dict(flat=False)

        new_dict['arrival_date'] = datetime.strptime(request.form['arrival_date'], '%Y-%m-%d')
        new_dict['dob'] = datetime.strptime(request.form['dob'], '%Y-%m-%d')

        new_dict['is_found'] = int(new_dict['is_found'][0]) == 1
        new_dict['in_hospital'] = int(new_dict['in_hospital'][0]) == 1

        patient = Patient.query.filter_by(iin=new_dict["iin"][0]).first()
        if patient:
            msg = 'Пациент с ИИН {} уже есть в базе'.format(new_dict["iin"][0])
            return route_template( 'add_person', form=PatientForm(request.form), added=False, error_msg=msg)

        patient = Patient.query.filter_by(pass_num=new_dict["pass_num"][0]).first()
        if patient:
            msg = 'Пациент с Номером Паспорта {} уже есть в базе'.format(new_dict["pass_num"][0])
            return route_template( 'add_person', form=PatientForm(request.form), added=False, error_msg=msg)

        # # else we can create the user
        patient = Patient(**new_dict)

        query = "{}, {}".format(patient.region, patient.home_address)
        results = geocoder.geocode(query)
        
        if len(results):
            patient.address_lat = results[0]['geometry']['lat']
            patient.address_lng = results[0]['geometry']['lng']        

        db.session.add(patient)
        db.session.commit()

        return route_template( 'add_person', form=patient_form, added=True, error_msg=None)
        # return render_template( 'login/register.html', success='User created please <a href="/login">login</a>', form=patient_form)
    else:
        return route_template( 'add_person', form=patient_form, added=False, error_msg=None)

@blueprint.route('/add_hospitals_csv', methods=['GET', 'POST'])
def add_hospitals_csv():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    data_form = AddHospitalsDataForm()
    docs = UploadSet('documents', 'csv')

    if "submit" in request.form:
        filename = docs.save(data_form.file.data)
        file_url = docs.url(filename)

        hospitals = pd.read_csv(docs.path(filename))
        added = 0

        def get_default(l, index, default_val):
            try:
                return l[index]
            except IndexError:
                return default_val
        print(data_form.region)
        for index, row in hospitals.iterrows():
            hospital = Hospital()

            hospital.name = row[0]
            hospital.address = row[1]
            hospital.beds_amount = get_default(row, 2, 0)
            hospital.meds_amount = get_default(row, 3, 0)
            hospital.tests_amount = get_default(row, 4, 0)
            hospital.tests_used = get_default(row, 5, 0)
            hospital.region = request.form["region"]
            hospital.hospital_type = request.form["hospital_type"]

            query = "{}, {}".format(data_form.region, hospital.address)
            results = geocoder.geocode(query)
            
            if len(results):
                hospital.address_lat = results[0]['geometry']['lat']
                hospital.address_lng = results[0]['geometry']['lng']

            db.session.add(hospital)
            db.session.commit()
            added += 1

        # # else we can create the user
        return route_template( 'add_hospitals_csv', form=data_form, added=added)
        # return render_template( 'login/register.html', success='User created please <a href="/login">login</a>', form=patient_form)
    else:
        return route_template( 'add_hospitals_csv', form=data_form, added=-1)


@blueprint.route('/hospital_profile', methods=['GET', 'POST'])
@login_required
def hospital_profile():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    if "id" in request.args:
        hospital = Hospital.query.filter_by(id=request.args["id"]).first()
        
        if not hospital:
            return render_template('error-404.html'), 404
        else:
            form = UpdateProfileForm()
            updated = False

            # if len(request.form):
            #     if "hospital" in request.form:
            #         patient.hospital = request.form["hospital"]
                
            #     patient.is_found = "is_found" in request.form 
            #     patient.in_hospital = "in_hospital" in request.form 
            #     db.session.add(patient)
            #     db.session.commit()
            #     updated = True
            
            # form.hospital.default = patient.hospital

            # if patient.is_found:
            #     form.is_found.default = 'checked'
            
            # if patient.in_hospital:
            #     form.in_hospital.default='checked'


            # form.process()
            return route_template('hospital_profile', hospital=hospital, form = form, updated = updated)
    else:    
        return render_template('error-500.html'), 500