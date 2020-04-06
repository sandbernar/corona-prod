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
from app.main.trains.models import TrainCode, TrainTravel
from app.main.trains.forms import TrainForm
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

@blueprint.route("/get_trains_by_date", methods=['POST'])
def get_trains_by_date():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    date = request.form.get("date")

    trains = TrainCode.query.filter_by(date=date)

    trains_options = "".join([ "<option value='{}'>{}</option>".format(
        f.id, "{} - {}".format(t.from_city, t.to_city)) for t in trains ])

    return json.dumps(trains_options, ensure_ascii=False)

@blueprint.route('/trains', methods=['GET'])
@login_required
def trains():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    form = TableSearchForm()
    regions = get_regions(current_user)

    if not form.region.choices:
        form.region.choices = [ (-1, c.all_regions) ] + [(r.id, r.name) for r in regions]

    trains = []
    filt = dict()

    q = TrainCode.query

    page = 1
    per_page = 5
    if "page" in request.args:
        page = int(request.args["page"])

    total_len = q.count()

    trains = q.offset((page-1)*per_page).limit(per_page).all()

    max_page = math.ceil(total_len/per_page)

    trains_count = dict()
    
    for t in trains:
    	trains_count[t.id] = TrainTravel.query.filter_by(train_code_id=t.id).count()

    form.process()
    return route_template('trains/trains', trains=trains, trains_count=trains_count, form=form, page=page, 
                                    max_page=max_page, total = total_len, constants=c)

@blueprint.route('/add_trains', methods=['GET', 'POST'])
def add_trains():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500        

    form = TrainForm()
    # regions = get_regions(current_user)

    if 'create' in request.form:
        new_dict = request.form.to_dict(flat=True)

        train = TrainCode.query.filter_by(code=new_dict['code'][0]).filter_by(date=new_dict['date']).first()
        if train:
            return route_template( 'trains/add_train', error_msg=_('Поезд уже зарегистрирован'), form=form, change=None)

        train = TrainCode(**new_dict)
        
        db.session.add(train)
        db.session.commit()

        return route_template( 'trains/add_train', form=form, change=_("Поезд был успешно добавлен"), error_msg=None)
    else:
        return route_template( 'trains/add_train', form=form, change=None, error_msg=None)


@blueprint.route('/train_profile', methods=['GET', 'POST'])
@login_required
def train_profile():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if "id" in request.args:
        train = TrainCode.query.filter_by(id=request.args["id"]).first()
        
        if not train:
            return render_template('errors/error-404.html'), 404
        else:
            form = FlightForm()

            form.date.default = train.date

            form.from_country.default = train.from_country
            form.from_city.default = train.from_city

            form.to_country.default = train.to_country
            form.to_city.default = train.to_city
            
            change = None
            error_msg = None
            patients = []
            
            train_type_id = TravelType.query.filter_by(value=c.train_type[0]).first().id

            q = db.session.query(Patient, TrainTravel)
            q = q.filter(Patient.travel_type_id == train_type_id)
            q = q.filter(Patient.travel_id == TrainTravel.id)
            q = q.filter(TrainTravel.train_code_id == train.id)
            letters = []

            # plane_seats = []
            # for result in q.all():
            #     if result[1].seat:
            #         plane_seats.append((result[1].seat, result[0]))

            seatmap = []
            patients_seat = {}

            # boardmap = []

            # if len(plane_seats):
            #     new_seats = {}
            #     for p in plane_seats:
            #         if p[0].lower() != c.board_team:
            #             match = re.findall(r'[A-Za-zА-Яа-я]+|\d+', p[0])
            #             if len(match) == 2:
            #                 letter = c.cyrillic_to_ascii.get(match[1].upper(), match[1].upper())

            #                 new_seats[int(match[0])] = new_seats.get(int(match[0]), {})
            #                 new_seats[int(match[0])][letter] = p[1]
            #                 letters.append(letter)
            #         else:
            #             pass
                
            #     new_seats = OrderedDict(sorted(new_seats.items(), key=lambda t: t[0]))
            #     seat_num = list(new_seats.keys())[-1]
            #     seat_letters = np.sort(np.unique(letters))

            #     for k in new_seats.keys():
            #         for s in new_seats[k].keys():
            #             seat = "{}{}".format(k, s)
            #             patients_seat[seat] = new_seats[k][s]

            #     for row in range(1, seat_num + 1):
            #         row_string = ""
            #         row_s = []
            #         row_seats = new_seats.get(row, {}).keys()
            #         for letter in seat_letters:
            #             row_letter = ""
            #             if letter in row_seats:
            #                 row_letter = "i" if new_seats[row][letter].is_infected else "o"
            #             else:
            #                 row_letter = "e"
            #             row_letter = "{}[,{}]".format(row_letter, "{}{}".format(row, letter))
            #             row_s.append(row_letter)

            #         if len(row_s) == 7:                        
            #             row_string = "{}{}_{}{}{}_{}{}"
            #         elif len(row_s) == 6:
            #             row_string = "{}{}{}_{}{}{}"
            #         else:
            #             row_string = "{}"*len(row_s)

            #         row_string = row_string.format(*row_s)

            #         seatmap.append(row_string)

            page = 1
            per_page = 5

            if "page" in request.args:
                page = int(request.args["page"])

            total_len = q.count()

            for p in q.offset((page-1)*per_page).limit(per_page).all():
                patients.append(p[0])

            max_page = math.ceil(total_len/per_page)
  
            form.process()
            return route_template('trains/train_profile', form = form, train=train, change=change, seatmap=seatmap,
                patients_seat=patients_seat, error_msg=error_msg, patients=patients, total_patients=total_len, max_page=max_page, page=page)
    else:    
        return render_template('errors/error-500.html'), 500

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