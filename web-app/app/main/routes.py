# -*- encoding: utf-8 -*-
"""
License: MIT
"""

from app.main import blueprint
from flask import render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app import login_manager, db
from app import constants as c
from jinja2 import TemplateNotFound

from app.main.patients.models import Patient, PatientStatus
from app.main.models import Region, Infected_Country_Category
from app.main.hospitals.models import Hospital, Hospital_Type

from datetime import datetime
from app.main.forms import TableSearchForm
import json
import requests
from flask_babelex import _


@blueprint.route('/index', methods=['GET'])
@login_required
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    q = Patient.query
    
    if not current_user.is_admin:
        q = q.filter_by(region_id=current_user.region_id)

    last_five_patients = []
    for p in q.order_by(Patient.id.desc()).limit(5).all():
        last_five_patients.append(p)

    coordinates_patients = []
    for p in q.all():
        if p.home_address.lat:
            coordinates_patients.append(p)

    patients = q.all()
    regions_list = Region.query.all()

    regions = dict()
    in_hospital_id = PatientStatus.query.filter_by(value=c.in_hospital[0]).first().id
    
    for region in regions_list:
        patient_region_query = Patient.query.filter_by(region_id=region.id)

        found_count = patient_region_query.filter_by(is_found=True).count()
        infected_count = patient_region_query.filter_by(is_infected = True).count()
        
        regions[region.name] = (found_count, infected_count)

    return route_template('index', last_five_patients=last_five_patients, coordinates_patients=coordinates_patients, regions=regions, constants=c)

@blueprint.route('/<template>')
def route_template(template, **kwargs):
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))
    try:
        q = Patient.query
    
        if not current_user.is_admin:
            q = q.filter_by(region_id=current_user.region_id)        

        # Total Patients
        total = q.filter_by().count()

        # Is Found
        is_found = q.filter_by(is_found=True).count()
        ratio = 0 if total == 0 else is_found/total
        is_found_str  = str("{}/{} ({}%)".format(is_found, total, format(ratio*100, '.2f')))
        
        # In Hospital
        in_hospital_status_id = PatientStatus.query.filter_by(value=c.in_hospital[0]).first().id
        in_hospital = q.filter_by(status_id=in_hospital_status_id).count()
        ratio = 0 if is_found == 0 else in_hospital/is_found
        in_hospital_str = str("{}/{} ({}%)".format(in_hospital, is_found, format(ratio*100, '.2f')))

        # Is Infected
        is_infected = q.filter_by(is_infected=True).count()
        ratio = 0 if total == 0 else is_infected/total
        is_infected_str  = str("{}/{} ({}%)".format(is_infected, total, format(ratio*100, '.2f')))

        return render_template(template + '.html', total_kz_patients = str(total), is_found_str = is_found_str,
                                in_hospital_str = in_hospital_str, is_infected_str = is_infected_str, **kwargs)

    except TemplateNotFound:
        return render_template('errors/error-404.html'), 404
    
    # except:
        # return render_template('error-500.html'), 500

@blueprint.route("/get_hospital_by_region", methods=['POST'])
def get_hospital_by_region():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    region_id = request.form.get("region_id")
    hospital_type_id = request.form.get("hospital_type_id")

    hospitals = Hospital.query.filter_by(region_id=int(region_id), hospital_type_id=int(hospital_type_id))

    hospitals_options = "".join([ "<option value='{}'>{}</option>".format(h.id, h.name) for h in hospitals ])

    return json.dumps(hospitals_options, ensure_ascii=False)

@blueprint.route('/countries_categories')
@login_required
def countries_categories():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    categories = Infected_Country_Category.query.all()

    return route_template('countries_categories', categories=categories)

@blueprint.route("/help", methods=['POST'])
@login_required
def help_route():
    return render_template('help.html')