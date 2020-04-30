# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""
import os
import dateutil.parser
import math, json, re, itertools
from datetime import datetime
from multiprocessing.pool import ThreadPool as threadpool

import numpy as np
import nltk
import requests
import pandas as pd
from flask import jsonify
from flask import render_template, redirect, url_for, request
from flask_babelex import _
from flask_login import login_required, current_user
from flask_uploads import UploadSet
from jinja2 import TemplateNotFound
from sqlalchemy import func, exc

from app import login_manager, db
from app import constants as c
from app.main import blueprint
from app.main.models import Region, Country, VisitedCountry, Infected_Country_Category
from app.main.models import TravelType, BorderControl, VariousTravel, BlockpostTravel, Address, HGBDToken
from app.main.patients.forms import PatientForm, UpdateProfileForm, AddFlightFromExcel, ContactedPatientsSearchForm
from app.main.patients.models import Patient, PatientStatus, ContactedPersons, State, PatientState
from app.main.patients.modules import ContactedPatientsTableModule
from app.main.hospitals.models import Hospital, Hospital_Type
from app.main.flights_trains.models import FlightCode, FlightTravel, Train, TrainTravel
from app.main.forms import TableSearchForm
from app.main.routes import route_template
from app.main.util import get_regions, get_regions_choices, get_flight_code, populate_form, parse_date
from app.login.util import hash_pass

def prepare_patient_form(patient_form, with_old_data = False):
    """
    Function adds values for input fields of PatientForm
    """
    # return all regions
    regions_choices = get_regions_choices(current_user, False)

    # Regions for select field
    if not patient_form.region_id.choices:
        patient_form.region_id.choices = regions_choices
        patient_form.hospital_region_id.choices = regions_choices

    # TravelTypes for select fiels: Местный, Самолет итд
    if not patient_form.travel_type.choices:
        patient_form.travel_type.choices = []
        for typ in TravelType.query.all():
            if typ.value == c.old_data_type[0]:
                if with_old_data:
                    patient_form.travel_type.choices.append((typ.value, typ.name))
            else:
                patient_form.travel_type.choices.append((typ.value, typ.name))

    # Flight Travel
    if not patient_form.flight_arrival_date.choices:
        dates = np.unique([f.date for f in FlightCode.query.all()])
        patient_form.flight_arrival_date.choices = [(date, date) for date in dates]
    
    # Flight Code id if exists
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

    # Blockpost Travel
    if not patient_form.blockpost_region_id.choices:
        patient_form.blockpost_region_id.choices = regions_choices

    # Hospital
    hospital_types = Hospital_Type.query.all()
    hospital_types = [(h.id, h.name) for h in hospital_types]
    patient_form.hospital_type_id.choices = hospital_types

    # States
    patient_form.patient_status.choices = [(s[0], s[1]) for s in c.form_states]

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

    country_id = request_dict[form_prefix + '_address_country_id']

    if address.country_id != (int(country_id) if country_id != None else country_id):
        is_same = False
    elif address.state != request_dict.get(form_prefix + '_address_state', None):
        is_same = False
    elif address.county != request_dict.get(form_prefix + '_address_county', None):
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
    if request_dict[form_prefix + '_address_country_id'] == '-1':
        request_dict[form_prefix + '_address_country_id'] = None

    if address is None:
        address = Address()
    else:
        if is_same_address(request_dict, address):
            return address

    address.country_id = request_dict[form_prefix + '_address_country_id']
    address.state = request_dict.get(form_prefix + '_address_state', None)
    address.county = request_dict.get(form_prefix + '_address_county', None)
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
    
    # 1 Set values from request_dict
    for key in form_val_key:
        if key in request_dict:
            if key == "country_of_residence_id" and request_dict[key] == '-1':
                request_dict[key] = None
            final_dict[key] = request_dict[key]
    # 2
    final_dict['dob'] = parse_date(request.form['dob'])    
    final_dict['gender'] = None if int(request_dict['gender']) == -1 else int(request_dict['gender']) == 1

    state_value = request_dict.get('patient_status')
    if state_value is not None and state_value != "":
        state = State.query.filter_by(value=state_value).first()
        if state is not None:
            final_dict['state_id'] = state.id
    final_dict['is_found'] = int(request_dict['is_found']) == 1
    final_dict['is_infected'] = int(request_dict['is_infected']) == 1

    # 3
    travel_type = TravelType.query.filter_by(value=request_dict['travel_type']).first()
    final_dict['travel_type_id'] = travel_type.id if travel_type else None

    # 5
    # Home Address
    home_address = process_address(request_dict, address=update_dict.get("home_address", None))
    final_dict['home_address_id'] = home_address.id

    # Job Address
    job_address = process_address(request_dict, "job", False, address=update_dict.get("job_address", None))
    final_dict['job_address_id'] = job_address.id

def handle_after_patient(request_dict, final_dict, patient, update_dict = {}):
    # print(patient)
    patient.is_found = final_dict['is_found']
    patient.is_infected = final_dict['is_infected']
    if 'state_id' in final_dict:
        patientState = PatientState(state_id=final_dict['state_id'])
        patient.addState(patientState)

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
        elif travel_type.value == c.blockpost_type[0]:
            blockpost_t = update_dict.get('blockpost_travel', BlockpostTravel(patient_id = patient.id))
            
            date = request_dict['arrival_date']
            blockpost_r_id = request_dict['blockpost_region_id']
            
            if blockpost_t.region_id != blockpost_r_id or blockpost_t.date != date:
                blockpost_t.date = date
                blockpost_t.region_id = blockpost_r_id

                db.session.add(blockpost_t)
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
    v_country_id = request_dict.get('visited_country_id', None)
    v_country_id = None if v_country_id == '-1' else v_country_id
    v_country = update_dict.get('visited_country', VisitedCountry(patient_id = patient.id))
    
    from_date = request_dict.get('visited_from_date', None)
    from_date = None if not from_date else from_date
    
    to_date = request_dict.get('visited_from_date', None)
    to_date = None if not to_date else to_date

    if v_country.to_date != to_date or v_country.from_date != from_date or v_country.country_id != v_country_id:
        v_country.from_date = from_date
        v_country.to_date = to_date
        v_country.country_id = v_country_id

        db.session.add(v_country)
        db.session.commit()

@blueprint.route('/add_person', methods=['GET', 'POST'])
@login_required
def add_patient():
    patient_form = PatientForm()
    patient_form = prepare_patient_form(patient_form)
    patient_form.process()

    if 'create' in request.form:
        request_dict = request.form.to_dict(flat=True)
        final_dict = {'created_by_id': current_user.id}
        
        # create Patient
        handle_add_update_patient(request_dict, final_dict)        
        patient = Patient(**final_dict)
        db.session.add(patient)
        db.session.commit()

        # Create Travels and VisitedCountries to created Patient
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
            form = UpdateProfileForm(request.form)
            change = None

            regions = Region.query.all()

            form = prepare_patient_form(form, True)
            form.travel_type.default = patient.travel_type.value
            
            # States
            states = State.query.all()
            states = [(st.value, st.name) for st in states]
            form.state.choices = states

            if len(request.form):
                request_dict = request.form.to_dict(flat = True)
                
                final_dict = {}
                update_dict = {}
                
                request_dict['is_found'] = "is_found" in request.form
                request_dict['is_infected'] = "is_infected" in request.form
                # request_dict['is_contacted'] = "is_contacted" in request.form

                # status = c.no_status[0]
                # for s in c.patient_statuses:
                    # if s[0] in request.form:
                        # status = s[0]

                # request_dict['patient_status'] = status
                request_dict['travel_type'] = patient.travel_type.value

                update_dict["home_address"] = patient.home_address
                update_dict["job_address"] = patient.job_address
                
                if request_dict['travel_type'] == c.flight_type[0]:
                    update_dict['flight_travel'] = FlightTravel.query.filter_by(patient_id=patient.id).first()
                elif request_dict['travel_type'] == c.train_type[0]:
                    update_dict['train_travel'] = TrainTravel.query.filter_by(patient_id=patient.id).first()
                elif request_dict['travel_type'] == c.blockpost_type[0]:
                    update_dict['blockpost_travel'] = BlockpostTravel.query.filter_by(patient_id=patient.id).first()
                elif request_dict['travel_type'] in dict(c.various_travel_types).keys():
                    update_dict['various_travel'] = VariousTravel.query.filter_by(patient_id=patient.id).first()

                if patient.visited_country and len(patient.visited_country):
                    update_dict["visited_country"] = patient.visited_country[0]

                handle_add_update_patient(request_dict, final_dict, update_dict)
                handle_after_patient(request_dict, final_dict, patient, update_dict)

                if "travel_type_id" in request.form:
                    travel_type_id = request.form['travel_type_id']
                    if travel_type_id == "None":
                        travel_type_id = None                    

                    patient.travel_type_id = travel_type_id

                for k, v in final_dict.items():
                    setattr(patient, k, v)

                # TODO
                # if patient.status.value != c.in_hospital[0]:
                if patient.in_hospital == False:
                    patient.hospital_id = None

                db.session.add(patient)
                db.session.commit()
                change = _("Профиль успешно обновлен")

            # Populate the form

            form.hospital_region_id.default = patient.region_id if not patient.hospital else patient.hospital.region_id
            travel = None
            travel_type = TravelType.query.filter_by(id=patient.travel_type_id).first()
            
            if travel_type.value == c.flight_type[0]:
                travel = FlightTravel.query.filter_by(patient_id=patient.id).first()
            elif travel_type.value == c.train_type[0]:
                travel = TrainTravel.query.filter_by(patient_id=patient.id).first()
            elif travel_type.value == c.blockpost_type[0]:
                travel = BlockpostTravel.query.filter_by(patient_id=patient.id).first()
            elif travel_type.value != c.local_type[0]:
                travel = VariousTravel.query.filter_by(patient_id=patient.id).first()

            if patient.is_found:
                form.is_found.default = 'checked'

            if patient.is_infected:
                form.is_infected.default = 'checked'
            

            hospital_name = None
            if patient.hospital:
                form.hospital_id.default = patient.hospital.id
                hospital_name = Hospital.query.filter_by(id=patient.hospital.id).first().name

            today = datetime.today()
            age =  today.year - patient.dob.year - ((today.month, today.day) < (patient.dob.month, patient.dob.day))

            def preprocess_params(params_dict, param_to_check):
                params_dict = params_dict.copy()

                if params_dict[param_to_check] == None:
                    params_dict[param_to_check] = -1

                return params_dict

            populate_form(form, preprocess_params(patient.__dict__, 'country_of_residence_id'))

            form.travel_type.default = travel_type.value

            if patient.visited_country:
                populate_form(form, patient.visited_country[0].__dict__, prefix='visited_')

            form.gender.default = -1 if patient.gender is None else int(patient.gender)

            if patient.home_address:
                populate_form(form, preprocess_params(patient.home_address.__dict__, 'country_id')
                    , prefix='home_address_')
            
            if patient.job_address:
                populate_form(form, preprocess_params(patient.job_address.__dict__, 'country_id'),
                 prefix='job_address_')

            if "success" in request.args:
                change = _("Пользователь %(full_name)s успешно добавлен", full_name=patient.full_name)

            form.process()

            # states = PatientState.query.filter_by(patient_id=patient.id).all()
            states = patient.states

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
        parsed_address["country"] = home_address.country.name if home_address.country else ""
        parsed_address["state"] = home_address.state
        parsed_address["county"] = home_address.county
        parsed_address["city"] = home_address.city
        parsed_address["street"] = home_address.street
        parsed_address["houseNumber"] = home_address.house
        parsed_address = {k: v for k, v in parsed_address.items() if v}

        params['qq'] = ';'.join(['%s=%s' % (key, value) for (key, value) in parsed_address.items()])

        url = "https://geocode.search.hereapi.com/v1/geocode"

        resp = requests.get(url=url, params=params, verify=False)
        data = resp.json()
                   
        if data and "items" in data and len(data["items"]):
            item = data["items"][0]

            item = item["position"]

            lat = item["lat"]
            lng = item["lng"]

            
        lat_lng.append((lat, lng))

    return lat_lng

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

    # if not current_user.is_admin:
        # filt["region_id"] = current_user.region_id
    # else:
    if "region" in request.args:
        region = request.args["region"]
        if region != '-1':
            filt["region_id"] = region
            form.region.default = region
    elif current_user.region_id != None:
        region = current_user.region_id
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
    
    # if "is_contacted" in request.args:
    #     filt["is_contacted"] = True
    #     form.is_contacted.default='checked'

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

    # TODO
    if "not_in_hospital" in request.args:
        # in_hospital_id = PatientStatus.query.filter_by(value=c.in_hospital[0]).first().id
        q = q.filter(Patient.in_hospital == False)

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

    select_contacted = None

    if "select_contacted_id" in request.args:
        try:
            patient_query = Patient.query.filter_by(id = request.args["select_contacted_id"])
            patient = patient_query.first()
        except exc.SQLAlchemyError:
            return render_template('errors/error-400.html'), 400        
        
        select_contacted = patient.id

    q = q.order_by(Patient.created_date.desc())

    page = 1
    per_page = 10
    if "page" in request.args:
        page = int(request.args["page"])

    total_len = q.count()
    
    if select_contacted:
        infected_contacted = ContactedPersons.query.filter_by(infected_patient_id=select_contacted)
        infected_contacted_ids = [c.contacted_patient_id for c in infected_contacted]

        contacted_infected = ContactedPersons.query.filter_by(contacted_patient_id=select_contacted)
        contacted_infected_ids = [c.infected_patient_id for c in contacted_infected]

    for result in q.offset((page-1)*per_page).limit(per_page).all():
        p = result
        contacted = ContactedPersons.query.filter_by(infected_patient_id=p.id).all()

        p.contacted_count = len(contacted)
        p.contacted_found_count = 0

        for contact in contacted:
            contacted_person = Patient.query.filter_by(id=contact.contacted_patient_id).first()
            if contacted_person and contacted_person.is_found:
                p.contacted_found_count += 1

        if select_contacted:
            if p.id in infected_contacted_ids:
                p.already_contacted = True
            elif p.id in contacted_infected_ids:
                p.already_infected = True

        patients.append(p)

    max_page = math.ceil(total_len/per_page)

    flight_codes_list = [c.all_flight_codes] + [ code.code for code in FlightCode.query.all() ]

    change = None
    error_msg = None

    if "delete" in request.args:
        change = _("Пользователь успешно удален")

    if "success" in request.args:
        change = request.args['success']
    elif "error" in request.args:
        error_msg = request.args['error']

    form.process()
    return route_template('patients/patients', patients=patients, form=form, page=page, max_page=max_page, total = total_len, 
                            constants=c, flight_codes_list=flight_codes_list, change=change, error_msg=error_msg, select_contacted = select_contacted)

@blueprint.route('/delete_patient', methods=['POST'])
@login_required
def delete_patient():
    # if not current_user.is_authenticated:
    #     return redirect(url_for('login_blueprint.login'))
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
                # if patient.is_contacted_person:
                q = ContactedPersons.query.filter_by(contacted_patient_id=patient_id)
                if q.first() is not None:
                    return_url = "{}?id={}".format(url_for('main_blueprint.contacted_persons'), q.first().patient_id)
                    q.delete()
                
                patient_query.delete()
                if patient.home_address:
                    db.session.delete(patient.home_address)
                if patient.job_address:
                    db.session.delete(patient.job_address)
                db.session.commit()

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
            q = ContactedPersons.query.filter_by(infected_patient_id=patient.id)
            all_patients = [p.contacted_patient for p in q.all()]

            infected_contact = ContactedPersons.query.filter_by(contacted_patient_id = patient.id).all()

            change = None
            error_msg = None

            if "success" in request.args:
                change = request.args['success']
            elif "error" in request.args:
                error_msg = request.args['error']
            
            contacted_search_form = ContactedPatientsSearchForm()
            if not contacted_search_form.region_id.choices:
                contacted_search_form.region_id.choices = get_regions_choices(current_user)

            q = q.join(ContactedPersons.contacted_patient)

            try:
                contacted_patients_table = ContactedPatientsTableModule(request, q, contacted_search_form,
                                        (_("Выбрать Контактное Лицо"), "patients?select_contacted_id={}".format(patient.id)))
            except ValueError:
                return render_template('errors/error-500.html'), 500

            form.process()
            return route_template('patients/contacted_persons', patients=patients,
                                contacted_patients_table=contacted_patients_table, contacted_search_form=contacted_search_form,
                                all_patients=all_patients, form=form, constants=c, main_patient=patient,
                                infected_contact=infected_contact, change=change, error_msg=error_msg)
        else:
            return render_template('errors/error-404.html'), 404

    return render_template('errors/error-500.html'), 500

@blueprint.route('/select_contacted', methods=['GET'])
def select_contacted():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if "infected_patient_id" and "contacted_patient_id" in request.args:
        try:
            infected_patient = Patient.query.filter_by(id = request.args["infected_patient_id"]).first()
            contacted_patient = Patient.query.filter_by(id = request.args["contacted_patient_id"]).first()
        except exc.SQLAlchemyError:
            return render_template('errors/error-400.html'), 400

    if not ContactedPersons.query.filter_by(infected_patient_id=infected_patient.id).filter_by(contacted_patient_id=contacted_patient.id).count():
        contacted = ContactedPersons(infected_patient_id=infected_patient.id, contacted_patient_id=contacted_patient.id)
    
        db.session.add(contacted)
        db.session.commit()

        return redirect("/contacted_persons?id={}&success={}".format(infected_patient.id, _("Контактный успешно добавлен")))
    else:
        return render_template('errors/error-400.html'), 400

@blueprint.route('/delete_contacted', methods=['GET'])
def delete_contacted():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))    

    if "contact_id" in request.args:
        try:
            contact = ContactedPersons.query.filter_by(id = request.args["contact_id"]).first()
        except exc.SQLAlchemyError:
            return render_template('errors/error-400.html'), 400        

        if contact:
            infected_patient_id = contact.infected_patient_id
            db.session.delete(contact)
            db.session.commit()
            message = _("Контактная связь успешно удалена")

            return redirect("/contacted_persons?id={}&success={}".format(infected_patient_id, message))

    message = _("Не удалось удалить контактную связь")
    return redirect("/patients?error={}".format(message))

@blueprint.route('/add_state', methods=['POST'])
@login_required
def add_state():
    if len(request.form):
        patient_id = request.form["id"]
        patient = None
        try:
            patient_query = Patient.query.filter(Patient.id == patient_id)
            patient = patient_query.first()
        except exc.SQLAlchemyError:
            return render_template('errors/error-400.html'), 400

        if patient:
            state = State.query.filter_by(value=request.form["state"]).first()
            result = patient.addState(state,
                    detection_date=request.form["stateDetectionDate"],
                    comment=request.form["stateComment"]
                )
            print(result)
    
    url = f"/patient_profile?id={request.form['id']}"
    return redirect(url)


@blueprint.route('/delete_state', methods=['POST'])
@login_required
def delete_state():
    if len(request.form):
        patient_state_id = request.form["id"]
        patient_state = PatientState.query.filter_by(id=patient_state_id).first()
        if patient_state:
            db.session.delete(patient_state)
            db.session.commit()
    url = f"/patient_profile?id={request.form['patientID']}"
    return redirect(url)

@blueprint.route('/update_state', methods=['POST'])
@login_required
def update_state():
    if len(request.form):
        patient_state_id = request.form["id"]
        patient_state = PatientState.query.filter_by(id=patient_state_id).first()
        if patient_state:
            state = State.query.filter_by(id=request.form["state"]).first()
            if state:
                patient_state.state_id = state.id
            patient_state.detection_date = request.form["detection_date"]
            patient_state.comment = request.form["comment"]
            db.session.add(patient_state)
            db.session.commit()
    url = f"/patient_profile?id={request.form['patientID']}"
    return redirect(url)


class RPNService:
    def __init__(self):
        self.hgdb = self.getHGBDToken()

    def incrementCount(self):
        self.hgdb.count += 1
        db.session.add(self.hgdb)
        db.session.commit()

    def checkToken(self, token):
        """Function check if API returns valid response with given token
        
        Return:
            (bool)
        """
        hGBDpath = "http://5.104.236.197:22999/services/api/person"
        address = f"{hGBDpath}?fioiin=иванов&page=1&pagesize=1"
        headers = {'Authorization': f"Bearer {token}"}
        response = requests.request("GET", address, headers=headers, verify=False)
        if not response.ok:
            return False
        data = response.json()
        if type(data) != list or len(data) == 0:
            return False
        return True

    def getHGBDToken(self):
        """Function to retrieve token from HGBD

        If there is no token, then new one is retrieved.
        Token is checked for validity by self.checkToken

        Return:
            (HGBDToken|None)
        """
        tokenRecord = None
        tokenFuncs = [HGBDToken.query.order_by(-HGBDToken.id).first, self.newHGBDToken]
        for tokenFunc in tokenFuncs:
            tokenRecord = tokenFunc()
            if tokenRecord is None:
                continue
            healthy = self.checkToken(tokenRecord.token)
            if healthy:
                return tokenRecord
        return None

    def newHGBDToken(self):
        """Function sends request to eta777 to fetch access_token for HGBD database.
        If server returns valid response, then the new token is saved to database.

        Return:
            token: (str|None) None if couldnt retrieve token
        """

        url = f"{os.getenv('RPN_URL')}/oauth/token"
        payload = f"grant_type=password&username={os.getenv('RPN_USERNAME')}&password={os.getenv('RPN_PASSWORD')}&scope=profile"
        headers = {
            'Authorization': f"Basic {os.getenv('RPN_CLIENT')}",
            'Content-Type': 'text/plain'
        }
        response = requests.request("POST", url, headers=headers, data = payload, verify=False)
        data = response.json()
        if "access_token" not in data:
            return None
        hgbd = HGBDToken(token=data["access_token"])
        db.session.add(hgbd)
        db.session.commit()
        return hgbd
    
    def getPerson(self, iin):
        """Function fetches user data by iin

        Args:
            iin: (str)    
        Return:
            response: (Requests)
        """
        if self.hgdb is None:
            return None
        token = self.hgdb.token
        hGBDpath = f"{os.getenv('RPN_API_URL')}/services/api/person"
        address = f"{hGBDpath}?fioiin={iin}&page=1&pagesize=1"
        headers = {'Authorization': f"Bearer {token}"}
        response = requests.request("GET", address, headers=headers, verify=False)
        data = response.json()
        if len(data) == 0 or type(data) != list:
            return None
        self.incrementCount()
        data[0]["citizen"] = c.HGDBCountry[data[0]["citizen"]]
        return data[0]
    
    def getPhones(self, personID):
        if self.hgdb is None:
            return None
        token = self.hgdb.token
        address = f"{os.getenv('RPN_API_URL')}/services/api/person/{personID}/getPhones"
        headers = {'Authorization': f"Bearer {token}"}
        response = requests.request("GET", address, headers=headers, verify=False)
        data = response.json()
        if len(data) == 0 or type(data) != list:
            return None
        self.incrementCount()
        return data[0]

    def getAddresses(self, personID):
        if self.hgdb is None:
            return None
        token = self.hgdb.token
        address = f"{os.getenv('RPN_API_URL')}/services/api/person/{personID}/addresses"
        headers = {'Authorization': f"Bearer {token}"}
        response = requests.request("GET", address, headers=headers, verify=False)
        data = response.json()
        if len(data) == 0 or type(data) != list:
            return None
        self.incrementCount()
        return data[0]
    

@blueprint.route('/iin/data', methods=['POST'])
@login_required
def iin_data():
    """Endpoint for retrieving user data by iin.

    1) Validate "iin" key and its value.
    2) Check if there is already a Patient with the same iin
    3) Get data from HGBD

    If one of this steps fails, returns error with description.
    """
    data = json.loads(request.data)
    if data == None or 'iin' not in data or type(data['iin']) != str or len(data['iin']) != 12:
        return jsonify({'description': 'No valid iin'}), 403
    patient = Patient.query.filter_by(iin=data['iin']).first()
    if patient:
        return jsonify({'description': 'Patient exists', 'id': patient.id}), 203
    rpn = RPNService()
    if rpn.hgdb is None:
        return jsonify({'description': 'Service unreachable'}), 406
    personData = rpn.getPerson(data['iin'])
    if personData is None:
        return jsonify({'description': 'Person not found'}), 405
    personData["address"] = rpn.getAddresses(personData["PersonID"])
    personData["phone"] = rpn.getPhones(personData["PersonID"])
    return jsonify(personData)
