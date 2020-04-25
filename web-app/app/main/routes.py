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
from flask import jsonify
import time
import json
from functools import wraps
from flask import redirect, request, current_app
import math
from functools import lru_cache


from app.main.patients.models import Patient, PatientState, State
from app.main.models import Region, Infected_Country_Category, Address
from app.main.hospitals.models import Hospital, Hospital_Type

from datetime import datetime
from app.main.forms import TableSearchForm
import json
import requests
from flask_babelex import _
from sqlalchemy import exc


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

    # coordinates_patients = []
    # for p in q.all():
    #     if p.home_address.lat:
    #         coordinates_patients.append(p)

    # patients = q.all()
    regions_list = Region.query.all()

    regions = dict()
    # in_hospital_id = PatientStatus.query.filter_by(value=c.in_hospital[0]).first().id

    for region in regions_list:
        patient_region_query = Patient.query.filter_by(region_id=region.id)

        found_count = patient_region_query.filter(Patient.is_found==True).count()
        infected_count = patient_region_query.filter(Patient.is_infected==True).count()

        regions[region.name] = (found_count, infected_count)

    return route_template('index', last_five_patients=last_five_patients, regions=regions, constants=c)


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
        # found_state_id = State.query.filter_by(name=c.state_found).first().id
        # is_found = PatientState.query.filter_by(state_id=found_state_id).count()
        is_found = q.filter(Patient.is_found==True).count()
        ratio = 0 if total == 0 else is_found / total
        is_found_str = str("{}/{} ({}%)".format(is_found, total, format(ratio * 100, '.2f')))


        # in_hosp_state_id = State.query.filter_by(name=c.state_hosp).first().id
        # in_hospital = PatientState.query.filter_by(state_id=in_hosp_state_id).count()
        in_hospital = q.filter(Patient.in_hospital==True).count()
        # in_hospital = 0
        ratio = 0 if is_found == 0 else in_hospital / is_found
        in_hospital_str = str("{}/{} ({}%)".format(in_hospital,
                                                   is_found, format(ratio * 100, '.2f')))

        # Is Infected
        # infected_state_id = State.query.filter_by(name=c.state_infec).first().id
        # is_infected = PatientState.query.filter_by(state_id=infected_state_id).count()
        is_infected = q.filter(Patient.is_infected==True).count()
        ratio = 0 if total == 0 else is_infected / total
        is_infected_str = str("{}/{} ({}%)".format(is_infected, total, format(ratio * 100, '.2f')))

        return render_template(template + '.html', total_kz_patients=str(total), is_found_str=is_found_str,
                               in_hospital_str=in_hospital_str, is_infected_str=is_infected_str, **kwargs)

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

    hospitals = Hospital.query.filter_by(region_id=int(
        region_id), hospital_type_id=int(hospital_type_id))

    hospitals_options = "".join(
        ["<option value='{}'>{}</option>".format(h.id, h.name) for h in hospitals])

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

# move to another dir


def support_jsonp(f):
    """Wraps JSONified output for JSONP"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            content = str(callback) + '(' + str(f().data.decode("utf-8")) + ')'
            return current_app.response_class(content, mimetype='application/json')
        else:
            return f(*args, **kwargs)
    return decorated_function


# def deg2num(lat_deg, lon_deg, zoom):
#     lat_rad = math.radians(lat_deg)
#     n = 2.0 ** zoom
#     xtile = int((lon_deg + 180.0) / 360.0 * n)
#     ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
#     return (xtile, ytile)

# def num2deg(xtile, ytile, zoom):
#     n = 2.0 ** zoom
#     lon_deg = xtile / n * 360.0 - 180.0
#     lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
#     lat_deg = math.degrees(lat_rad)
#     return (lat_deg, lon_deg)

@blueprint.route("/patients_content_by_id", methods=['POST'])
def patients_content_by_id():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))
    
    ids = request.get_json()
    if not "ids" in ids:
        return render_template('errors/error-400.html'), 400

    ids = ids["ids"]

    q = Patient.query

    response = []

    for i in ids:
        p = None
        try:
            p = q.filter_by(id=i).first()
        except exc.SQLAlchemyError:
            return render_template('errors/error-400.html'), 400
        if not p:
            continue
        is_found = _("Нет")
        is_infected = _("Нет")
        if p.is_found:
            is_found = _("Да")
        if p.is_infected:
            is_infected = _("Да")
        response.append({
            "id": i,
            "balloonContent": '<a href="/patient_profile?id=' + str(p.id) + '">' + repr(p) +
                              '</a><br><strong>Регион</strong>:' + repr(p.region) + 
                              '<br><strong>Адрес</strong>: ' + repr(p.home_address) + 
                              '<br><strong>Найден</strong>: ' + is_found + 
                              '<br><strong>Инфицирован</strong>: ' + is_infected,
                              #'<br><strong>Статус</strong>:' + _("Неизвестно") if not p.status else p.status.name + '<br>',
            "clusterCaption": repr(p)
        })

    return jsonify(response)


def get_ttl_hash(seconds=3600):
    """Return the same value withing `seconds` time period"""
    return round(time.time() / seconds)


@lru_cache()
def getR(bbox_x1, bbox_y1, bbox_x2, bbox_y2, ttl_hash=None):
    del ttl_hash
    r = jsonify(type="FeatureCollection", features=[i.serialize for i in Patient.query.join(Address, Patient.home_address_id == Address.id).filter(Address.lng != None).filter(Address.lat >= bbox_x1).filter(
        Address.lat <= bbox_x2).filter(Address.lng >= bbox_y1).filter(Address.lng <= bbox_y2)])
    return r


@blueprint.route("/patients_within_tiles")
@login_required
@support_jsonp
def patients_within_tiles():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))
    if not "bbox" in request.args:
        return render_template('errors/error-400.html'), 400
    latlng = request.args["bbox"].split(',')
    bbox_x1 = float(latlng[0])
    bbox_y1 = float(latlng[1])
    bbox_x2 = float(latlng[2])
    bbox_y2 = float(latlng[3])
    r = getR(bbox_x1, bbox_y1, bbox_x2, bbox_y2, ttl_hash=get_ttl_hash())
    return r
