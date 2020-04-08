# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from app.main import blueprint

from flask import render_template, redirect, url_for, request
from flask_login import login_required, current_user
from flask_babelex import _

from app import login_manager, db
from app import constants as c
from jinja2 import TemplateNotFound

from app.main.models import (Region, Country, VisitedCountry, Infected_Country_Category, 
                            TravelType, BorderControl, VariousTravel, Address)
from app.main.patients.models import Patient, PatientStatus, ContactedPersons, State, PatientState
from app.main.hospitals.models import Hospital, Hospital_Type
from app.main.flights_trains.models import FlightCode, FlightTravel, Train, TrainTravel

from app.main.patients.forms import PatientForm, UpdateProfileForm, AddFlightFromExcel
from app.main.forms import TableSearchForm

from app.main.routes import route_template

from datetime import datetime
from flask_uploads import UploadSet
from flask import jsonify

import pandas as pd
import numpy as np
import math, json, re, itertools
import nltk
import dateutil.parser
import requests

from multiprocessing.pool import ThreadPool as threadpool
from app.main.util import get_regions, get_regions_choices, get_flight_code
from app.login.util import hash_pass
from sqlalchemy import func, exc

def prepare_patient_form(patient_form):
    if not patient_form.region_id.choices:
        patient_form.region_id.choices = get_regions_choices(current_user, False)
        patient_form.hospital_region_id.choices = get_regions_choices(current_user, False)

    if not patient_form.travel_type.choices:
        patient_form.travel_type.choices = [ (typ.value, typ.name) for typ in TravelType.query.all() ]

    # Flight Travel
    if not patient_form.flight_arrival_date.choices:
        dates = np.unique([f.date for f in FlightCode.query.all()])
        patient_form.flight_arrival_date.choices = [(date, date) for date in dates]
    
    if not patient_form.flight_code_id.choices:
        if patient_form.flight_arrival_date.choices:
            first_date = patient_form.flight_arrival_date.choices[0][0]
            patient_form.flight_code_id.choices = [(f.id,"{}, {} - {}".format(
                f.code, f.from_city, f.to_city)) for f in FlightCode.query.filter_by(date=first_date).all()]
        else:
            patient_form.flight_code_id.choices = []

    

    t_ids = {}
    for typ in TravelType.query.all():
        t_ids[typ.value] = typ.id

    travel_id_form = [(t_ids[c.by_auto_type[0]], patient_form.auto_border_id),
                      (t_ids[c.by_foot_type[0]], patient_form.foot_border_id),
                      (t_ids[c.by_sea_type[0]], patient_form.sea_border_id)]
    # Various Travel
    for typ_id, typ_select in travel_id_form:
        if not typ_select.choices:
            borders = BorderControl.query.filter_by(travel_type_id = typ_id).all()
            typ_select.choices =[(b.id, b.name) for b in borders]

    # Hospital
    hospital_types = Hospital_Type.query.all()
    hospital_types = [(h.id, h.name) for h in hospital_types]
    patient_form.hospital_type_id.choices = hospital_types

    # Countries
    countries = Country.query.all()
    kz = Country.query.filter_by(code="KZ").first()

    def populate_countries_select(select_input, default, with_unknown = True):
        if not select_input.choices:
            select_input.choices = [(-1, c.unknown[1])] if with_unknown else []
            select_input.choices += [(c.id, c.name) for c in countries]
            select_input.default = default

    populate_countries_select(patient_form.citizenship_id, kz.id, False)
    populate_countries_select(patient_form.country_of_residence_id, kz.id)

    populate_countries_select(patient_form.home_address_country_id, kz.id)
    populate_countries_select(patient_form.job_address_country_id, kz.id)

    populate_countries_select(patient_form.visited_country_id, -1)

    return patient_form

def is_same_address(request_dict, address, form_prefix='home'):
    is_same = True

    if address.country_id != int(request_dict[form_prefix + '_address_country_id']):
        is_same = False
    elif address.state != request_dict.get(form_prefix + '_address_state', None):
        is_same = False
    elif address.city != request_dict[form_prefix + '_address_city']:
        is_same = False
    elif address.street != request_dict[form_prefix + '_address_street']:
        is_same = False
    elif address.house != request_dict[form_prefix + '_address_house']:
        is_same = False
    elif address.flat != request_dict.get(form_prefix + '_address_flat', None):
        is_same = False
    elif address.building != request_dict.get(form_prefix + '_address_building', None):
        is_same = False

    return is_same

def process_address(request_dict, form_prefix='home', lat_lng = True, address = None):
    if address is None:
        address = Address()

    address.country_id = request_dict[form_prefix + '_address_country_id']
    address.state = request_dict.get(form_prefix + '_address_state', None)
    address.city = request_dict[form_prefix + '_address_city']
    address.street = request_dict[form_prefix + '_address_street']
    address.house = request_dict[form_prefix + '_address_house']
    address.flat = request_dict.get(form_prefix + '_address_flat', None)
    address.building = request_dict.get(form_prefix + '_address_building', None)

    db.session.add(address)
    db.session.commit()

    if lat_lng:
        lat_lng = get_lat_lng([address])[0]

        address.lat = lat_lng[0]
        address.lng = lat_lng[1]

        db.session.add(address)

    return address

def handle_add_update_patient(request_dict, final_dict, update_dict = {}):
    form_val_key = ['region_id', 'first_name', 'second_name', 'patronymic_name', 'dob', 'iin', 'citizenship_id', 
                    'pass_num', 'country_of_residence_id', 'telephone', 'email', 'job', 'job_position', 'hospital_id']
    
    # 1
    for key in form_val_key:
        if key in request_dict:
            final_dict[key] = request_dict[key]
    # 2
    final_dict['dob'] = datetime.strptime(request.form['dob'], '%Y-%m-%d')    
    final_dict['gender'] = None if int(request_dict['gender']) == -1 else int(request_dict['gender']) == 1

    status = request_dict.get('patient_status', c.no_status[0])
    final_dict['status_id'] = PatientStatus.query.filter_by(value=status).first().id
    final_dict['is_found'] = int(request_dict['is_found']) == 1
    final_dict['is_infected'] = int(request_dict['is_infected']) == 1    

    # 3
    travel_type = TravelType.query.filter_by(value=request_dict['travel_type']).first()
    
    final_dict['travel_type_id'] = travel_type.id if travel_type else None

    # 5
    # Home Address
    home_address = process_address(request_dict)
    final_dict['home_address_id'] = home_address.id

    job_address = None
    if "job_address_city" in request_dict:
        job_address = process_address(request_dict, "job", False)

    if job_address:
        final_dict['job_address_id'] = job_address.id

def handle_after_patient(request_dict, final_dict, patient, update_dict = {}):
    travel_type = patient.travel_type

    if travel_type:
        if travel_type.value == c.flight_type[0]:
            f_travel = update_dict.get('flight_travel', FlightTravel(patient_id = patient.id))
            
            f_code_id = request_dict['flight_code_id']
            seat = request_dict.get('flight_seat', None)
            
            if f_travel.flight_code_id != f_code_id or f_travel.seat != seat:
                f_travel.flight_code_id = f_code_id
                f_travel.seat = seat

                db.session.add(f_travel)
                db.session.commit()
        elif travel_type.value == c.train_type[0]:
            t_travel = update_dict.get('train_travel', TrainTravel(patient_id = patient.id))
            
            t_id = request_dict['train_id']
            wagon = request_dict.get('train_wagon', None)
            seat = request_dict.get('train_seat', None)
            
            if t_travel.train_id != t_id or t_travel.seat != seat or t_travel.wagon != wagon:
                t_travel.train_id = t_id
                t_travel.seat = seat
                t_travel.wagon = wagon

                db.session.add(t_travel)
                db.session.commit()                
        else:
            border_form_key = None

            if travel_type.value == c.by_auto_type[0]:
                border_form_key = 'auto_border_id'
            elif travel_type.value == c.by_foot_type[0]:
                border_form_key = 'foot_border_id'
            elif travel_type.value == c.by_sea_type[0]:
                border_form_key = 'sea_border_id'
            
            if border_form_key:
                v_travel = update_dict.get('various_travel', VariousTravel(patient_id = patient.id))

                date = request_dict['arrival_date']
                border_control_id = request_dict[border_form_key]

                if v_travel.border_control_id != border_control_id or v_travel.date != date:
                    v_travel.date = date 
                    v_travel.border_control_id = border_control_id

                    db.session.add(v_travel)
                    db.session.commit()

    # 4 Visited Country
    visited_country_id = request_dict.get('visited_country_id', None)

    if visited_country_id !='-1' and visited_country_id:
        visited_country = VisitedCountry(patient_id = patient.id, country_id=visited_country_id)
        
        from_date = request_dict.get('visited_from_date', None)
        visited_country.from_date = from_date if from_date else None

        to_date = request_dict.get('visited_from_date', None)
        visited_country.to_date = to_date if from_date else None            

        db.session.add(visited_country)
        db.session.commit()

@blueprint.route('/add_person', methods=['GET', 'POST'])
def add_patient():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    patient_form = PatientForm()
    patient_form = prepare_patient_form(patient_form)

    patient_statuses = PatientStatus.query.all()
    if not patient_form.patient_status.choices:
        patient_form.patient_status.choices = [(s.value, s.name) for s in patient_statuses]

    patient_form.process()

    if 'create' in request.form:
        request_dict = request.form.to_dict(flat=True)
        final_dict = {'created_by_id': current_user.id}

        handle_add_update_patient(request_dict, final_dict)        

        # else we can create the user
        patient = Patient(**final_dict)
        patient.is_contacted_person = False
        
        db.session.add(patient)
        db.session.commit()

        handle_after_patient(request_dict, final_dict, patient)

        return jsonify({"patient_id": patient.id})
    else:
        return route_template( 'patients/add_person', form=patient_form, added=False, error_msg=None, c=c)

@blueprint.route('/patient_profile', methods=['GET', 'POST'])
@login_required
def patient_profile():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if "id" in request.args:
        patient = Patient.query.filter_by(id=request.args["id"]).first()
      
        if not patient:
            return render_template('errors/error-404.html'), 404
        else:
            # patient.visited_country = []
            # db.session.delete(patient.visited_country[0])
            # db.session.commit()

            form = UpdateProfileForm(request.form)
            change = None

            regions = Region.query.all()

            form = prepare_patient_form(form)
            form.travel_type.default = patient.travel_type.value
            
            # States
            states = State.query.all()
            states = [(st.id, st.name) for st in states]
            form.state.choices = states

            if len(request.form):
                request_dict = request.form.to_dict(flat = True)
                
                final_dict = {}
                update_dict = {}
                
                request_dict['is_found'] = "is_found" in request.form
                request_dict['is_infected'] = "is_infected" in request.form

                status = c.no_status[0]
                for s in c.patient_statuses:
                    if s[0] in request.form:
                        status = s[0]

                request_dict['patient_status'] = status
                request_dict['travel_type'] = patient.travel_type.value
                
                if request_dict['travel_type'] == c.flight_type[0]:
                    update_dict['flight_travel'] = FlightTravel.query.filter_by(id=patient.id).first()
                elif request_dict['travel_type'] in dict(c.various_travel_types).keys():
                    update_dict['various_travel'] = VariousTravel.query.filter_by(id=patient.id).first()

                handle_add_update_patient(request_dict, final_dict, update_dict)
                
                if "travel_type_id" in request.form:
                    travel_type_id = request.form['travel_type_id']
                    if travel_type_id == "None":
                        travel_type_id = None                    

                    patient.travel_type_id = travel_type_id

                if not is_same_address(request_dict, patient.home_address):
                    process_address(request_dict, address=patient.home_address)

                if patient.job_address:
                    if not is_same_address(request_dict, patient.job_address, form_prefix="job"):
                        process_address(request_dict, lat_lng = False, form_prefix="job", address=patient.job_address)

                for k, v in final_dict.items():
                    setattr(patient, k, v)

                db.session.add(patient)
                db.session.commit()
                change = _("Профиль успешно обновлен")

            # Populate the form

            form.hospital_region_id.default = patient.region_id if not patient.hospital else patient.hospital.region_id

            travel = None
            travel_type = TravelType.query.filter_by(id=patient.travel_type_id).first()
            
            if travel_type.value == c.flight_type[0]:
                travel = FlightTravel.query.filter_by(patient_id=patient.id).first()
            if travel_type.value == c.train_type[0]:
                travel = TrainTravel.query.filter_by(patient_id=patient.id).first()
            elif travel_type.value != c.local_type[0]:
                travel = VariousTravel.query.filter_by(patient_id=patient.id).first()

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

            hospital_name = None
            if patient.hospital:
                form.hospital_id.default = patient.hospital.id
                hospital_name = Hospital.query.filter_by(id=patient.hospital.id).first().name

            today = datetime.today()
            age =  today.year - patient.dob.year - ((today.month, today.day) < (patient.dob.month, patient.dob.day))

            def populate_form(form, attrs, prefix = ''):
                for k in attrs:
                    param = getattr(form, prefix + k, None)
                    if param:
                        if attrs[k] is not None:
                            setattr(param, 'default', attrs[k])

            populate_form(form, patient.__dict__)

            form.travel_type.default = travel_type.value

            if patient.visited_country:
                populate_form(form, patient.visited_country[0].__dict__, prefix='visited_')

            form.gender.default = -1 if patient.gender is None else int(patient.gender)

            if patient.home_address:
                populate_form(form, patient.home_address.__dict__, prefix='home_address_')
            
            if patient.job_address:
                populate_form(form, patient.job_address.__dict__, prefix='job_address_')

            if "success" in request.args:
                change = _("Пользователь %(full_name)s успешно добавлен", full_name=patient.full_name)

            form.process()

            states = PatientState.query.filter_by(patient_id=patient.id).join(State).all()

            return route_template('patients/profile', states=states, patient=patient, age=age, hospital_name=hospital_name, form = form, change = change, c=c, travel=travel)
    else:    
        return render_template('errors/error-500.html'), 500

def get_lat_lng(patients):
    lat_lng = []
    for home_address in patients:
        lat = None
        lng = None

        params = dict(
            apiKey='S25QEDJvW3PCpRvVMoFmIJBHL01xokVyinW8F5Fj0pw',
        )

        # home_address = re.sub(r"([0-9]+(\.[0-9]+)?)",r" \1 ", home_address).strip()
        parsed_address = {}
        parsed_address["country"] = home_address.country.name
        parsed_address["state"] = home_address.state
        parsed_address["city"] = home_address.city
        parsed_address["street"] = home_address.street
        parsed_address["houseNumber"] = home_address.house
        parsed_address = {k: v for k, v in parsed_address.items() if v}

        params['qq'] = ';'.join(['%s=%s' % (key, value) for (key, value) in parsed_address.items()])

        url = "https://geocode.search.hereapi.com/v1/geocode"

        resp = requests.get(url=url, params=params)
        data = resp.json()
                   
        if len(data["items"]):
            item = data["items"][0]

            item = item["position"]

            lat = item["lat"]
            lng = item["lng"]

            print(lat, lng)
            
        lat_lng.append((lat, lng))

    return lat_lng

@blueprint.route('/add_data', methods=['GET', 'POST'])
def add_data():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    data_form = AddFlightFromExcel()
    docs = UploadSet('documents', ['xls', 'xlsx', 'csv'])

    if not data_form.flights_id.choices:
        data_form.flights_id.choices = []
        for flight in FlightCode.query.all():
            flight_name = "{}, {}, {}-{}".format(flight.date, flight.code, flight.from_city, flight.to_city)
            data_form.flights_id.choices.append((str(flight.id), flight_name))

        form_dict = request.form.to_dict()
        if "flights_id" in form_dict:
            data_form.flights_id.default = form_dict["flights_id"]

    found_hospitals = dict()

    if data_form.validate_on_submit():
        filename = docs.save(data_form.file.data)
        file_url = docs.url(filename)

        patients = pd.read_excel(docs.path(filename))
        added = 0
        regions = get_regions(current_user)

        created_patients = []

        def create_patient(row, flight_code_id):

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

            patient.citizenship = row.get("Гражданство", None)
            patient.pass_num = row["Номер паспорта"]
            patient.telephone = row["Номер мобильного телефона"]

            # try:
            #     patient.arrival_date = dateutil.parser.parse(row["Дата въезда"])
            # except TypeError:
            #     patient.arrival_date = datetime(1000, 1, 1)           

            patient.travel_type_id = TravelType.query.filter_by(value = c.flight_type[0]).first().id

            # Create travel for this user
            flight_travel = FlightTravel(flight_code_id=flight_code_id, seat=None)
            flight_travel.seat = row.get("Место пассажира на борту воздушного судна", None)

            db.session.add(flight_travel)
            db.session.commit()
            patient.travel_id = flight_travel.id

            patient.visited_country = row.get("Место и сроки пребывания в последние 14 дней до прибытия в Казахстан (укажите страну, область, штат и т.д.)", None)
            
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
            patient.job = row.get("Место работы", None)
            
            if "Найден (да/нет)" in row.keys():
                patient.is_found = True if row["Найден (да/нет)"].lower() == "да" else False
            else:
                if "Госпитализирован (да/нет)" in row.keys():
                    patient.is_found = True if row["Госпитализирован (да/нет)"].lower() == "да" else False    
    
            hospitals = Hospital.query.filter_by(region_id=patient.region_id).all()

            if not pd.isnull(row.get("Место госпитализации", None)):
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

        patients.apply(lambda row: create_patient(row, request.form['flights_id'][0]), axis=1)
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

        return route_template( 'patients/add_data', form=data_form, added=added)
    else:
        return route_template( 'patients/add_data', form=data_form, added=-1)

@blueprint.route('/patients')
@login_required
def patients():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    form = TableSearchForm()

    if not form.region.choices:
        form.region.choices = get_regions_choices(current_user)
    
    if not form.travel_type.choices:
        form.travel_type.choices = [(-1, c.all_types)] + [(t.id, t.name) for t in TravelType.query.all()]

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

    if "travel_type" in request.args:
        travel_type_id = request.args["travel_type"]
        if travel_type_id != '-1':
            filt["travel_type_id"] = travel_type_id
            form.travel_type.default = travel_type_id

    if "not_found" in request.args:
        filt["is_found"] = False
        form.not_found.default='checked'

    if "is_infected" in request.args:
        filt["is_infected"] = True
        form.is_infected.default='checked'

    q = db.session.query(Patient).filter_by(**filt)
    # q = q.filter(Patient.travel_id == FlightTravel.id)

    if "flight_code" in request.args:
        flight_code = request.args["flight_code"]
        if flight_code != '' and flight_code != c.all_flight_codes:
            fc = FlightCode.query.filter_by(code=flight_code).first()
            if fc:
                flight_type_id = TravelType.query.filter_by(value=c.flight_type[0]).first().id

                q = q.filter(Patient.travel_type_id == flight_type_id)
                q = q.filter(FlightTravel.flight_code_id == fc.id)
                form.flight_code.default = fc.code
        else:
            form.flight_code.default = c.all_flight_codes    

    if "not_in_hospital" in request.args:
        in_hospital_id = PatientStatus.query.filter_by(value=c.in_hospital[0]).first().id
        q = q.filter(Patient.status_id != in_hospital_id)

        form.not_in_hospital.default='checked'

    def name_search(param, param_str, q):
        if param_str in request.args:
            req_str = request.args[param_str]
            q = q.filter(func.lower(param).contains(req_str.lower()))
            param = getattr(form, param_str, None)
            if param:
                setattr(param, 'default', req_str)
        
        return q

    q = name_search(Patient.first_name, "first_name", q)
    q = name_search(Patient.second_name, "second_name", q)
    q = name_search(Patient.patronymic_name, "patronymic_name", q)

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

    for result in q.offset((page-1)*per_page).limit(per_page).all():
        p = result
        contacted = ContactedPersons.query.filter_by(patient_id=p.id).all()

        p.contacted_count = len(contacted)
        p.contacted_found_count = 0

        for contact in contacted:
            contacted_person = Patient.query.filter_by(id=contact.person_id).first()
            if contacted_person and contacted_person.is_found:
                p.contacted_found_count += 1

        patients.append(p)

    max_page = math.ceil(total_len/per_page)

    flight_codes_list = [c.all_flight_codes] + [ code.code for code in FlightCode.query.all() ]

    change = None
    error_msg = None

    if "delete" in request.args:
        change = _("Пользователь успешно удален")

    form.process()
    return route_template('patients/patients', patients=patients, form=form, page=page, max_page=max_page, total = total_len, 
                            constants=c, flight_codes_list=flight_codes_list, change=change, error_msg=error_msg)

@blueprint.route('/delete_patient', methods=['POST'])
@login_required
def delete_patient():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))
    
    return_url = "{}?delete".format(url_for('main_blueprint.patients'))

    if len(request.form):
        if "delete" in request.form:
            patient_id = request.form["delete"]
            patient = None
            try:
                patient_query = Patient.query.filter(Patient.id == patient_id)
                patient = patient_query.first()
            except exc.SQLAlchemyError:
                return render_template('errors/error-400.html'), 400

            if patient:
                if patient.is_contacted_person:
                    q = ContactedPersons.query.filter_by(person_id=patient_id)
                    return_url = "{}?id={}".format(url_for('main_blueprint.contacted_persons'), q.first().patient_id)
                    q.delete()

                    q.delete()               


                patient_query.delete()
                db.session.commit()
            
            # user does not exist

    return redirect(return_url)

@blueprint.route('/contacted_persons', methods=['GET', 'POST'])
@login_required
def contacted_persons():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    form = TableSearchForm()
    regions = get_regions(current_user)

    if not form.region.choices:
        form.region.choices = [ (-1, c.all_regions) ] + [(r.id, r.name) for r in regions]

    patients = []
    filt = dict()

    if "id" in request.args:
        patient = None
        try:
            patient = Patient.query.filter_by(id=request.args["id"]).first()
        except exc.SQLAlchemyError:
            return render_template('errors/error-400.html'), 400

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
        return redirect(url_for('login_blueprint.login'))

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
        final_dict = request.form.to_dict(flat=False)

        final_dict['dob'] = datetime.strptime(request.form['dob'], '%Y-%m-%d')

        status = request.form.get("patient_status", c.no_status[0])
        final_dict['status_id'] = PatientStatus.query.filter_by(value=status).first().id
        final_dict['is_found'] = int(final_dict['is_found'][0]) == 1

        # else we can create the user
        patient = Patient(**final_dict)
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


@blueprint.route('/add_state', methods=['POST'])
@login_required
def add_state():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if len(request.form):
        patient_id = request.form["id"]
        patient = None
        try:
            patient_query = Patient.query.filter(Patient.id == patient_id)
            patient = patient_query.first()
        except exc.SQLAlchemyError:
            return render_template('errors/error-400.html'), 400

        if patient:
            state = {
                "id": request.form["state"],
                "comment": request.form["stateComment"],
                "detection_date":request.form["stateDetectionDate"]
            }
            patientState = PatientState(
                patient_id=patient_id, 
                state_id=state["id"],
                detection_date=state["detection_date"],
                comment=state["comment"])
            db.session.add(patientState)
            db.session.commit()
    
    url = f"/patient_profile?id={request.form['id']}"
    return redirect(url)