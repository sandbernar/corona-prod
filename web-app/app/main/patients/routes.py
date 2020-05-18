# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""
import os
import dateutil.parser
import math, json, re, itertools
import collections
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
from app.main.models import Region, Country, VisitedCountry, Infected_Country_Category, JobCategory
from app.main.models import TravelType, BorderControl, VariousTravel, BlockpostTravel, Address, HGBDToken
from app.main.patients.forms import PatientForm, UpdateProfileForm, AddFlightFromExcel, ContactedPatientsSearchForm, PatientsSearchForm
from app.main.patients.models import Patient, PatientStatus, ContactedPersons, State, PatientState
from app.main.patients.modules import ContactedPatientsTableModule, AllPatientsTableModule
from app.main.hospitals.models import Hospital, Hospital_Type
from app.main.flights_trains.models import FlightCode, FlightTravel, Train, TrainTravel
from app.main.forms import TableSearchForm
from app.main.routes import route_template
from app.main.util import get_regions, get_regions_choices, get_flight_code, populate_form, parse_date
from app.login.util import hash_pass

def prepare_patient_form(patient_form, with_old_data = False, with_all_travel_type=False, search_form=False):
    regions_choices = get_regions_choices(current_user, False)

    # Regions for select field
    if not patient_form.region_id.choices:
        patient_form.region_id.choices = [("", "")] if not search_form else [(-1, c.all_regions)]
        patient_form.region_id.choices += regions_choices

        if current_user.region_id != None and not search_form:
            patient_form.region_id.default = current_user.region_id

    if not search_form:
        if not patient_form.hospital_region_id.choices:
            patient_form.hospital_region_id.choices = regions_choices

        if current_user.region_id != None:
            patient_form.hospital_region_id.default = current_user.region_id            

    # TravelTypes for select fiels: Местный, Самолет итд
    if not patient_form.travel_type.choices:
        patient_form.travel_type.choices = [] if not with_all_travel_type else [c.all_travel_types]
        for typ in TravelType.query.all():
            if typ.value == c.old_data_type[0]:
                if with_old_data:
                    patient_form.travel_type.choices.append((typ.value, typ.name))
            else:
                patient_form.travel_type.choices.append((typ.value, typ.name))
        
        if not search_form:
            patient_form.travel_type.default = c.local_type[0]

    # Flight Travel
    if not patient_form.flight_arrival_date.choices:
        patient_form.flight_arrival_date.choices = [c.all_dates] if search_form else []

        dates = np.unique([f.date for f in FlightCode.query.all()])
        patient_form.flight_arrival_date.choices += [(date, date) for date in dates]
    
    # Flight Code id if exists
    if not patient_form.flight_code_id.choices:
        if patient_form.flight_arrival_date.choices and not search_form:
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
            typ_select.choices = [c.all_blockposts] if search_form else []
            borders = BorderControl.query.filter_by(travel_type_id = typ_id).all()
            typ_select.choices += [(b.id, b.name) for b in borders]

    # Blockpost Travel
    if not patient_form.blockpost_region_id.choices:
        patient_form.blockpost_region_id.choices = get_regions_choices(current_user, with_all_regions=search_form)

    # Hospital
    if not search_form:
        hospital_types = Hospital_Type.query.all()
        hospital_types = [(h.id, h.name) for h in hospital_types]
        patient_form.hospital_type_id.choices = hospital_types

    # States
    # patient_form.patient_status.choices = [(s[0], s[1]) for s in c.form_states]

    # Countries
    countries = Country.query.all()
    kz = Country.query.filter_by(code="KZ").first()

    # Job Category
    job_categories = JobCategory.query.all()
    if not patient_form.job_category_id.choices:
        patient_form.job_category_id.choices = [] if not search_form else [c.all_job_categories]
        if search_form:
            patient_form.job_category_id.default = c.all_job_categories[0]
            
        patient_form.job_category_id.choices += [c.unknown] + [(cat.id, cat.name) for cat in job_categories]

    def populate_countries_select(select_input, default, with_unknown = True):
        if not select_input.choices:
            select_input.choices = [(-1, c.unknown[1])] if with_unknown else []
            select_input.choices += [(c.id, c.name) for c in countries]
            select_input.default = default

    if not search_form:
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

def can_we_add_patient(request_dict):
    
    iin = request_dict.get('iin', '')
    if iin:
        if Patient.query.filter_by(iin = iin.strip()).count():
            return False, _("Пациент с данным ИИН уже есть в системе")

    pass_num = request_dict.get('pass_num', '')
    if pass_num:
        if Patient.query.filter_by(pass_num = request_dict['pass_num'].strip()).count():
            return False, _("Пациент с данным номером паспорта уже есть в системе")

    return True, None

def handle_add_update_patient(request_dict, final_dict, update_dict = {}):
    form_val_key = ['region_id', 'first_name', 'second_name', 'patronymic_name', 'dob', 'iin',
                    'citizenship_id', 'pass_num', 'country_of_residence_id', 'telephone', 'email', 
                    'job', 'job_position', 'hospital_id']
    
    # 1 Set values from request_dict
    for key in form_val_key:
        if key in request_dict:
            if key == "country_of_residence_id" and request_dict[key] == '-1':
                request_dict[key] = None
            final_dict[key] = request_dict[key]
    # 2
    final_dict['dob'] = parse_date(request.form['dob'])    
    final_dict['gender'] = None if int(request_dict['gender']) == -1 else int(request_dict['gender']) == 1

    if 'is_transit' in request_dict:
        final_dict['is_transit'] = int(request_dict['is_transit']) == 1

    if 'job_category_id' in request_dict:
        job_category_id = None if request_dict['job_category_id'] == "None" else request_dict['job_category_id']
        final_dict['job_category_id'] = job_category_id

    # 3
    travel_type = TravelType.query.filter_by(value=request_dict['travel_type']).first()
    if travel_type.value != c.old_data_type[0]:
        final_dict['travel_type_id'] = travel_type.id if travel_type else None

    # 5
    # Home Address
    home_address = process_address(request_dict, address=update_dict.get("home_address", None))
    final_dict['home_address_id'] = home_address.id

    # Job Address
    job_address = process_address(request_dict, "job", False, address=update_dict.get("job_address", None))
    final_dict['job_address_id'] = job_address.id

def handle_after_patient(request_dict, final_dict, patient, update_dict = {}, update_patient=True):
    if not update_patient:
        patient.is_found = patient.addState(State.query.filter_by(value=c.state_found[0]).first())
        print(final_dict)
        
        if final_dict['is_transit'] == True:
            patient.addState(State.query.filter_by(value=c.state_is_transit[0]).first())

    travel_type = request_dict['travel_type']
    if travel_type:
        if travel_type == c.flight_type[0]:
            f_travel = update_dict.get('flight_travel', FlightTravel(patient_id = patient.id))
            
            f_code_id = request_dict['flight_code_id']
            seat = request_dict.get('flight_seat', None)
            
            if f_travel.flight_code_id != f_code_id or f_travel.seat != seat:
                f_travel.flight_code_id = f_code_id
                f_travel.seat = seat

                db.session.add(f_travel)
                db.session.commit()
        elif travel_type == c.train_type[0]:
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
        elif travel_type == c.blockpost_type[0]:
            blockpost_t = update_dict.get('blockpost_travel', BlockpostTravel(patient_id = patient.id))
            
            date = parse_date(request_dict['arrival_date'])
            blockpost_r_id = request_dict['blockpost_region_id']
            
            if blockpost_t.region_id != blockpost_r_id or blockpost_t.date != date:
                blockpost_t.date = date
                blockpost_t.region_id = blockpost_r_id

                db.session.add(blockpost_t)
                db.session.commit()
        elif travel_type == c.old_data_type[0]:
            pass                     
        else:
            border_form_key = None

            if travel_type == c.by_auto_type[0]:
                border_form_key = 'auto_border_id'
            elif travel_type == c.by_foot_type[0]:
                border_form_key = 'foot_border_id'
            elif travel_type == c.by_sea_type[0]:
                border_form_key = 'sea_border_id'
            
            if border_form_key:
                v_travel = update_dict.get('various_travel', VariousTravel(patient_id = patient.id))

                date = parse_date(request_dict['arrival_date'])
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

    select_contacted = None

    select_contacted_id = request.args.get("select_contacted_id", None)
    if select_contacted_id:
        try:
            select_contacted = Patient.query.filter_by(id=select_contacted_id).first()
        except exc.SQLAlchemyError:
            return render_template('errors/error-400.html'), 400             

    if 'create' in request.form:
        request_dict = request.form.to_dict(flat=True)
        final_dict = {'created_by_id': current_user.id}
        
        should_we_add_patient, message = can_we_add_patient(request_dict)
        if not should_we_add_patient:
            return jsonify({"error": message})
        # create Patient
        handle_add_update_patient(request_dict, final_dict)        
        patient = Patient(**final_dict)
        db.session.add(patient)
        db.session.commit()

        # Create Travels and VisitedCountries to created Patient
        handle_after_patient(request_dict, final_dict, patient, update_patient=False)
        if select_contacted:
            try:
                contacted = ContactedPersons(infected_patient_id=select_contacted.id, contacted_patient_id=patient.id)
                db.session.add(contacted)
                db.session.commit()
            except exc.SQLAlchemyError:
                return jsonify({"error": _("Ошибка при добавлении контактной связи")})

            return jsonify({"patient_id": patient.id, "selected_patient_id": select_contacted.id})
        return jsonify({"patient_id": patient.id})
    else:
        return route_template( 'patients/add_person', form=patient_form, select_contacted=select_contacted,
                                added=False, error_msg=None, c=c)

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

                # status = c.no_status[0]
                # for s in c.patient_statuses:
                    # if s[0] in request.form:
                        # status = s[0]

                update_dict["home_address"] = patient.home_address
                update_dict["job_address"] = patient.job_address                    

                travel_type_key = None
                travel_value = None

                if patient.travel_type.value == c.flight_type[0]:
                    travel_type_key = 'flight_travel'
                    travel_value = FlightTravel.query.filter_by(patient_id=patient.id).first()
                elif patient.travel_type.value == c.train_type[0]:
                    travel_type_key = 'train_travel'
                    travel_value = TrainTravel.query.filter_by(patient_id=patient.id).first()
                elif patient.travel_type.value == c.blockpost_type[0]:
                    travel_type_key = 'blockpost_travel'
                    travel_value = BlockpostTravel.query.filter_by(patient_id=patient.id).first()
                elif patient.travel_type.value == c.old_data_type[0]:
                    travel_type_key = c.old_data_type[0]
                    travel_value = OldDataTravel.query.filter_by(patient_id=patient.id).first()
                elif patient.travel_type.value in dict(c.various_travel_types).keys():
                    travel_type_key = 'various_travel'
                    travel_value = VariousTravel.query.filter_by(patient_id=patient.id).first()

                if request_dict['travel_type'] != patient.travel_type.value:
                        if request_dict['travel_type'] != c.old_data_type[0]  != c.local_type[0] and travel_value:
                            db.session.delete(travel_value)
                            db.session.commit()
                else:
                    update_dict[travel_type_key] = travel_value

                if patient.visited_country and len(patient.visited_country):
                    update_dict["visited_country"] = patient.visited_country[0]

                handle_add_update_patient(request_dict, final_dict, update_dict)
                handle_after_patient(request_dict, final_dict, patient, update_dict)

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

            return route_template('patients/profile', states=states, patient=patient, age=age, hospital_name=hospital_name,
                                    form = form, change = change, c=c, travel=travel)
    else:    
        return render_template('errors/error-500.html'), 500

@blueprint.route('/patient_edit_history', methods=['GET'])
@login_required
def patient_edit_history():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if "id" in request.args:
        patient = Patient.query.filter_by(id=request.args["id"]).first()
      
        if not patient:
            return render_template('errors/error-404.html'), 404
        else:
            sql = "select * from logging.t_history WHERE tabname='Patient' \
                AND new_val->>'id'='{}';".format(patient.id)
            
            result = db.engine.execute(sql).fetchall()
            edit_history = []

            def get_field_display_name(field_name, field_data):
                display_name_dict = {"lng": _("Долгота"),
                                      "lat": _("Широта"),
                                      "region_id": _("Регион"),
                                      "gender": _("Пол"),
                                      "travel_type_id": _("Тип Въезда"),
                                      "job_address_id": _("Адрес Работы"),
                                      "home_address_id": _("Домашний Адрес"),
                                      "first_name": _("Имя"),
                                      "second_name": _("Фамилия"),
                                      "patronymic_name": _("Отчество"),
                                      "is_found": _("Найден"),
                                      "is_infected": _("Инфицирован"),
                                      "dob": _("Дата Рождения"),
                                      "iin": _("ИИН"),
                                      "pass_num": _("Номер Паспорта"),
                                      "telephone": _("Телефон"),
                                      "email": _("Электронная Почта"),
                                      "country_id": _("Страна")}

                display_name = display_name_dict.get(field_name, None)
                display_name = field_name if display_name is None else display_name

                display_data = field_data
                if field_name == "region_id":
                    display_data = Region.query.filter_by(id = field_data).first().name
                elif field_name == "gender":
                    if display_data == True:
                        display_data = _("Мужчина")
                    elif display_data == False:
                        display_data = _("Женщина")
                    elif display_data == None:
                        display_data = _("Неизвестно")
                elif field_name == "home_address_id" or field_name == "job_address_id":
                    display_data = "{} - id {}".format(_("Привязка адреса к профилю"), field_data)
                elif field_name == "country_id":
                    display_data = str(Country.query.filter_by(id=field_data).first())
                elif field_name == "travel_type_id":
                    display_data = str(TravelType.query.filter_by(id=field_data).first())

                if type(display_data) == bool:
                    if display_data == True:
                        display_data = _("Да")
                    elif display_data == False:
                        display_data = _("Нет")
                    elif display_data == None:
                        display_data = _("Неизвестно")

                return (display_name, display_data)

            ignore_keys_dict = ["created_date"]

            def get_edit_history(tabname, address_id, type_string):
                sql = "select * from logging.t_history WHERE tabname='{}' \
                    AND new_val->>'id'='{}';".format(tabname, address_id)

                all_history = []
                pred_val = None

                result = db.engine.execute(sql).fetchall()
                for r in result:
                    edit = dict()
                    if r['operation'] == 'INSERT':
                        pred_val = r['new_val']
                        edit['type'] = "{} {}".format(_("Создание"), type_string)
                    else:
                        edit['type'] = "{} {}".format(_("Обновление"), type_string)

                    edit['date'] = r['tstamp']

                    def get_rid_of_unhashable(dictionary):
                        items = list(dictionary.items())
                        for i, item in zip(range(len(items)), items):
                            if not isinstance(item[1], collections.Hashable):
                                items[i] = (item[0], None)

                        return items

                    if pred_val and r['new_val']:
                        update_data =  set(get_rid_of_unhashable(r['new_val'])) - set(get_rid_of_unhashable(pred_val))
                        pred_val = r['new_val']

                        if update_data:
                            for data in update_data:
                                data_entry = edit.copy()
                                data_entry['update_data'] = get_field_display_name(data[0], data[1])
                                
                                if data_entry['update_data'][0] not in ignore_keys_dict:
                                    all_history.append(data_entry)
                        elif r['operation'] == 'INSERT':
                            all_history.append(edit)

                return all_history

            edit_history += get_edit_history("Patient", patient.id, "Профиля")
            edit_history += get_edit_history("Address", patient.home_address_id, "Домашнего Адреса")
            edit_history += get_edit_history("Address", patient.job_address_id, "Рабочего Адреса")


            edit_history = sorted(edit_history, key=lambda k: k['date'])

            return route_template('patients/patient_edit_history', patient=patient, edit_history=edit_history)

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

@blueprint.route('/patients', methods=['GET', 'POST'])
@login_required
def patients():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    form = PatientsSearchForm()
    form = prepare_patient_form(form, with_all_travel_type=True, with_old_data=True, search_form=True)

    patients = []
    filt = dict()

    select_contacted = request.args.get("select_contacted_id", None)

    if select_contacted:
        try:
            patient_query = Patient.query.filter_by(id = request.args["select_contacted_id"])
            patient = patient_query.first()
        except exc.SQLAlchemyError:
            return render_template('errors/error-400.html'), 400        
        
        select_contacted = patient.id

    flight_codes_list = [c.all_flight_codes] + [ code.code for code in FlightCode.query.all() ]

    change = None
    error_msg = None

    if "delete" in request.args:
        change = _("Пользователь успешно удален")

    if "success" in request.args:
        change = request.args['success']
    elif "error" in request.args:
        error_msg = request.args['error']

    try:
        all_patients_table = AllPatientsTableModule(request, Patient.query, select_contacted,
                            search_form=form)

        if "download_xls" in request.args and all_patients_table.xls_response:
            return all_patients_table.xls_response

    except ValueError:
        return render_template('errors/error-500.html'), 500        

    form.process()

    return route_template('patients/patients', form=form, all_patients_table = all_patients_table, constants=c, 
                        flight_codes_list=flight_codes_list, change=change, error_msg=error_msg, select_contacted = select_contacted)

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
                patient_states = PatientState.query.filter_by(patient_id=patient.id).all()
                for patient_state in patient_states:
                    db.session.delete(patient_state)

                if ContactedPersons.query.filter_by(contacted_patient_id=patient_id).count():
                    return redirect("patients?error={}".format(_("У пациента есть контактные связи с инфицированными")))

                if ContactedPersons.query.filter_by(infected_patient_id=patient_id).count():
                    return redirect("patients?error={}".format(_("Пациент является нулевым в контактных связях")))

                home_address = patient.home_address
                job_address = patient.job_address

                patient_query.delete()                
                db.session.commit()

                if home_address:
                    db.session.delete(home_address)
                if job_address:
                    db.session.delete(job_address)
                                    
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
                                        header_button=[(_("Добавить Контактное Лицо"), "add_person?select_contacted_id={}".format(patient.id)),
                                            (_("Выбрать Контактное Лицо"), "patients?select_contacted_id={}".format(patient.id))]
                                        )
                if "download_xls" in request.args:
                    return contacted_patients_table.download_xls()

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

@blueprint.route('/select_contacted', methods=['POST'])
def select_contacted():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    try:
        if "infected_patient_id" and "contacted_patients[]" in request.form:
            infected_patient = Patient.query.filter_by(id = request.form["infected_patient_id"]).first()
            contacted_patients_ids = request.form.getlist('contacted_patients[]')

            contacted_patients = list()

            for cont_patient_id in contacted_patients_ids:
                contacted_patient = Patient.query.filter_by(id = cont_patient_id).first()
                
                if contacted_patient and ContactedPersons.query.filter_by(
                                        infected_patient_id=infected_patient.id).filter_by(
                                        contacted_patient_id=contacted_patient.id).count():
                    
                    return jsonify({"redirect_url": "/contacted_persons?id={}&error={}".format(infected_patient.id, _("Одна из контактных связей уже существует"))})

                contacted_patients.append(contacted_patient)

            for contacted_patient in contacted_patients:                
                    contacted = ContactedPersons(infected_patient_id=infected_patient.id, contacted_patient_id=contacted_patient.id)
                
                    db.session.add(contacted)
                    db.session.commit()
            
            return jsonify({"redirect_url": "/contacted_persons?id={}&success={}".format(infected_patient.id, "{} {}".format(len(contacted_patients), _("связей были успешно добавлены")))})
    except exc.SQLAlchemyError:
        return jsonify({"redirect_url": "/contacted_persons?id={}&error={}".format(infected_patient.id, _("Неизвестная Ошибка"))})


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

def get_all_states(patient_states):
    states = []

    for state in patient_states:
        attrs = state.attrs
        
        if state.value == c.state_hosp[0]:
            try:
                hospital = Hospital.query.filter_by(id = state.attrs["hospital_id"]).first()
            except exc.SQLAlchemyError:
                return jsonify({'description': _("Hospital not found")}), 405
            
            attrs["hospital_id"] = hospital.id
            attrs["hospital_region_id"] = hospital.region_id
            attrs["hospital_type_id"] = hospital.hospital_type_id
            print(attrs)

        states.append({
            "id":state.id,
            "name":state.name,
            "comment":state.comment,
            "detection_date":datetime.strftime(state.detection_date, "%Y-%m-%d"),
            "formatted_comment":state.formatted_comment,
            "formatted_detection_date":state.formatted_detection_date,
            "attrs":attrs
        })

    return states  

@blueprint.route('/get_states', methods=['POST'])
@login_required
def get_states():
    data = json.loads(request.data)
    patient = Patient.query.filter(Patient.id == data['patient_id']).first()

    if not patient:
        return jsonify({'description': 'Patient not found'}), 405

    states = get_all_states(patient.states)

    return jsonify({'status': 'loaded', 'states': states}), 200

@blueprint.route('/add_state', methods=['POST'])
@login_required
def add_state():
    data = json.loads(request.data)
    if data == None or 'value' not in data \
                    or 'comment' not in data \
                    or 'patient_id' not in data \
                    or 'detection_date' not in data:
        return jsonify({'description': 'not valid data'}), 403

    result = False
    patient = Patient.query.filter(Patient.id == data['patient_id']).first()
    if not patient:
        return jsonify({'description': 'Patient not found'}), 405
    state = State.query.filter_by(value=data["value"]).first()
    attrs = {}
    
    if data["value"] == c.state_hosp[0]:
        try:
            hospital = Hospital.query.filter_by(id = data["hospital_id"]).first()
            patient.hospital_id = hospital.id
            
            db.session.add(patient)
            db.session.commit()
        except exc.SQLAlchemyError:
            return jsonify({'description': _("Hospital not found")}), 405

        attrs["hospital_id"] = hospital.id

    result = patient.addState(state,
            detection_date=data["detection_date"],
            comment=data["comment"],
            attrs=attrs)
    if result == True:
        states = get_all_states(patient.states)

        return jsonify({'status': 'added', 'states': states}), 200
    return jsonify({'description': 'Couldn\'t be added'}), 300


@blueprint.route('/delete_state', methods=['POST'])
@login_required
def delete_state():
    data = json.loads(request.data)
    if data == None or 'patient_state_id' not in data \
                    or 'patient_id' not in data:
        return jsonify({'description': 'not valid data'}), 403
    result = False
    patient = Patient.query.filter_by(id=data['patient_id']).first()
    if not patient:
        return jsonify({'description': 'Patient not found'}), 405
    result = patient.deleteState(data["patient_state_id"])
    if result == True:
        states = get_all_states(patient.states)

        return jsonify({'status': 'deleted', 'states': states}), 200
    return jsonify({'description': 'Couldn\'t be deleted'}), 300

@blueprint.route('/update_state', methods=['POST'])
@login_required
def update_state():
    data = json.loads(request.data)
    if data == None or 'value' not in data \
                    or 'comment' not in data \
                    or 'patient_id' not in data \
                    or 'detection_date' not in data \
                    or 'patient_state_id' not in data:
        return jsonify({'description': 'not valid data'}), 403
    result = False
    patient = Patient.query.filter_by(id=data['patient_id']).first()
    if not patient:
        return jsonify({'description': 'Patient not found'}), 405
    patient_state = PatientState.query.filter_by(id=data["patient_state_id"]).first()
    if not patient_state:
        return jsonify({'description': 'PatientState not found'}), 406
    state = State.query.filter_by(value=data["value"]).first()

    attrs = {}
    
    if data["value"] == c.state_hosp[0]:
        if patient_state.attrs["hospital_id"] != data["hospital_id"]:
            try:
                hospital = Hospital.query.filter_by(id = data["hospital_id"]).first()
                patient.hospital_id = hospital.id
                
                db.session.add(patient)
                db.session.commit()
            except exc.SQLAlchemyError:
                return jsonify({'description': _("Hospital not found")}), 405

        attrs["hospital_id"] = hospital.id

    patient_state.attrs = attrs

    if state:
        patient_state.state_id = state.id
    patient_state.detection_date = data["detection_date"]
    patient_state.comment = data["comment"]

    result = patient.updateState(patient_state)
    if result == True:
        states = get_all_states(patient.states)

        return jsonify({'status': 'updated', 'states': states}), 200
    return jsonify({'description': 'Couldn\'t be updated'}), 300


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
