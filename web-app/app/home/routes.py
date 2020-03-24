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
from app.home.models import Patient, Hospital, Region, Hospital_Type, Hospital_Nomenklatura, PatientStatus, Foreign_Country, Infected_Country_Category, ContactedPersons
from datetime import datetime
from flask_uploads import UploadSet
import pandas as pd
from opencage.geocoder import OpenCageGeocode
import numpy as np
from wtforms import SelectField
import math
from app.home.forms import PatientForm, UploadDataForm, TableSearchForm, UpdateProfileForm, AddHospitalsDataForm, HospitalSearchForm, UpdateHospitalProfileForm
import json
import nltk
import dateutil.parser
# from postal.parser import parse_address
import re
import requests
from multiprocessing.pool import ThreadPool as threadpool
import itertools

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
            # print(p.address_lat)

    patients = [ p for p in Patient.query.filter_by().all()]
    regions = dict()
    for p in patients:
        found_hospital = regions.get(p.region, (0, 0))
        in_hospital_id = PatientStatus.query.filter_by(value=c.in_hospital[0]).first().id

        regions[p.region] = (found_hospital[0] + (1 - int(p.is_found)), found_hospital[1] + (1 - int(p.status_id == in_hospital_id)))
    print(coordinates_patients)

    return route_template('index', last_five_patients=last_five_patients, coordinates_patients=coordinates_patients, regions=regions, constants=c)

@blueprint.route('/<template>')
def route_template(template, **kwargs):
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    try:
        total = len(Patient.query.filter_by().all())

        is_found = len(Patient.query.filter_by(is_found=True).all())

        ratio = 0 if total == 0 else is_found/total
        is_found_str  = str("{}/{} ({}%)".format(is_found, total, format(ratio*100, '.2f')))
        

        in_hospital_status_id = PatientStatus.query.filter_by(value=c.in_hospital[0]).first().id
        in_hospital = len(Patient.query.filter_by(status_id=in_hospital_status_id).all())
        # in_hospital = 1
        ratio = 0 if is_found == 0 else in_hospital/is_found
        in_hospital_str = str("{}/{} ({}%)".format(in_hospital, is_found, format(ratio*100, '.2f')))

        regions = len(Region.query.all())

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

    patient_statuses = PatientStatus.query.all()
    if not patient_form.patient_status.choices:
        patient_form.patient_status.choices = [(s.value, s.name) for s in patient_statuses]

    hospital_types = Hospital_Type.query.all()
    hospital_types = [(h.id, h.name) for h in hospital_types]

    if 'create' in request.form:
        new_dict = request.form.to_dict(flat=False)

        new_dict['arrival_date'] = datetime.strptime(request.form['arrival_date'], '%Y-%m-%d')
        new_dict['dob'] = datetime.strptime(request.form['dob'], '%Y-%m-%d')

        status = request.form.get("patient_status", c.no_status[0])
        new_dict['status_id'] = PatientStatus.query.filter_by(value=status).first().id
        new_dict['is_found'] = int(new_dict['is_found'][0]) == 1
        new_dict['is_infected'] = int(new_dict['is_infected'][0]) == 1

        # patient = Patient.query.filter_by(iin=new_dict["iin"][0]).first()
        # if patient:
        #     msg = 'Пациент с ИИН {} уже есть в базе'.format(new_dict["iin"][0])
        #     return route_template( 'add_person', form=PatientForm(request.form), added=False, error_msg=msg)

        # patient = Patient.query.filter_by(pass_num=new_dict["pass_num"][0]).first()
        # if patient:
        #     msg = 'Пациент с Номером Паспорта {} уже есть в базе'.format(new_dict["pass_num"][0])
        #     return route_template( 'add_person', form=PatientForm(request.form), added=False, error_msg=msg)

        # # else we can create the user
        patient = Patient(**new_dict)
        patient.is_contacted_person = False
        
        lat_lng = get_lat_lng([(patient.home_address, Region.query.filter_by(id=patient.region_id).filter().name)])[0]

        patient.address_lat = lat_lng[0]
        patient.address_lng = lat_lng[1]

        db.session.add(patient)
        db.session.commit()

        return route_template( 'add_person', form=patient_form, added=True, error_msg=None)
        # return render_template( 'login/register.html', success='User created please <a href="/login">login</a>', form=patient_form)
    else:
        return route_template( 'add_person', form=patient_form, hospital_types=hospital_types, added=False, error_msg=None)

def get_lat_lng(patients):
    lat_lng = []
    for patient in patients:
        lat = None
        lng = None

        if not pd.isnull(patient[0]):
            home_address = patient[0].replace(".", ". ")
            region_name = patient[1]

            address_query = home_address

            params = dict(
                apiKey='S25QEDJvW3PCpRvVMoFmIJBHL01xokVyinW8F5Fj0pw',
            )

            home_address = re.sub(r"([0-9]+(\.[0-9]+)?)",r" \1 ", home_address).strip()
            # parsed_address = {k: v for (v, k) in parse_address(patient.home_address)}

            address_query = home_address
            # if "city" not in parsed_address:
            #     city = region_name if "city" not in parsed_address else parsed_address["city"]
            #     country = "Kazakhstan" if "country" not in parsed_address else parsed_address["country"]

            #     address_query = "city={};country={}".format(city, country)
                
            #     street = None

            #     if "road" in parsed_address:
            #         street = parsed_address["road"]
            #     elif "house" in parsed_address:
            #         street = parsed_address["house"]
                
            #     if street:
            #         address_query += ";street={}".format(street)

            #     if "house_number" in parsed_address:
            #         address_query += ";houseNumber={}".format(parsed_address["house_number"])
            #     params['qq'] = address_query
            # else:
            #     address_query = address_query.replace(parsed_address["city"], "")
            #     address_query = "{}, город {}".format(address_query, parsed_address["city"])
            params['q'] = "{}, {}".format(address_query, region_name)

            url = "https://geocode.search.hereapi.com/v1/geocode"


            resp = requests.get(url=url, params=params)
            data = resp.json()
                       
            if len(data["items"]):
                item = data["items"][0]

                if "access" in item:
                    item = item["access"][0]
                else:
                    item = item["position"]

                lat = item["lat"]
                lng = item["lng"]
            
        lat_lng.append((lat, lng))

    return lat_lng

@blueprint.route('/add_data', methods=['GET', 'POST'])
def add_data():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    data_form = UploadDataForm()
    docs = UploadSet('documents', ['xls', 'xlsx', 'csv'])

    found_hospitals = dict()

    if data_form.validate_on_submit():
        filename = docs.save(data_form.file.data)
        file_url = docs.url(filename)

        patients = pd.read_excel(docs.path(filename))
        added = 0
        regions = Region.query.all()

        created_patients = []

        def create_patient(row):
            patient = Patient()
            # print(row)
            patient.full_name = row["ФИО"]
            patient.iin = row["ИИН"]

            if isinstance(row["Дата рождения"], pd._libs.tslibs.nattype.NaTType):
                patient.dob = datetime(1000, 1, 1)
            else:
                if not isinstance(row["Дата рождения"], datetime):
                    try:
                        patient.dob = dateutil.parser.parse(row["Дата рождения"])
                    except TypeError:
                        patient.dob = datetime(1000, 1, 1)
                else:
                    patient.dob = row["Дата рождения"]

            patient.citizenship = row["Гражданство"]
            patient.pass_num = row["Номер паспорта"]
            patient.telephone = row["Номер мобильного телефона"]

            try:
                patient.arrival_date = dateutil.parser.parse(row["Дата въезда"])
            except TypeError:
                patient.arrival_date = datetime(1000, 1, 1)           

            patient.flight_code = row["рейс"]
            patient.visited_country = row["Место и сроки пребывания в последние 14 дней до прибытия в Казахстан (укажите страну, область, штат и т.д.)"]
            
            region_name = ""
            if not pd.isnull(row["регион"]):
                regions_distance = []
                preprocessed_region = row["регион"].lower().split(" ")

                for r in regions:
                    preprocessed_r = r.name.lower().replace("(", "").replace(")", "").split(" ")
                    common_elements = len(set(preprocessed_region).intersection(preprocessed_r))
                    regions_distance.append(common_elements)

                if np.max(regions_distance) == len(preprocessed_region):
                    region = regions[np.argmax(regions_distance)]
                else:
                    regions_distance = []
                    for r in regions:
                        regions_distance.append(nltk.edit_distance(row["регион"], r.name))

                    region = regions[np.argmin(regions_distance)]
                
                patient.region_id = region.id
                region_name = region.name
            else:
                patient.region_id = Region.query.filter_by(name="Вне РК").first().id

            patient.home_address = row["Место жительство, либо предпологаемое место проживания"]

            patient.job = row["Место работы"]
            patient.is_found = True if row["Найден (да/нет)"].lower() == "да" else False
    
            hospitals = Hospital.query.filter_by(region_id=patient.region_id).all()

            if not pd.isnull(row["Место госпитализации"]):
                hospital_lower = row["Место госпитализации"].lower()

                status = None
                if "вылет" in hospital_lower or "транзит" in hospital_lower:
                    status = c.is_transit
                elif "карантин" in hospital_lower:
                    status = c.is_home
                elif len(hospital_lower):
                    status = c.in_hospital
                    hospital = found_hospitals.get(row["Место госпитализации"], None)

                    if not hospital:
                        hospital_distances = []
                        hospital_name = row["Место госпитализации"]

                        for h in hospitals:
                            hospital_distances.append(nltk.edit_distance(hospital_name, h.name, True))

                        hospital = hospitals[np.argmin(hospital_distances)]
                        patient.hospital_id = hospital.id
                else:
                    status = c.no_status
                
                if status != None:
                    patient.status_id = PatientStatus.query.filter_by(value=status[0]).first().id
            else:
                patient.status_id = PatientStatus.query.filter_by(value=c.no_status[0]).first().id    


            created_patients.append(patient)

        patients.apply(lambda row: create_patient(row), axis=1)
        added = len(patients)

        lat_lng_data = []
        for p in created_patients:
            lat_lng_data.append((p.home_address, Region.query.filter_by(id=p.region_id).first().name))

        p_num = 16
        pool = threadpool(processes = p_num)
        lat_lng = pool.map(get_lat_lng, np.array_split(lat_lng_data, p_num))
        pool.close()
        pool.join()

        lat_lng = list(itertools.chain.from_iterable(lat_lng))

        for p, coordinates in zip(created_patients, lat_lng):
            p.address_lat = coordinates[0]
            p.address_lng = coordinates[1]

            db.session.add(p)

        db.session.commit()      

        # else we can create the user
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
    regions = Region.query.all()

    if not form.region.choices:
        form.region.choices = [ (-1, c.all_regions) ] + [(r.id, r.name) for r in regions]

    patients = []
    filt = dict()

    if "region" in request.args:
        region = request.args["region"]
        if region != -1:
            filt["region_id"] = region
            form.region.default = region

    if "not_found" in request.args:
        filt["is_found"] = False
        form.not_found.default='checked'
    q = Patient.query.filter_by(**filt)

    if "not_in_hospital" in request.args:
        in_hospital_id = PatientStatus.query.filter_by(value=c.in_hospital[0]).first().id
        q = Patient.query.filter(Patient.status_id != in_hospital_id).filter_by(**filt)

        form.not_in_hospital.default='checked'

    page = 1
    per_page = 5
    if "page" in request.args:
        page = int(request.args["page"][0])

    total_len = q.count()

    for p in q.offset((page-1)*per_page).limit(per_page).all():
        contacted = ContactedPersons.query.filter_by(patient_id=p.id).all()
        p.contacted_count = len(contacted)
        p.contacted_found_count = 0

        for contact in contacted:
            p = Patient.query.filter_by(id=contact.person_id).first()
            if p and p.is_found:
                p.contacted_found_count += 1

        patients.append(p)


    max_page = math.ceil(total_len/per_page)

    form.process()
    return route_template('patients', patients=patients, form=form, page=page, max_page=max_page, total = total_len, constants=c)

@blueprint.route('/delete_patient', methods=['POST'])
@login_required
def delete_patient():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    if len(request.form):
        if "delete" in request.form:
            patient_id = request.form["delete"]
            patient = Patient.query.filter(Patient.id == patient_id)
            
            if patient.first().is_contacted_person:
                ContactedPersons.query.filter_by(person_id=patient_id).delete()
            # else:


            patient.delete()
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
            form = UpdateProfileForm(request.form)
            updated = False

            regions = Region.query.all()

            if not form.hospital_region_id.choices:
                form.hospital_region_id.choices = [(r.id, r.name) for r in regions]

            hospital_types = Hospital_Type.query.all()
            form.hospital_type.choices = [(h.id, h.name) for h in hospital_types]

            if len(request.form):
                if "hospital" in request.form:
                    patient.hospital = request.form["hospital"]
                
                status = None
                if "is_found" in request.form:
                    patient.is_found = True
                else:
                    patient.is_found = False

                print(request.form)
                if "in_hospital" in request.form:
                    status = c.in_hospital
                elif "is_home" in request.form:
                    status = c.is_home
                elif "is_transit" in request.form:
                    status = c.is_transit

                if status:
                    patient.status_id = PatientStatus.query.filter_by(value=status[0]).first().id
                
                if "hospital_id" in request.form:
                    patient_hospital = Hospital.query.filter_by(id=request.form['hospital_id']).first()

                    if patient_hospital:
                        patient.hospital_id = patient_hospital.id

                db.session.add(patient)
                db.session.commit()
                updated = True
            
            hospital_region_id = patient.region_id
            hospital_type_id = hospital_types[0].id

            if patient.hospital:
                hospital_region_id = patient.hospital.region_id
                hospital_type_id = patient.hospital.hospital_type_id

            form.hospital_region_id.default = hospital_region_id
            form.hospital_type.default = hospital_type_id

            if patient.is_found:
                form.is_found.default = 'checked'

            if patient.is_infected:
                form.is_infected.default = 'checked'            

            if patient.status:
                if patient.status.value == c.in_hospital[0]:
                    form.in_hospital.default = 'checked'
                elif patient.status.value == c.is_home[0]:
                    form.is_home.default = 'checked'
                elif patient.status.value == c.is_transit[0]:
                    form.is_transit.default = 'checked'                         

            hospitals = Hospital.query.filter_by(region_id=hospital_region_id, hospital_type_id=hospital_type_id).all()
            if not form.hospital_id.choices:
                form.hospital_id.choices = [(h.id, h.name) for h in hospitals]

            hospital_name = None
            if patient.hospital:
                form.hospital_id.default = patient.hospital.id
                hospital_name = Hospital.query.filter_by(id=patient.hospital.id).first().name

            today = datetime.today()
            age =  today.year - patient.dob.year - ((today.month, today.day) < (patient.dob.month, patient.dob.day))

            form.process()
            return route_template('profile', patient=patient, age=age, hospital_name=hospital_name, form = form, updated = updated)
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
        patients_num = Patient.query.filter_by(hospital_id=h.id).count()
        hospitals.append((h, patients_num))

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
            form = UpdateHospitalProfileForm()
            updated = False
            patients = []

            q = Patient.query.filter_by(hospital_id=hospital.id)

            page = 1
            per_page = 5

            if "page" in request.args:
                page = int(request.args["page"][0])

            total_len = q.count()

            for p in q.offset((page-1)*per_page).limit(per_page).all():
                patients.append(p)

            max_page = math.ceil(total_len/per_page)            
            # form.process()
            return route_template('hospital_profile', hospital=hospital, form = form, updated = updated, 
                                                    patients=patients, total_patients=total_len, max_page=max_page, page=page)
    else:    
        return render_template('error-500.html'), 500

@blueprint.route('/countries_categories')
@login_required
def countries_categories():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    categories = Infected_Country_Category.query.all()

    return route_template('countries_categories', categories=categories)


@blueprint.route('/contacted_persons', methods=['GET', 'POST'])
@login_required
def contacted_persons():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    form = TableSearchForm()
    regions = Region.query.all()

    if not form.region.choices:
        form.region.choices = [ (-1, c.all_regions) ] + [(r.id, r.name) for r in regions]

    patients = []
    filt = dict()

    if "id" in request.args:
        # region = request.args["region"]
        # if region != -1:
            # filt["region_id"] = region
            # form.region.default = region

    # if "not_found" in request.args:
    #     filt["is_found"] = False
    #     form.not_found.default='checked'
        q = ContactedPersons.query.filter_by(patient_id=request.args["id"])
        patient = Patient.query.filter_by(id = request.args["id"]).first()

    # if "not_in_hospital" in request.args:
    #     in_hospital_id = PatientStatus.query.filter_by(value=c.in_hospital[0]).first().id
    #     q = Patient.query.filter(Patient.status_id != in_hospital_id).filter_by(**filt)

    #     form.not_in_hospital.default='checked'

        page = 1
        per_page = 5
        if "page" in request.args:
            page = int(request.args["page"][0])

        total_len = q.count()

        for p in q.offset((page-1)*per_page).limit(per_page).all():
            patients.append(Patient.query.filter_by(id=p.person_id).first())

        max_page = math.ceil(total_len/per_page)

        form.process()
        return route_template('contacted_persons', patients=patients, form=form, page=page, 
                                        max_page=max_page, total = total_len, constants=c, patient=patient)

    return render_template('error-500.html'), 500


@blueprint.route('/add_contacted_person', methods=['GET', 'POST'])
def add_contacted_person():
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

    patient_statuses = PatientStatus.query.all()
    if not patient_form.patient_status.choices:
        patient_form.patient_status.choices = [(s.value, s.name) for s in patient_statuses]

    hospital_types = Hospital_Type.query.all()
    hospital_types = [(h.id, h.name) for h in hospital_types]

    if 'create' in request.form and "id" in request.args:
        new_dict = request.form.to_dict(flat=False)

        new_dict['dob'] = datetime.strptime(request.form['dob'], '%Y-%m-%d')

        status = request.form.get("patient_status", c.no_status[0])
        new_dict['status_id'] = PatientStatus.query.filter_by(value=status).first().id
        new_dict['is_found'] = int(new_dict['is_found'][0]) == 1

        # else we can create the user
        patient = Patient(**new_dict)
        patient.is_contacted_person = True
        
        lat_lng = get_lat_lng([(patient.home_address, Region.query.filter_by(id=patient.region_id).filter().name)])[0]

        patient.address_lat = lat_lng[0]
        patient.address_lng = lat_lng[1]

        db.session.add(patient)
        db.session.commit()

        contacted = ContactedPersons(patient_id=request.args["id"], person_id=patient.id)
        db.session.add(contacted)
        db.session.commit()

        return redirect("/contacted_persons?id={}".format(request.args["id"]))

        return route_template( 'add_contacted_person', form=patient_form, added=True, error_msg=None)
        # return render_template( 'login/register.html', success='User created please <a href="/login">login</a>', form=patient_form)
    else:
        return route_template( 'add_contacted_person', form=patient_form, hospital_types=hospital_types, added=False, error_msg=None)