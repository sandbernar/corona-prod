# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""
from app.main import blueprint
from flask import render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app import login_manager, db

from app.main.models import Region
from app.main.flights.models import FlightCode, FlightTravel
from app.main.flights.forms import AddFlightForm
from app.main.forms import TableSearchForm

import math

from app.main.util import get_regions, get_regions_choices
from app.login.util import hash_pass
from flask_babelex import _
from app.main.routes import route_template
from jinja2 import TemplateNotFound
from app import constants as c

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

    form.process()
    return route_template('flights/flights', flights=flights, flights_count=flights_count, form=form, page=page, 
                                    max_page=max_page, total = total_len, constants=c)

@blueprint.route('/add_flight', methods=['GET', 'POST'])
def add_flight():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500        

    form = AddFlightForm()
    # regions = get_regions(current_user)

    if 'create' in request.form:
        new_dict = request.form.to_dict(flat=True)
        print(new_dict)

        flight = FlightCode.query.filter_by(code=new_dict['code'][0]).filter_by(date=new_dict['date']).first()
        if flight:
            return route_template( 'flights/add_flight', error_msg=_('Рейс уже зарегистрировано'), form=form, change=None)

        flight = FlightCode(**new_dict)
        
        db.session.add(flight)
        db.session.commit()

        return route_template( 'flights/add_flight', form=form, change=_("Рейс был успешно добавлен"), error_msg=None)
    else:
        return route_template( 'flights/add_flight', form=form, change=None, error_msg=None)


# @blueprint.route('/user_profile', methods=['GET', 'POST'])
# @login_required
# def user_profile():
#     if not current_user.is_authenticated:
#         return redirect(url_for('login_blueprint.login'))

#     if not current_user.is_admin:
#         return render_template('errors/error-500.html'), 500        

#     if "id" in request.args:
#         user = User.query.filter_by(id=request.args["id"]).first()
        
#         if not user:
#             return render_template('errors/error-404.html'), 404
#         else:
#             form = UpdateUserForm()
            
#             change = None
#             error_msg = None
            
#             if 'update' in request.form:
#                 if request.form['username']:
#                     new_username = request.form['username']
                    
#                     if not new_username == user.username:  
#                         if not User.query.filter_by(username = new_username).count():
#                             user.username = new_username
#                         else:
#                             error_msg = _("Пользователь с таким логином уже существует")

#                 if not error_msg:
#                     if request.form['password']:
#                         password = request.form['password']

#                         user.password = hash_pass(password)

#                     user.telephone = request.form['telephone']
#                     user.email = request.form['email']

#                     db.session.add(user)
#                     db.session.commit()

#                     change = _("Данные обновлены")

#             form.username.default = user.username

#             form.email.default = user.email
#             form.telephone.default = user.telephone
            
#             form.region_id.choices = get_regions_choices(current_user)
#             form.region_id.default = user.region_id
  
#             form.process()
#             return route_template('users/user_profile', form = form, user=user, change=change, error_msg=error_msg)
#     else:    
#         return render_template('errors/error-500.html'), 500

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