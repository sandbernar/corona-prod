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

import uuid
from sqlalchemy import text

@blueprint.route('/index', methods=['GET'])
@login_required
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    q = Patient.query

    if not current_user.user_role.can_lookup_other_regions_stats:
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

        out_of_rk = Region.query.filter_by(name="Вне РК").first()

        q = q.filter(Patient.region_id != out_of_rk.id)

        if not current_user.user_role.can_lookup_other_regions_stats:
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
        # in_hospital = q.filter(Patient.in_hospital==True).count()
        # # in_hospital = 0
        # ratio = 0 if is_found == 0 else in_hospital / is_found
        # in_hospital_str = str("{}/{} ({}%)".format(in_hospital,
        #                                            is_found, format(ratio * 100, '.2f')))

        # Is Infected
        infected_state_id = State.query.filter_by(value=c.state_infec[0]).first().id

        is_infected = q.join(PatientState, PatientState.patient_id == Patient.id)
        is_infected = is_infected.filter(PatientState.state_id == infected_state_id).count()

        ratio = 0 if total == 0 else is_infected / total
        is_infected_str = str("{}/{} ({}%)".format(is_infected, total, format(ratio * 100, '.2f')))

        # Is Currently Infected
        is_currently_infected = q.filter(Patient.is_infected==True).count()
        ratio = 0 if total == 0 else is_currently_infected / total
        is_currently_infected_str = str("{}/{} ({}%)".format(is_currently_infected, total, format(ratio * 100, '.2f')))

        return render_template(template + '.html', total_kz_patients=str(total), is_found_str=is_found_str,
                                is_currently_infected_str=is_currently_infected_str, 
                                is_infected_str=is_infected_str, **kwargs)

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

    hospitals_options = ""

    if region_id != '' and hospital_type_id != '':
        hospitals = Hospital.query.filter_by(region_id=int(region_id), hospital_type_id=int(hospital_type_id))

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

@blueprint.route("/patients_content_by_id", methods=['POST'])
def patients_content_by_id():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))
    req = request.get_json()
    if not "lat_lon" in req:
        return render_template('errors/error-400.html'), 400
    print("lat lon", req["lat_lon"])
    lat_lon = req["lat_lon"]

    q = Patient.query

    response = []

    pat = None
    lat_lon[0] = format(lat_lon[0], ".5f")
    lat_lon[1] = format(lat_lon[1], ".5f")
    try:
        pat = q.join(Address, Patient.home_address_id == Address.id).filter(Address.lat == str(lat_lon[0])).filter(Address.lng == str(lat_lon[1])).filter(Patient.is_infected == True).all()
    except exc.SQLAlchemyError as err:
        return render_template('errors/error-400.html'), 400
    if not pat:
        return jsonify({})
    for p in pat:
        is_found = "Нет"
        is_infected = "Нет"
        if p.is_found:
            is_found = "Да"
        if p.is_infected:
            is_infected = "Да"
        response.append({
            "id": uuid.uuid1(),
            "balloonContent": '<a href="/patient_profile?id=' + str(p.id) + '">' + repr(p) + '</a><br><strong>Регион</strong>:' + repr    (p.region) + '<br><strong>Адрес</strong>: ' + repr(p.home_address) + '<br><strong>Найден</strong>: ' + is_found +   '<br><strong>Инфицирован</strong>: ' + is_infected + '<br>',
            "clusterCaption": repr(p)
        })

    return jsonify(response)


@blueprint.route("/patients_within_tiles")
@login_required
@support_jsonp
def patients_within_tiles():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))
    if not "bbox" in request.args or not "zoom" in request.args:
        return render_template('errors/error-400.html'), 400
    latlng = request.args["bbox"].split(',')
    bbox_x1 = float(latlng[0])
    bbox_y1 = float(latlng[1])
    bbox_x2 = float(latlng[2])
    bbox_y2 = float(latlng[3])

    zoom = int(request.args["zoom"])

    distance = 0.1**10

    wo_clusters = "clusters_off" in request.args
    if not wo_clusters:
        if (zoom > 19 or zoom < 0):
            return render_template('errors/error-400.html'), 400
        distances = [0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.5, 0.5, 0.09, 0.07, 0.02, 0.01, 0.009,  0.008, 0.003, 0.002, 0.0009, 0.0005, 0.0001]
        distance = distances[zoom]
    
    # distance = 2
    print(distance)
    coordinates_patients = {
        "type": "FeatureCollection",
        "features": []
    }

    sql = text("""
    SELECT row_number() over () AS id,
      ST_NumGeometries(gc) as count,
      ST_X(ST_Centroid(gc)) AS X,
      ST_Y(ST_Centroid(gc)) AS Y
    FROM (
      SELECT unnest(ST_ClusterWithin(geom, %s)) gc
      FROM (
        SELECT * FROM "Address" 
        JOIN "Patient" 
        ON "Address".id = "Patient".home_address_id
        WHERE "Address".geom && ST_MakeEnvelope(%s, %s, %s, %s, 3857) AND "Patient".is_infected = true
      ) AS points
    ) f;
    """ % (str(distance), bbox_y1, bbox_x1, bbox_y2, bbox_x2))
    # sql = text("""
    # SELECT id,
    #   count(*) as num,
    #   ST_X(ST_Centroid(ST_Extent(geom))) as X,
    #   ST_Y(ST_Centroid(ST_Extent(geom))) as Y
    # FROM
    # (
    #     SELECT ST_ClusterKMeans(geom, 1) OVER() AS id, ST_Centroid(geom) as geom
    #     FROM (
    #           SELECT * FROM "Address" WHERE geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
    #     ) AS points
    # ) tsub
    # GROUP BY id;
    # """ % (bbox_y1, bbox_x1, bbox_y2, bbox_x2))
    m = db.engine.execute(sql)
    for a in m:
        features = []
        count = int(a[1])
        if zoom == 19:
            for i in range(count):
                features.append(
                    {
                        "type": 'Feature',
                        "id":  uuid.uuid1(),
                        "properties": {
                            "balloonConntent": "Loading...",
                            "clusterCaption": "Loading..."
                        },
                        "geometry": {
                            "type": 'Point',
                            "coordinates": [a[3], a[2]]
                        }
                    }
                )
        if count == 1:
            coordinates_patients["features"].append(
                 {
                    "type": 'Feature',
                    "geometry": {
                        "type": 'Point',
                        "coordinates": [a[3], a[2]]
                    },
                    "id": uuid.uuid1(),
                    "options": {
                        "preset": 'islands#blueIcon'
                    }
                },
            )
        else:
            coordinates_patients["features"].append(
                {
                    "type": 'Cluster',
                    "id": uuid.uuid1(),
                    "number": int(a[1]),
                    "geometry": {
                        "type": 'Point',
                        "coordinates": [a[3], a[2]]
                    },
                    "features": features,
                    "properties": {
                        "iconContent": int(a[1]),
                    }
                }
            )
    return jsonify(coordinates_patients)
