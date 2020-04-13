# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from app.main import blueprint
from flask import render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app import login_manager, db
from app import constants as c
from jinja2 import TemplateNotFound

from app.main.hospitals.models import Hospital, Hospital_Type
from app.main.patients.models import Patient
from app.main.models import Region

from datetime import datetime
import pandas as pd
import numpy as np
import math, re
from app.main.hospitals.forms import AddHospitalForm, HospitalSearchForm
from app.main.util import get_regions, get_regions_choices, populate_form, disable_form_fields
from flask_babelex import _
from app.main.routes import route_template

from sqlalchemy import exc

def prepare_hospital_form(form, current_user):
    if not form.region_id.choices:
        form.region_id.choices = get_regions_choices(current_user, with_all_regions=False)

    if not form.hospital_type_id.choices:
        form.hospital_type_id.choices = [(t.id, t.name) for t in Hospital_Type.query.all()]

def get_hospital_short_name(full_name):
    short_name = re.findall('"([^"]*)"', full_name.replace("«", "\"").replace("»", "\""))

    if not len(short_name):
        short_name = full_name
    elif not (len(short_name[0])):
        short_name = full_name
    else:
        short_name = short_name[0]

    return short_name

@blueprint.route('/hospitals')
@login_required
def hospitals():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))
    
    form = HospitalSearchForm(request.form)

    if not form.region.choices:
        form.region.choices = get_regions_choices(current_user)
    
    filt = dict()

    q = Hospital.query
    region = request.args.get("region", '-1')
    
    if not current_user.is_admin:
        filt["region_id"] = current_user.region_id
    else:
        if region != str(-1):
            filt["region_id"] = region
            form.region.default = region
            q = Hospital.query.filter_by(region_id = filt["region_id"])

    hospital_type = Hospital_Type.query.all()

    if not form.hospital_type.choices:
        form.hospital_type.choices = [ (-1, c.all_hospital_types) ] + [(r.id, r.name) for r in hospital_type]

    hospitals = []

    hospital_type = request.args.get("hospital_type", '-1')
    if hospital_type != str(-1):
        filt["hospital_type_id"] = hospital_type
        form.hospital_type.default = hospital_type

    page = 1
    per_page = 10
    if "page" in request.args:
        page = int(request.args["page"])

    q = q.filter_by(**filt)
    
    total_len = q.count()

    for h in q.offset((page-1)*per_page).limit(per_page).all():
        patients_num = Patient.query.filter_by(hospital_id=h.id).count()
        hospitals.append((h, patients_num))

    max_page = math.ceil(total_len/per_page)

    change = None
    error_msg = None

    if "added_hospital" in request.args:
        change =_("Стационар был успешно добавлен")
    elif "delete_hospital" in request.args:
        change =_("Стационар был успешно удален")
    elif "error" in request.args:
        error_msg = request.args["error"]

    form.process()    

    return route_template('hospitals/hospitals', hospitals=hospitals, form=form, page=page, max_page=max_page,
                         total = total_len, change=change, error_msg=error_msg)

@blueprint.route('/add_hospital', methods=['GET', 'POST'])
def add_hospital():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500

    form = AddHospitalForm()

    prepare_hospital_form(form, current_user)

    form.process()

    if 'create' in request.form:
        new_dict = request.form.to_dict(flat=True)
        
        full_name = new_dict.get('full_name', '')

        hospital = Hospital.query.filter_by(full_name=full_name).first()
        if hospital:
            return route_template( 'hospitals/add_hospital_and_profile', error_msg=_('Стационар с таким именем уже добавлен'), form=form, change=None)

        if full_name:
            new_dict['name'] = get_hospital_short_name(full_name)
            new_dict['full_name'] = full_name

            hospital = Hospital(**new_dict)

            hospital.beds_amount = 0
            hospital.meds_amount = 0
            hospital.tests_amount = 0
            hospital.tests_used = 0            
            
            db.session.add(hospital)
            db.session.commit()

            return redirect("{}?added_hospital".format(url_for('main_blueprint.hospitals')))
        else:
            return render_template('errors/error-500.html'), 500
    else:
        return route_template( 'hospitals/add_hospital_and_profile', form=form, change=None, error_msg=None, is_profile=False)

@blueprint.route('/hospital_profile', methods=['GET', 'POST'])
@login_required
def hospital_profile():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if "id" in request.args:
        try:
            hospital_query = Hospital.query.filter_by(id=request.args["id"])
            hospital = hospital_query.first()
        except exc.SQLAlchemyError:
            return render_template('errors/error-400.html'), 400    
        
        if not hospital:
            return render_template('errors/error-404.html'), 404
        else:
            form = AddHospitalForm()
            
            change = None
            error_msg = None

            if not current_user.is_admin:
                form_fields = ["full_name", "region_id", "hospital_type_id"]

                disable_form_fields(form, form_fields)
                                
            if 'update' in request.form and current_user.is_admin:
                values = request.form.to_dict()
                values.pop("csrf_token", None)
                values.pop("update", None)

                values['name'] = get_hospital_short_name(values['full_name'])
                
                hospital_query.update(values)

                db.session.add(hospital)
                db.session.commit()

                change = _("Данные обновлены")                

            prepare_hospital_form(form, current_user)

            hospital = hospital_query.first()
            hospital_parameters = hospital.__dict__.copy()

            populate_form(form, hospital_parameters)

            form.process()

            return route_template('hospitals/add_hospital_and_profile', form = form, change=change, hospital=hospital, error_msg=error_msg, is_profile=True)
    else:    
        return render_template('errors/error-500.html'), 500

@blueprint.route('/delete_hospital', methods=['POST'])
@login_required
def delete_hospital():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500        
    
    if len(request.form):
        if "delete" in request.form:
            hospital_id = request.form["delete"]
            try:
                hospital = Hospital.query.filter(Hospital.id == hospital_id).first()
            except exc.SQLAlchemyError:
                pass

            if hospital:
                if Patient.query.filter_by(hospital_id=hospital.id).count():
                    error_msg = _("К стационару прикреплены пациенты. Удалите пациентов, прикрепленных к данному стационару")
                    return redirect("{}?error={}".format(url_for('main_blueprint.hospitals'), error_msg))

                db.session.delete(hospital)
                db.session.commit()

    return redirect("{}?delete_hospital".format(url_for('main_blueprint.hospitals')))