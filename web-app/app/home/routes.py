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
from app.home.models import (Patient, Hospital, Region, Hospital_Type, Hospital_Nomenklatura, PatientStatus, Foreign_Country, 
    Infected_Country_Category, ContactedPersons, FlightCode, TravelType)
from datetime import datetime
from flask_uploads import UploadSet
import pandas as pd
from opencage.geocoder import OpenCageGeocode
import numpy as np
from wtforms import SelectField
import math
from app.home.forms import (PatientForm, UploadDataForm, TableSearchForm, UpdateProfileForm, AddHospitalsDataForm, HospitalSearchForm, 
    UpdateHospitalProfileForm, CreateUserForm, UpdateUserForm)
import json
import nltk
import dateutil.parser
import re
import requests
from multiprocessing.pool import ThreadPool as threadpool
import itertools
from app.base.models import User
from app.home.util import get_regions, get_regions_choices, get_flight_code
from app.base.util import hash_pass
from sqlalchemy import func

@blueprint.route('/index', methods=['GET'])
@login_required
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    q = Patient.query
    
    if not current_user.is_admin:
        q = q.filter_by(region_id=current_user.region_id)

    last_five_patients = []
    for p in q.order_by(Patient.id.desc()).limit(5).all():
        last_five_patients.append(p)

    coordinates_patients = []
    for p in q.all():
        if p.address_lat:
            coordinates_patients.append(p)

    patients = q.all()
    regions = dict()
    for p in patients:
        found_hospital = regions.get(p.region, (0, 0))
        in_hospital_id = PatientStatus.query.filter_by(value=c.in_hospital[0]).first().id

        regions[p.region] = (found_hospital[0] + (1 - int(p.is_found)), found_hospital[1] + (1 - int(p.status_id == in_hospital_id)))

    return route_template('index', last_five_patients=last_five_patients, coordinates_patients=coordinates_patients, regions=regions, constants=c)

@blueprint.route('/<template>')
def route_template(template, **kwargs):
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))
    try:
        q = Patient.query
    
        if not current_user.is_admin:
            q = q.filter_by(region_id=current_user.region_id)        

        total = len(q.filter_by().all())

        is_found = len(q.filter_by(is_found=True).all())

        ratio = 0 if total == 0 else is_found/total
        is_found_str  = str("{}/{} ({}%)".format(is_found, total, format(ratio*100, '.2f')))
        
        in_hospital_status_id = PatientStatus.query.filter_by(value=c.in_hospital[0]).first().id
        in_hospital = len(q.filter_by(status_id=in_hospital_status_id).all())
        # in_hospital = 1
        ratio = 0 if is_found == 0 else in_hospital/is_found
        in_hospital_str = str("{}/{} ({}%)".format(in_hospital, is_found, format(ratio*100, '.2f')))

        regions = "Весь РК" if current_user.region_id == None else Region.query.filter_by(id=current_user.region_id).first().name

        return render_template(template + '.html', stats = [str(total), is_found_str, in_hospital_str, regions], **kwargs)

    except TemplateNotFound:
        return render_template('errors/error-404.html'), 404
    
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

    if not patient_form.region_id.choices:
        patient_form.region_id.choices = get_regions_choices(current_user, False)
        patient_form.hospital_region_id.choices = get_regions_choices(current_user, False)

    if not patient_form.travel_type_id.choices:
        patient_form.travel_type_id.choices = [ (typ.id, typ.name) for typ in TravelType.query.all() ]

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

        if new_dict['flight_code'][0]:
            new_dict['flight_code_id'] = get_flight_code(new_dict['flight_code'][0])
        else:
            new_dict['flight_code_id'] = None

        del new_dict['flight_code']

        # else we can create the user
        patient = Patient(**new_dict)
        patient.is_contacted_person = False
        
        lat_lng = get_lat_lng([(patient.home_address, Region.query.filter_by(id=patient.region_id).first().name)])[0]

        patient.address_lat = lat_lng[0]
        patient.address_lng = lat_lng[1]

        db.session.add(patient)
        db.session.commit()

        return redirect("/patient_profile?id={}&success".format(patient.id))
    else:
        return route_template( 'patients/add_person', form=patient_form, hospital_types=hospital_types, added=False, error_msg=None)

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
        regions = get_regions(current_user)

        created_patients = []

        def create_patient(row):
            patient = Patient()
            patient.full_name = row["ФИО"]
            patient.iin = row["ИИН"]

            if isinstance(row["Дата рождения"], pd._libs.tslibs.nattype.NaTType):
                patient.dob = datetime(1000, 1, 1)
            else:
                if not isinstance(row["Дата рождения"], datetime):
                    try:
                        patient.dob = dateutil.parser.parse(row["Дата рождения"])
                    except (TypeError, ValueError) as e:
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

            patient.flight_code_id = get_flight_code(row["рейс"])
            patient.travel_type_id = TravelType.query.filter_by(value = c.flight_type[0]).first().id

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

                        if len(hospital_distances):
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
        return route_template( 'patients/add_data', form=data_form, added=added)
        # return render_template( 'login/register.html', success='User created please <a href="/login">login</a>', form=patient_form)
    else:
        return route_template( 'patients/add_data', form=data_form, added=-1)

@blueprint.route('/patients')
@login_required
def patients():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    form = TableSearchForm()

    if not form.region.choices:
        form.region.choices = get_regions_choices(current_user)

    patients = []
    filt = dict()

    if not current_user.is_admin:
        filt["region_id"] = current_user.region_id
    else:
        if "region" in request.args:
            region = request.args["region"]
            if region != '-1':
                filt["region_id"] = region
                form.region.default = region

    if "flight_code" in request.args:
        flight_code = request.args["flight_code"]
        if flight_code != '' and flight_code != c.all_flight_codes:
            fc = FlightCode.query.filter_by(name=flight_code).first()
            if fc:
                filt["flight_code_id"] = fc.id
                form.flight_code.default = fc.name
        else:
            form.flight_code.default = c.all_flight_codes

    if "not_found" in request.args:
        filt["is_found"] = False
        form.not_found.default='checked'

    if "is_infected" in request.args:
        filt["is_infected"] = True
        form.is_infected.default='checked'

    q = Patient.query.filter_by(**filt)

    if "not_in_hospital" in request.args:
        in_hospital_id = PatientStatus.query.filter_by(value=c.in_hospital[0]).first().id
        q = Patient.query.filter(Patient.status_id != in_hospital_id).filter_by(**filt)

        form.not_in_hospital.default='checked'

    if "full_name" in request.args:
        q = q.filter(func.lower(Patient.full_name).contains(request.args["full_name"].lower()))
        form.full_name.default = request.args["full_name"]

    if "iin" in request.args:
        q = q.filter(Patient.iin.contains(request.args["iin"]))
        form.iin.default = request.args["iin"]

    if "telephone" in request.args:
        q = q.filter(Patient.telephone.contains(request.args["telephone"]))
        form.telephone.default = request.args["telephone"]        

    page = 1
    per_page = 10
    if "page" in request.args:
        page = int(request.args["page"])

    total_len = q.count()

    for p in q.offset((page-1)*per_page).limit(per_page).all():
        contacted = ContactedPersons.query.filter_by(patient_id=p.id).all()

        p.contacted_count = len(contacted)
        p.contacted_found_count = 0

        for contact in contacted:
            contacted_person = Patient.query.filter_by(id=contact.person_id).first()
            if contacted_person and contacted_person.is_found:
                p.contacted_found_count += 1

        patients.append(p)

    max_page = math.ceil(total_len/per_page)

    flight_codes_list = [c.all_flight_codes] + [ code.name for code in FlightCode.query.all() ]

    change = None
    error_msg = None

    if "delete" in request.args:
        change = "Пользователь успешно удален"

    form.process()
    return route_template('patients/patients', patients=patients, form=form, page=page, max_page=max_page, total = total_len, 
                            constants=c, flight_codes_list=flight_codes_list, change=change, error_msg=error_msg)

@blueprint.route('/delete_patient', methods=['POST'])
@login_required
def delete_patient():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))
    
    return_url = "{}?delete".format(url_for('home_blueprint.patients'))

    if len(request.form):
        if "delete" in request.form:
            patient_id = request.form["delete"]
            patient = Patient.query.filter(Patient.id == patient_id)
            
            if patient.first().is_contacted_person:
                q = ContactedPersons.query.filter_by(person_id=patient_id)
                return_url = "{}?id={}".format(url_for('home_blueprint.contacted_persons'), q.first().patient_id)
                q.delete()

            patient.delete()
            db.session.commit()

    return redirect(return_url)

@blueprint.route('/patient_profile', methods=['GET', 'POST'])
@login_required
def patient_profile():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    if "id" in request.args:
        patient = Patient.query.filter_by(id=request.args["id"]).first()
      
        if not patient:
            return render_template('errors/error-404.html'), 404
        else:
            form = UpdateProfileForm(request.form)
            change = None

            regions = Region.query.all()

            if not form.hospital_region_id.choices:
                form.region_id.choices = [(r.id, r.name) for r in regions]
                form.hospital_region_id.choices = [(r.id, r.name) for r in regions]

            if not form.travel_type_id.choices:
                form.travel_type_id.choices = [c.unknown] + [ (typ.id, typ.name) for typ in TravelType.query.all() ]            

            hospital_types = Hospital_Type.query.all()
            form.hospital_type.choices = [(h.id, h.name) for h in hospital_types]
            form.flight_code_id.choices = [c.unknown] + [ (code.id, code.name) for code in FlightCode.query.all() ]

            if len(request.form):
                if "hospital" in request.form:
                    patient.hospital = request.form["hospital"]
                
                status = None
                patient.is_found = "is_found" in request.form
                patient.is_infected = "is_infected" in request.form

                if "in_hospital" in request.form:
                    status = c.in_hospital
                elif "is_home" in request.form:
                    status = c.is_home
                elif "is_transit" in request.form:
                    status = c.is_transit
                else:
                    status = c.no_status

                if status:
                    patient.status_id = PatientStatus.query.filter_by(value=status[0]).first().id
                
                if "hospital_id" in request.form:
                    patient_hospital = Hospital.query.filter_by(id=request.form['hospital_id']).first()

                    if patient_hospital:
                        patient.hospital_id = patient_hospital.id

                # Update parameters
                if request.form['full_name']:
                    patient.full_name = request.form['full_name']

                if request.form['iin']:
                    patient.iin = str(request.form['iin'])

                if request.form['dob']:
                    patient.dob = request.form['dob']

                if request.form['citizenship']:
                    patient.citizenship = request.form['citizenship']

                patient.region_id = request.form['region_id']
                
                if "travel_type_id" in request.form:
                    patient.travel_type_id = request.form['travel_type_id']

                if request.form['home_address']:
                    if patient.home_address != request.form['home_address']:
                        patient.home_address = request.form['home_address']

                        lat_lng = get_lat_lng([(patient.home_address, Region.query.filter_by(id=patient.region_id).first().name)])[0]

                        patient.address_lat = lat_lng[0]
                        patient.address_lng = lat_lng[1]

                if "flight_code_id" in request.form:
                    patient.flight_code_id = int(request.form['flight_code_id'])

                if "visited_country" in request.form:
                    patient.visited_country = request.form['visited_country']

                db.session.add(patient)
                db.session.commit()
                change = "Профиль успешно обновлен"

            hospital_region_id = patient.region_id
            hospital_type_id = hospital_types[0].id

            if patient.hospital:
                hospital_region_id = patient.hospital.region_id
                hospital_type_id = patient.hospital.hospital_type_id

            form.region_id.default = patient.region_id
            form.flight_code_id.default = patient.flight_code_id

            form.travel_type_id.default = patient.travel_type_id

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

            if "success" in request.args:
                change = "Пользователь {} успешно добавлен".format(patient.full_name)

            form.process()

            return route_template('patients/profile', patient=patient, age=age, hospital_name=hospital_name, form = form, change = change)
    else:    
        return render_template('errors/error-500.html'), 500

# Hospitals

@blueprint.route('/hospitals')
@login_required
def all_hospitals():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))
    
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

        return route_template( 'hospitals/add_hospital', form=patient_form, added=True, error_msg=None)
        # return render_template( 'login/register.html', success='User created please <a href="/login">login</a>', form=patient_form)
    else:
        return route_template( 'hospitals/add_hospital', form=patient_form, added=False, error_msg=None)

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
        return redirect(url_for('base_blueprint.login'))

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
    regions = get_regions(current_user)

    if not form.region.choices:
        form.region.choices = [ (-1, c.all_regions) ] + [(r.id, r.name) for r in regions]

    patients = []
    filt = dict()

    if "id" in request.args:
        patient = Patient.query.filter_by(id=request.args["id"]).first()

        if patient:
            if patient.is_contacted_person:
                q = ContactedPersons.query.filter_by(person_id=request.args["id"])
            else:
                q = ContactedPersons.query.filter_by(patient_id=request.args["id"])

            page = 1
            per_page = 5
            if "page" in request.args:
                page = int(request.args["page"])

            total_len = q.count()

            for contact in q.offset((page-1)*per_page).limit(per_page).all():
                p_id = contact.patient_id if patient.is_contacted_person else contact.person_id
                patients.append(Patient.query.filter_by(id=p_id).first())

            max_page = math.ceil(total_len/per_page)

            form.process()
            return route_template('patients/contacted_persons', patients=patients, form=form, page=page, 
                                            max_page=max_page, total = total_len, constants=c, patient=patient)
        else:
            return render_template('errors/error-404.html'), 404

    return render_template('errors/error-500.html'), 500


@blueprint.route('/add_contacted_person', methods=['GET', 'POST'])
def add_contacted_person():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    patient_form = PatientForm()
    regions = get_regions(current_user)

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
    
    if not request.args.get("id", False):
        return route_template("errors/error-500.html")

    main_patient_id = Patient.query.filter_by(id=request.args["id"]).first()
    if main_patient_id == None:
        return route_template("errors/error-500.html")
    else:
        main_patient_id = main_patient_id.id

    if 'create' in request.form:
        new_dict = request.form.to_dict(flat=False)

        new_dict['dob'] = datetime.strptime(request.form['dob'], '%Y-%m-%d')

        status = request.form.get("patient_status", c.no_status[0])
        new_dict['status_id'] = PatientStatus.query.filter_by(value=status).first().id
        new_dict['is_found'] = int(new_dict['is_found'][0]) == 1

        # else we can create the user
        patient = Patient(**new_dict)
        patient.is_contacted_person = True
        
        lat_lng = get_lat_lng([(patient.home_address, Region.query.filter_by(id=patient.region_id).first().name)])[0]

        patient.address_lat = lat_lng[0]
        patient.address_lng = lat_lng[1]

        db.session.add(patient)
        db.session.commit()

        contacted = ContactedPersons(patient_id=main_patient_id, person_id=patient.id)
        db.session.add(contacted)
        db.session.commit()

        return redirect("/contacted_persons?id={}".format(request.args["id"]))
    else:
        return route_template( 'patients/add_contacted_person', form=patient_form, hospital_types=hospital_types, added=False, error_msg=None)

@blueprint.route('/users', methods=['GET'])
@login_required
def users():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500

    form = TableSearchForm()
    regions = get_regions(current_user)

    if not form.region.choices:
        form.region.choices = [ (-1, c.all_regions) ] + [(r.id, r.name) for r in regions]

    users = []
    filt = dict()

    q = User.query
    # patient = Patient.query.filter_by(id = request.args["id"]).first()

    page = 1
    per_page = 5
    if "page" in request.args:
        page = int(request.args["page"])

    total_len = q.count()

    users = q.offset((page-1)*per_page).limit(per_page).all()

    max_page = math.ceil(total_len/per_page)

    form.process()
    return route_template('users/users', users=users, form=form, page=page, 
                                    max_page=max_page, total = total_len, constants=c)

@blueprint.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500        

    patient_form = CreateUserForm()
    regions = get_regions(current_user)

    if not patient_form.region_id.choices:
        patient_form.region_id.choices = [(r.id, r.name) for r in regions]

    if 'create' in request.form:
        new_dict = request.form.to_dict(flat=False)
        
        user = User.query.filter_by(username=new_dict['username'][0]).first()
        if user:
            return route_template( 'users/add_user', error_msg='Имя пользователя уже зарегистрировано', form=patient_form, change=None)

        user = User(**new_dict)
        
        db.session.add(user)
        db.session.commit()

        return route_template( 'users/add_user', form=patient_form, change="Пользователь был успешно добавлен", error_msg=None)
    else:
        return route_template( 'users/add_user', form=patient_form, change=None, error_msg=None)


@blueprint.route('/user_profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500        

    if "id" in request.args:
        user = User.query.filter_by(id=request.args["id"]).first()
        
        if not user:
            return render_template('errors/error-404.html'), 404
        else:
            form = UpdateUserForm()
            
            change = None
            error_msg = None
            
            if 'update' in request.form:
                if request.form['username']:
                    new_username = request.form['username']
                    
                    if not new_username == user.username:  
                        if not User.query.filter_by(username = new_username).count():
                            user.username = new_username
                        else:
                            error_msg = "Пользователь с таким логином уже существует"

                if not error_msg:
                    if request.form['password']:
                        password = request.form['password']

                        user.password = hash_pass(password)

                    user.telephone = request.form['telephone']
                    user.email = request.form['email']

                    db.session.add(user)
                    db.session.commit()

                    change = "Данные обновлены"

            form.username.default = user.username

            form.email.default = user.email
            form.telephone.default = user.telephone
            
            form.region_id.choices = get_regions_choices(current_user)
            form.region_id.default = user.region_id
  
            form.process()
            return route_template('users/user_profile', form = form, user=user, change=change, error_msg=error_msg)
    else:    
        return render_template('errors/error-500.html'), 500

@blueprint.route('/delete_user', methods=['POST'])
@login_required
def delete_user():
    if not current_user.is_authenticated:
        return redirect(url_for('base_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500        
    
    return_url = url_for('home_blueprint.users')

    if len(request.form):
        if "delete" in request.form:
            user_id = request.form["delete"]
            user = User.query.filter(User.id == user_id)

            if user:
                user.delete()
                db.session.commit()

    return redirect(return_url)