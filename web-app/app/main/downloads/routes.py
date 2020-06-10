# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""
from app.main import blueprint
from flask import render_template, redirect, url_for, request, Response
from flask_login import login_required, current_user
from app import login_manager, db

import pandas as pd
import io

from app.main.models import Region
from app.main.patients.models import Patient
from app.main.users.forms import CreateUserForm, UpdateUserForm, UserActivityReportForm,\
                                    UserSearchForm, UserPatientsSearchForm, CreateUserRoleForm
from app.main.forms import TableSearchForm
import math
from app.login.models import User, UserRole
from app.main.util import get_regions, get_regions_choices, populate_form, disable_form_fields, parse_date
from app.login.util import hash_pass
from flask_babelex import _
from app.main.routes import route_template
from jinja2 import TemplateNotFound
from app import constants as c
from sqlalchemy import exc, func
from sqlalchemy.sql import select
import urllib
from datetime import datetime, timedelta

from app.main.users.modules import UserTableModule, UserPatientsTableModule, UserRolesTableModule

@blueprint.route('/downloads', methods=['GET'])
@login_required
def downloads():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.user_role.can_access_users and not current_user.user_role.can_export_users:
        return render_template('errors/error-500.html'), 500

    form = UserActivityReportForm()

    regions = get_regions(current_user)

    if not form.region_id.choices:
        form.region_id.choices = [ (-1, c.all_regions) ] + [(r.id, r.name) for r in regions]
   
    change = None
    error_msg = None

    if "added_user" in request.args:
        change =_("Пользователь был успешно добавлен")
    elif "delete_user" in request.args:
        change =_("Пользователь был успешно удален")
    elif "error" in request.args:
        error_msg = request.args["error"]

    users_search_form = UserSearchForm()

    if not users_search_form.region_id.choices:
        users_search_form.region_id.choices = [(-2, _("Неважно"))]
        users_search_form.region_id.choices += get_regions_choices(current_user)

    q_patient = db.session.query(Patient.created_by_id,
                                    func.count('*').label('patient_count'))    
    
    q_patient = q_patient.group_by(Patient.created_by_id).subquery()
    q = db.session.query(User, q_patient.c.patient_count).outerjoin(q_patient, User.id == q_patient.c.created_by_id)

    header_buttons = []
    
    if current_user.user_role.can_access_roles:
        header_buttons.append((_("Управление Ролями"), "users/roles"))

    if current_user.user_role.can_add_edit_user:
        header_buttons.append((_("Добавить Пользователя"), "add_user"))
    
    users_table = UserTableModule(request, q, users_search_form, 
        header_button=header_buttons)

    users_search_form.process()
    form.process()
    return route_template('downloads/downloads', users_table = users_table, form=form,
                            users_search_form=users_search_form, constants=c, change=change, error_msg=error_msg)