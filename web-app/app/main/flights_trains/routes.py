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
from app.main.flights_trains.forms import FlightTrainsForm, FlightForm, TrainForm, FlightSearchForm, TrainSearchForm
from app.main.patients.models import Patient
from collections import OrderedDict
from datetime import datetime

import numpy as np
import math
import re, json

from app.main.util import get_regions, get_regions_choices
from app.main.modules import TableModule

from app.login.util import hash_pass
from flask_babelex import _
from app.main.routes import route_template
from jinja2 import TemplateNotFound
from app import constants as c

from sqlalchemy import exc

def populate_countries_select(select_input, default, countries):
    if not select_input.choices:
        select_input.choices = [(c.id, c.name) for c in countries]
        select_input.default = default

@blueprint.route("/get_flights_by_date", methods=['POST'])
def get_flights_by_date():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    date = request.form.get("date")

    flights = FlightCode.query.filter_by(date=date)

    flights_options = "".join([ "<option value='{}'>{}</option>".format(
        f.id, "{}, {} - {}".format(f.code, f.from_city, f.to_city)) for f in flights ])

    return json.dumps(flights_options, ensure_ascii=False)

@blueprint.route("/get_trains_by_date_range", methods=['POST'])
def get_trains_by_date_range():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    departure_date = request.form.get("departure_date", None)
    arrival_date = request.form.get("arrival_date", None)

    if departure_date:
        trains = Train.query

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
    countries = Country.query.all()

    populate_countries_select(form.from_country_id, default_country, countries)
    populate_countries_select(form.to_country_id, default_country, countries)

    form.process()

def populate_profile_flight_train_form(form, travel):
    countries = Country.query.all()

    populate_countries_select(form.from_country_id, travel.from_country_id, countries)
    populate_countries_select(form.to_country_id, travel.to_country_id, countries)

    form.from_city.default = travel.from_city

    form.to_city.default = travel.to_city

@blueprint.route('/flights', methods=['GET'])
@login_required
def flights():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    change, error_msg = flights_trains(request)
    form = FlightSearchForm()

    table_head_params = OrderedDict()
    table_head_params[_("Код Рейса")] = ["code"]
    table_head_params[_("Дата")] = ["date"]
    table_head_params[_("Из")] = ["from_country", "from_city"]
    table_head_params[_("В")] = ["to_country", "to_city"]
    table_head_params[_("Кол-во Прибывших")] = []
    q = FlightCode.query

    def print_entry(result):
        code = (result, "/flight_profile?id={}".format(result.id))
        date = result.date
        from_country = "{}, {}".format(result.from_country, result.from_city)
        to_country = "{}, {}".format(result.to_country, result.to_city)
        passengers_num = FlightTravel.query.filter_by(flight_code_id=result.id).count()

        return [code, date, from_country, to_country, passengers_num]

    if "code" in request.args:
        code = request.args["code"]
        q = q.filter(FlightCode.code.contains(code))
        form.code.default = code

    if "date" in request.args:
        if request.args["date"]:
            date = datetime.strptime(request.args["date"], '%Y-%m-%d')

            q = q.filter_by(date=date)
            form.date.default = date

    flights_table = TableModule(request, q, table_head_params, print_entry, (_("Добавить Рейс"), "/add_flight"))

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

    table_head_params = OrderedDict()
    table_head_params[_("Профиль Рейса")] = []
    table_head_params[_("Дата Отправления")] = ["departure_date"]
    table_head_params[_("Дата Прибытия")] = ["arrival_date"]
    table_head_params[_("Из")] = ["from_country", "from_city"]
    table_head_params[_("В")] = ["to_country", "to_city"]
    table_head_params[_("Кол-во Прибывших")] = []
    
    q = Train.query

    def print_entry(result):
        profile = (_("Открыть Профиль"), "/train_profile?id={}".format(result.id))
        departure_date = result.departure_date
        arrival_date = result.arrival_date
        from_country = "{}, {}".format(result.from_country, result.from_city)
        to_country = "{}, {}".format(result.to_country, result.to_city)
        passengers_num = TrainTravel.query.filter_by(train_id=result.id).count()

        return [profile, departure_date, arrival_date, from_country, to_country, passengers_num]

    if "departure_date" in request.args:
        if request.args["departure_date"]:
            departure_date = datetime.strptime(request.args["departure_date"], '%Y-%m-%d')
            
            q = q.filter(Train.departure_date >= departure_date)
            form.departure_date.default = departure_date

    if "arrival_date" in request.args:
        if request.args["arrival_date"]:
            arrival_date = datetime.strptime(request.args["arrival_date"], '%Y-%m-%d')
            
            q = q.filter(Train.arrival_date <= arrival_date)
            form.arrival_date.default = arrival_date

    flights_table = TableModule(request, q, table_head_params, print_entry, (_("Добавить ЖД Рейс"), "/add_train"))

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

            form.code.default = flight.code
            form.date.default = flight.date

            populate_profile_flight_train_form(form, flight)
            
            change = None
            error_msg = None
            
            flight_type_id = TravelType.query.filter_by(value=c.flight_type[0]).first().id

            q = db.session.query(Patient, FlightTravel)
            q = q.filter(Patient.travel_type_id == flight_type_id)
            q = q.filter(Patient.id == FlightTravel.patient_id)
            q = q.filter(FlightTravel.flight_code_id == flight.id)
            
            table_head_params = OrderedDict()
            table_head_params[_("ФИО")] = ["second_name"]
            table_head_params[_("Телефон")] = ["telephone"]
            table_head_params[_("Регион")] = []
            table_head_params[_("Страна последние 14 дней")] = []
            table_head_params[_("Место")] = ["seat"]

            def print_entry(result):
                full_name = (result[0], "/patient_profile?id={}".format(result[0].id))
                telephone = result[0].telephone
                region = result[0].region

                if result[0].visited_country == None:
                    visited_country = _("Неизвестно")
                else:                
                    visited_country = ", ".join([ str(c) for c in result[0].visited_country])

                seat = result[1].seat

                return [full_name, telephone, region, visited_country, seat]

            patients_table = TableModule(request, q, table_head_params, print_entry)

            seatmap, patients_seat = generate_plane_seatmap(q)

            form.process()
            return route_template('flights_trains/flight_train_profile', form = form, travel=flight, change=change, seatmap=seatmap,
                patients_seat=patients_seat, error_msg=error_msg, is_trains = False, patients_table=patients_table)
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
            
            table_head_params = OrderedDict()
            table_head_params[_("ФИО")] = ["first_name", "second_name", "patronymic_name"]
            table_head_params[_("Телефон")] = ["telephone"]
            table_head_params[_("Регион")] = []
            table_head_params[_("Страна последние 14 дней")] = []
            table_head_params[_("Вагон")] = ["wagon"]
            table_head_params[_("Место")] = ["seat"]

            def print_entry(result):
                full_name = (result[0], "/patient_profile?id={}".format(result[0].id))
                telephone = result[0].telephone
                region = result[0].region
                visited_country = ", ".join([ str(c) for c in result[0].visited_country])
                wagon = result[1].wagon
                seat = result[1].seat

                return [full_name, telephone, region, visited_country, wagon, seat]

            patients_table = TableModule(request, q, table_head_params, print_entry)
  
            form.process()
            return route_template('flights_trains/flight_train_profile', form = form, travel=train, change=change, 
                                    error_msg=error_msg, patients_table=patients_table, is_trains=True, seatmap=[], patients_seat={})
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