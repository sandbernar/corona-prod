# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""
from app.main import blueprint
from flask import render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app import login_manager, db

from app.main.models import Region, TravelType, Country

from app.main.flights_trains.models import FlightCode, FlightTravel, Train, TrainTravel
from app.main.flights_trains.forms import FlightTrainsForm, FlightForm, TrainForm, FlightSearchForm,\
                                            TrainSearchForm, PatientsSearchForm

from app.main.flights_trains.modules import TrainTableModule, FlightTableModule, PatientsTravelTableModule

from app.main.patients.models import Patient
from collections import OrderedDict
from datetime import datetime

import numpy as np
import math
import re, json

from app.main.util import get_regions_choices, populate_countries_select, parse_date, disable_form_fields
from app.main.modules import TableModule

from app.login.util import hash_pass
from flask_babelex import _
from app.main.routes import route_template
from jinja2 import TemplateNotFound
from app import constants as c

from sqlalchemy import exc, func

@blueprint.route("/get_flights_by_date", methods=['POST'])
def get_flights_by_date():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    date = request.form.get("date")
    flights_options = ""

    if date != "-1":
        flights = FlightCode.query.filter_by(date=parse_date(date))

        flights_options = "".join([ "<option value='{}'>{}</option>".format(
            f.id, "{}, {} - {}".format(f.code, f.from_city, f.to_city)) for f in flights ])

    return json.dumps(flights_options, ensure_ascii=False)

@blueprint.route("/get_trains_by_date_range", methods=['POST'])
def get_trains_by_date_range():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    departure_date = request.form.get("departure_date", None)
    arrival_date = request.form.get("arrival_date", None)

    if departure_date or arrival_date:
        trains = Train.query

        if departure_date:
            trains = trains.filter(Train.departure_date >= departure_date)

        if arrival_date:
            trains = trains.filter(Train.arrival_date <= arrival_date)

        trains_options = "".join([ "<option value='{}'>{}</option>".format(
            t.id, "{} - {}, {} - {}".format(t.departure_date, t.arrival_date, t.from_city, t.to_city)) for t in trains ])

        return json.dumps(trains_options, ensure_ascii=False)

    return json.dumps("error")

def flights_trains(request):
    change = None
    error_msg = None

    if "success" in request.args:
        change = request.args['success']
    elif "error" in request.args:
        error_msg = request.args['error']

    return change, error_msg

def populate_add_flight_train_form(form):
    default_country = Country.query.filter_by(code="KZ").first().id

    populate_countries_select(form.from_country_id, default_country)
    populate_countries_select(form.to_country_id, default_country)

    form.process()
    countries = Country.query.all()

def populate_search_form(form, request):
    populate_countries_select(form.from_country_id, default_state=(-1, _("Все Страны")))
    populate_countries_select(form.to_country_id, default_state=(-1, _("Все Страны")))

def populate_profile_flight_train_form(form, travel):
    populate_countries_select(form.from_country_id)
    populate_countries_select(form.to_country_id)

@blueprint.route('/flights', methods=['GET'])
@login_required
def flights():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    change, error_msg = flights_trains(request)
    form = FlightSearchForm()

    populate_search_form(form, request)
    flights_table = FlightTableModule(request, form, [(_("Добавить Рейс"), "/add_flight")])

    form.process()

    return route_template('flights_trains/flights_trains',  form=form, flights_table=flights_table, constants=c, 
                            change=change, error_msg=error_msg, is_trains = False)

@blueprint.route('/trains', methods=['GET'])
@login_required
def trains():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    change, error_msg = flights_trains(request)
    form = TrainSearchForm()
    
    populate_search_form(form, request)
    flights_table = TrainTableModule(request, form, [(_("Добавить ЖД Рейс"), "/add_train")])

    form.process()

    return route_template('flights_trains/flights_trains',  form=form, flights_table=flights_table, constants=c, 
                            change=change, error_msg=error_msg, is_trains = True)                                       

@blueprint.route('/add_flight', methods=['GET', 'POST'])
def add_flight():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    form = FlightForm()
    populate_add_flight_train_form(form)

    if 'create' in request.form:
        new_dict = request.form.to_dict(flat=True)

        flight = FlightCode.query.filter_by(code=new_dict['code']).filter_by(date=new_dict['date']).first()
        if flight:
            return route_template( 'flights_trains/add_flight_train', error_msg=_('Рейс уже зарегистрирован'), 
                                    form=form, change=None, is_trains = False)

        flight = FlightCode(**new_dict)
        
        db.session.add(flight)
        db.session.commit()

        message = _("Рейс успешно добавлен")

        return_url = "{}?success={}".format(url_for('main_blueprint.flights'), message)

        return redirect(return_url)
    else:
        return route_template( 'flights_trains/add_flight_train', form=form, change=None, error_msg=None, is_trains = False)

@blueprint.route('/add_train', methods=['GET', 'POST'])
def add_train():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    form = TrainForm()
    populate_add_flight_train_form(form)

    if 'create' in request.form:
        new_dict = request.form.to_dict(flat=True)

        train_q = Train.query.filter_by(departure_date=new_dict['departure_date'])
        train_q = train_q.filter_by(arrival_date=new_dict['arrival_date'])
        train_q = train_q.filter_by(from_city=new_dict['from_city'])
        train_q = train_q.filter_by(to_city=new_dict['to_city'])
        train = train_q.first()

        if train:
            return route_template( 'flights_trains/add_flight_train', error_msg=_('ЖД Рейс уже зарегистрирован'), 
                                    form=form, change=None, is_trains = True)

        train = Train(**new_dict)
        
        db.session.add(train)
        db.session.commit()

        message = _("Рейс успешно добавлен")

        return_url = "{}?success={}".format(url_for('main_blueprint.trains'), message)

        return redirect(return_url)
    else:
        return route_template( 'flights_trains/add_flight_train', form=form, change=None, error_msg=None, is_trains = True)        

def generate_plane_seatmap(q):
    letters = []

    plane_seats = []
    for result in q.all():
        if result[1].seat:
            plane_seats.append((result[1].seat, result[0]))

    seatmap = []
    patients_seat = {}

    boardmap = []

    try:
        if len(plane_seats):
            new_seats = {}
            for p in plane_seats:
                if p[0].lower() != c.board_team:
                    match = re.findall(r'[A-Za-zА-Яа-я]+|\d+', p[0])
                    if len(match) == 2:
                        letter = c.cyrillic_to_ascii.get(match[1].upper(), match[1].upper())

                        new_seats[int(match[0])] = new_seats.get(int(match[0]), {})
                        new_seats[int(match[0])][letter] = p[1]
                        letters.append(letter)
                else:
                    pass
            
            if new_seats:
                new_seats = OrderedDict(sorted(new_seats.items(), key=lambda t: t[0]))
                seat_num = list(new_seats.keys())[-1]
                seat_letters = np.sort(np.unique(letters))

                for k in new_seats.keys():
                    for s in new_seats[k].keys():
                        seat = "{}{}".format(k, s)
                        patients_seat[seat] = new_seats[k][s]

                for row in range(1, seat_num + 1):
                    row_string = ""
                    row_s = []
                    row_seats = new_seats.get(row, {}).keys()
                    for letter in seat_letters:
                        row_letter = ""
                        if letter in row_seats:
                            row_letter = "i" if new_seats[row][letter].is_infected else "o"
                        else:
                            row_letter = "e"
                        row_letter = "{}[,{}]".format(row_letter, "{}{}".format(row, letter))
                        row_s.append(row_letter)

                    if len(row_s) == 7:                        
                        row_string = "{}{}_{}{}{}_{}{}"
                    elif len(row_s) == 6:
                        row_string = "{}{}{}_{}{}{}"
                    else:
                        row_string = "{}"*len(row_s)

                    row_string = row_string.format(*row_s)

                    seatmap.append(row_string)
    except ValueError:
        print("Check Value of Seat")
        pass

    return seatmap, patients_seat

@blueprint.route('/flight_profile', methods=['GET', 'POST'])
@login_required
def flight_profile():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if "id" in request.args:
        flight = None
        try:
            flight = FlightCode.query.filter_by(id=request.args["id"]).first()
        except exc.SQLAlchemyError:
            return render_template('errors/error-400.html'), 400

        if not flight:
            return render_template('errors/error-404.html'), 404
        else:
            form = FlightForm()
            
            disable_form_fields(form)

            form.code.default = flight.code
            form.date.default = flight.date

            populate_profile_flight_train_form(form, flight)

            form.from_country_id.default = flight.from_country_id
            form.from_city.default = flight.from_city

            form.to_country_id.default = flight.to_country_id
            form.to_city.default = flight.to_city

            change = None
            error_msg = None
            
            flight_type_id = TravelType.query.filter_by(value=c.flight_type[0]).first().id

            q = db.session.query(Patient, FlightTravel)
            q = q.filter(Patient.travel_type_id == flight_type_id)
            q = q.filter(Patient.id == FlightTravel.patient_id)
            q = q.filter(FlightTravel.flight_code_id == flight.id)

            patients_search_form = PatientsSearchForm()

            if not patients_search_form.region.choices:
                patients_search_form.region.choices = get_regions_choices(current_user)
            
            patients_table = PatientsTravelTableModule(request, q, patients_search_form)

            seatmap, patients_seat = generate_plane_seatmap(q)

            form.process()
            patients_search_form.process()

            return route_template('flights_trains/flight_train_profile', form = form, patients_search_form = patients_search_form,
             travel=flight, change=change, seatmap=seatmap, patients_seat=patients_seat, error_msg=error_msg,
              is_trains = False, patients_table=patients_table)
    else:    
        return render_template('errors/error-500.html'), 500

@blueprint.route('/train_profile', methods=['GET', 'POST'])
@login_required
def train_profile():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if "id" in request.args:
        train = None
        try:
            train = Train.query.filter_by(id=request.args["id"]).first()
        except exc.SQLAlchemyError:
            return render_template('errors/error-400.html'), 400

        if not train:
            return render_template('errors/error-404.html'), 404
        else:
            form = TrainForm()

            disable_form_fields(form)

            form.departure_date.default = train.departure_date
            form.arrival_date.default = train.arrival_date

            populate_profile_flight_train_form(form, train)
            
            change = None
            error_msg = None
            patients = []
            
            train_type_id = TravelType.query.filter_by(value=c.train_type[0]).first().id

            q = db.session.query(Patient, TrainTravel)
            q = q.filter(Patient.travel_type_id == train_type_id)
            q = q.filter(Patient.id == TrainTravel.patient_id)
            q = q.filter(TrainTravel.train_id == train.id)
            
            patients_search_form = PatientsSearchForm()

            if not patients_search_form.region.choices:
                patients_search_form.region.choices = get_regions_choices(current_user)
            
            patients_table = PatientsTravelTableModule(request, q, patients_search_form, True)
  
            form.process()
            return route_template('flights_trains/flight_train_profile', form = form, travel=train, change=change,
                                    patients_search_form = patients_search_form, error_msg=error_msg, 
                                    patients_table=patients_table, is_trains=True, seatmap=[], patients_seat={})
    else:    
        return render_template('errors/error-500.html'), 500

@blueprint.route('/delete_flight', methods=['POST'])
@login_required
def delete_flight():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))
    
    message_type = "error"
    message = _("Произошла Ошибка")

    if len(request.form):
        if "delete" in request.form:
            flight_id = request.form["delete"]

            # exception added only for first query
            flight = None
            try:
                flight = FlightCode.query.filter(FlightCode.id == flight_id).first()
            except exc.SQLAlchemyError:
                return render_template('errors/error-400.html'), 400

            if flight:
                if FlightTravel.query.filter_by(flight_code_id = flight.id).count():
                    message = _("Рейс содержит пассажиров")
                else:
                    db.session.delete(flight)
                    db.session.commit()
                    message_type = "success"
                    message = _("Рейс успешно удален")
            
            # add redirect

    return redirect("{}?{}={}".format(url_for('main_blueprint.flights'), message_type, message))

@blueprint.route('/delete_train', methods=['POST'])
@login_required
def delete_train():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))
    
    message_type = "error"
    message = _("Произошла Ошибка")

    if len(request.form):
        if "delete" in request.form:
            train_id = request.form["delete"]

            # exception added only for first query
            train = None
            try:
                train = Train.query.filter(Train.id == train_id).first()
            except exc.SQLAlchemyError:
                return render_template('errors/error-400.html'), 400

            if train:
                if TrainTravel.query.filter_by(train_id = train.id).count():
                    message = _("ЖД Рейс содержит пассажиров")
                else:
                    db.session.delete(train)
                    db.session.commit()
                    message_type = "success"
                    message = _("ЖД Рейс успешно удален")
            
            # add redirect

    return redirect("{}?{}={}".format(url_for('main_blueprint.trains'), message_type, message))