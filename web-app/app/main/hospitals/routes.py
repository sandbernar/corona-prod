# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from app.main import blueprint
from flask import render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app import login_manager, db
from app import constants as c
from jinja2 import TemplateNotFound
from app.main.hospitals.models import Hospital, Hospital_Type, Hospital_Nomenklatura
from app.main.models import Region, Patient
from datetime import datetime
import pandas as pd
import numpy as np
import math
from app.main.hospitals.forms import AddHospitalsDataForm, HospitalSearchForm, UpdateHospitalProfileForm
from app.main.util import get_regions, get_regions_choices
from flask_babelex import _
from app.main.routes import route_template

@blueprint.route('/hospitals')
@login_required
def all_hospitals():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))
    
    form = HospitalSearchForm(request.form)

    if not form.region.choices:
        form.region.choices = get_regions_choices(current_user)
    
    filt = dict()

    q = Hospital.query
    region = request.args.get("region", '-1')
    
    if not current_user.is_admin:
        filt["region_id"] = current_user.region_id
    else:
        if region != str(-1):
            filt["region_id"] = region
            form.region.default = region
            q = Hospital.query.filter_by(region_id = filt["region_id"])

    hospital_type = Hospital_Type.query.all()

    if not form.hospital_type.choices:
        form.hospital_type.choices = [ (-1, c.all_hospital_types) ] + [(r.id, r.name) for r in hospital_type]

    nomenklatura_ids = q.with_entities(Hospital.hospital_nomenklatura_id).all()
    nomenklatura_ids = np.unique([n.hospital_nomenklatura_id for n in nomenklatura_ids])
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
        page = int(request.args["page"])

    q = q.filter_by(**filt)
    
    total_len = q.count()

    for h in q.offset((page-1)*per_page).limit(per_page).all():
        patients_num = Patient.query.filter_by(hospital_id=h.id).count()
        hospitals.append((h, patients_num))

    max_page = math.ceil(total_len/per_page)

    form.process()    

    return route_template('hospitals/hospitals', hospitals=hospitals, form=form, page=page, max_page=max_page, total = total_len)


@blueprint.route('/add_hospital', methods=['GET', 'POST'])
def add_hospital():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

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

        # # else we can create the user
        patient = Patient(**new_dict)

        query = "{}, {}".format(patient.region, patient.home_address)
        results = geocoder.geocode(query)
        
        if len(results):
            patient.address_lat = results[0]['geometry']['lat']
            patient.address_lng = results[0]['geometry']['lng']        

        db.session.add(patient)
        db.session.commit()

        return route_template( 'hospitals/add_hospital', form=patient_form, added=True, error_msg=None)
        # return render_template( 'login/register.html', success='User created please <a href="/login">login</a>', form=patient_form)
    else:
        return route_template( 'hospitals/add_hospital', form=patient_form, added=False, error_msg=None)

@blueprint.route('/add_hospitals_csv', methods=['GET', 'POST'])
def add_hospitals_csv():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

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
        return route_template( 'hospitals/add_hospitals_csv', form=data_form, added=added)
        # return render_template( 'login/register.html', success='User created please <a href="/login">login</a>', form=patient_form)
    else:
        return route_template( 'hospitals/add_hospitals_csv', form=data_form, added=-1)


@blueprint.route('/hospital_profile', methods=['GET', 'POST'])
@login_required
def hospital_profile():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if "id" in request.args:
        hospital = Hospital.query.filter_by(id=request.args["id"]).first()
        
        if not hospital:
            return render_template('errors/error-404.html'), 404
        else:
            form = UpdateHospitalProfileForm()
            updated = False
            patients = []

            q = Patient.query.filter_by(hospital_id=hospital.id)

            page = 1
            per_page = 5

            if "page" in request.args:
                page = int(request.args["page"])

            total_len = q.count()

            for p in q.offset((page-1)*per_page).limit(per_page).all():
                patients.append(p)

            max_page = math.ceil(total_len/per_page)            
            # form.process()
            return route_template('hospitals/hospital_profile', hospital=hospital, form = form, updated = updated, 
                                                    patients=patients, total_patients=total_len, max_page=max_page, page=page)
    else:    
        return render_template('errors/error-500.html'), 500