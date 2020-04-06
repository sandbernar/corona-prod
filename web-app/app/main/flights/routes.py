# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""
from app.main import blueprint
from flask import render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app import login_manager, db

from app.main.models import Region, TravelType
from app.main.flights.models import FlightCode, FlightTravel
from app.main.flights.forms import FlightForm
from app.main.forms import TableSearchForm
from app.main.patients.models import Patient
from collections import OrderedDict

import numpy as np
import math
import re, json

from app.main.util import get_regions, get_regions_choices
from app.login.util import hash_pass
from flask_babelex import _
from app.main.routes import route_template
from jinja2 import TemplateNotFound
from app import constants as c

from sqlalchemy import exc

@blueprint.route("/get_flights_by_date", methods=['POST'])
def get_flights_by_date():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    date = request.form.get("date")

    flights = FlightCode.query.filter_by(date=date)

    flights_options = "".join([ "<option value='{}'>{}</option>".format(
        f.id, "{}, {} - {}".format(f.code, f.from_city, f.to_city)) for f in flights ])

    return json.dumps(flights_options, ensure_ascii=False)

@blueprint.route('/flights', methods=['GET'])
@login_required
def flights():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    form = TableSearchForm()
    regions = get_regions(current_user)

    if not form.region.choices:
        form.region.choices = [ (-1, c.all_regions) ] + [(r.id, r.name) for r in regions]

    flights = []
    filt = dict()

    q = FlightCode.query

    page = 1
    per_page = 5
    if "page" in request.args:
        page = int(request.args["page"])

    total_len = q.count()

    flights = q.offset((page-1)*per_page).limit(per_page).all()

    max_page = math.ceil(total_len/per_page)

    flights_count = dict()
    
    for f in flights:
    	flights_count[f.id] = FlightTravel.query.filter_by(flight_code_id=f.id).count()

    change = None
    if "message" in request.args:
        change = request.args['message']

    form.process()
    return route_template('flights/flights', flights=flights, flights_count=flights_count, form=form, page=page, 
                                    max_page=max_page, total = total_len, constants=c, change=change)

@blueprint.route('/add_flight', methods=['GET', 'POST'])
def add_flight():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500        

    form = FlightForm()
    # regions = get_regions(current_user)

    if 'create' in request.form:
        new_dict = request.form.to_dict(flat=True)

        flight = FlightCode.query.filter_by(code=new_dict['code'][0]).filter_by(date=new_dict['date']).first()
        if flight:
            return route_template( 'flights/add_flight', error_msg=_('Рейс уже зарегистрировано'), form=form, change=None)

        flight = FlightCode(**new_dict)
        
        db.session.add(flight)
        db.session.commit()

        message = _("Рейс успешно добавлен")

        return_url = "{}?message={}".format(url_for('main_blueprint.flights'), message)

        return redirect(return_url)
        # return route_template( 'flights/add_flight', form=form, change=_("Рейс был успешно добавлен"), error_msg=None)
    else:
        return route_template( 'flights/add_flight', form=form, change=None, error_msg=None)

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

            form.from_country.default = flight.from_country
            form.from_city.default = flight.from_city

            form.to_country.default = flight.to_country
            form.to_city.default = flight.to_city
            
            change = None
            error_msg = None
            patients = []
            
            flight_type_id = TravelType.query.filter_by(value=c.flight_type[0]).first().id

            q = db.session.query(Patient, FlightTravel)
            q = q.filter(Patient.travel_type_id == flight_type_id)
            q = q.filter(Patient.travel_id == FlightTravel.id)
            q = q.filter(FlightTravel.flight_code_id == flight.id)
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

            page = 1
            per_page = 5

            if "page" in request.args:
                page = int(request.args["page"])

            total_len = q.count()

            for p in q.offset((page-1)*per_page).limit(per_page).all():
                patients.append(p[0])

            max_page = math.ceil(total_len/per_page)
  
            form.process()
            return route_template('flights/flight_profile', form = form, flight=flight, change=change, seatmap=seatmap,
                patients_seat=patients_seat, error_msg=error_msg, patients=patients, total_patients=total_len, max_page=max_page, page=page)
    else:    
        return render_template('errors/error-500.html'), 500

@blueprint.route('/delete_flight', methods=['POST'])
@login_required
def delete_flight():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))
    
    message = _("Произошла Ошибка")
    print(message)

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
                    message = _("Рейс успешно удален")
            
            # add redirect

    return redirect("{}?message={}".format(url_for('main_blueprint.flights'), message))

# @blueprint.route('/delete_user', methods=['POST'])
# @login_required
# def delete_user():
#     if not current_user.is_authenticated:
#         return redirect(url_for('login_blueprint.login'))

#     if not current_user.is_admin:
#         return render_template('errors/error-500.html'), 500        
    
#     return_url = url_for('main_blueprint.users')

#     if len(request.form):
#         if "delete" in request.form:
#             user_id = request.form["delete"]
#             user = User.query.filter(User.id == user_id)

#             if user:
#                 user.delete()
#                 db.session.commit()

#     return redirect(return_url)